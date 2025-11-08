# Pipeline for testing RfR server.
from datetime import datetime
from typing import Optional
from pathlib import Path
from common.schema import Asset, AssetTable, AmountsOnly
from ollama import chat, ChatResponse, Options
import pandas as pd
import camelot, fitz, re, json, common  # PyMuPDF

SYSTEM_PROMPT = """
    You are a **financial data extraction agent**. 
    Your job is to read noisy tables extracted from stablecoin issuers’ PDF reports and fill a strict JSON object that matches the provided schema (AssetTable).
    Note that the tables may contain extraction errors, inconsistent formatting, footnotes, or other noise.
    The only attribute you have to fill correctly is the asset's `amount` in US dollars.
    ## Your tasks (do them in order, but only OUTPUT the final JSON):

    1) **Identify & Normalize Asset Lines**
    - Report wording varies by issuer. Map semantically equivalent line items into the schema fields below.
    - Examples of mapping:
        - "Cash and Cash Equivalents", "Bank deposits", "Cash held at custodians" → `cash_bank_deposits`
        - "U.S. Treasury Bills", "UST Bills", "T-Bills" → `us_treasury_bills`
        - "Government Money Market Funds" → `gov_mmf`
        - "Repos (Overnight/Term)" → `repo_overnight_term`
        - "Non‑U.S. Treasury Bills", "Sovereign Bills (non‑US)" → `non_us_treasury_bills`
        - "U.S. Treasury Notes/Bonds (other than bills)" → `us_treasury_other_notes_bonds`
        - "Corporate Bonds/Commercial Paper" → `coporate_bonds`
        - "Precious Metals" → `precious_metals`
        - "Digital Assets/Crypto" → `digital_assets`
        - "Secured Loans" → `secured_loans`
        - "Other Investments" → `other_investments`
        - "Custodial Concentration Risk" → `custodial_concentration`
    - If the report splits a category into multiple rows (e.g., several cash-like rows), **sum them** into the single schema field.

    2) **Use Instrument Codes (CUSIP, ISIN, Ticker)**
    - If a line includes identifiers (e.g., CUSIP/ISIN), use your financial knowledge to classify the instrument and map it into the correct schema category above.

    3) **Parse Numbers & Units Robustly**
    - Strip currency symbols (e.g., `$`), commas, and footnote markers.
    - Parentheses indicate negatives; treat them as negative values only if it is clearly a subtraction. Most reserve tables list positive holdings.
    - Convert percents like `"12.3%"` → `12.3` (number, not string).
    - All `amount` values must be in **US dollars** (not thousands/millions). If the table header indicates scale (e.g., "in millions"), multiply accordingly.
    - Be careful with numbers that contains ',' you should interpret them as thousands separator, not decimal point.

    4) **Fill Missing Items Carefully**
    - If a schema field cannot be located, set:
        ```
        tier = -1
        qls_score = 0.0
        amount = 0.0
        ratio = null
        ```
    - Do **not** invent numbers.

    5) **Validate Before Emitting JSON**
    - Ensure every schema key exists and is an object with the required fields.
    - Ensure numeric fields are numbers (not strings).
    - Compute `total_amount` as the **sum** of all `amount` fields you filled (even when some are 0.0).
    - Ensure all amounts ≥ 0 and ratios ∈ [0, 100] when present.
    - If a ratio is present but amount is missing, infer amount when the report provides `total` and ratios (amount = total × ratio/100). Only do this when the relation is explicitly implied by the table.

    6) **Output Format**
    - Output **only** one JSON object that matches the AssetTable schema exactly.
    - No explanations, no comments, no prose outside of JSON.
"""
USDT_PDF_PATH = "./test/report/USDT.pdf"
OLLAMA_MODEL = "martain7r/finance-llama-8b:q4_k_m"
MAX_ROWS_PER_TABLE = 1000  # 각 테이블당 최대 행 수 제한 (프롬프트 크기 제한을 위해)
USER_PROMPT_TEMPLATE = f"""
    You will get _tablenum_ dataframes the follwing dataframe extracted from a financial report PDF, extract the asset information and fill the given JSON format as specified below.
    Here is the extracted dataframe: __tables__.
"""


# PDF 분석 함수
def get_pdf_style(pdf_path, sample_pages=3):
    """
    PDF가 텍스트 기반인지 이미지 기반인지 판별.
    sample_pages: 앞쪽 몇 페이지만 검사 (기본 3)
    """
    doc = fitz.open(pdf_path)
    n_pages = len(doc)
    n_check = min(sample_pages, n_pages)
    text_chars = 0
    image_count = 0

    for i in range(n_check):
        page = doc[i]
        text = page.get_text("text")
        text_chars += len(text.strip())
        image_count += len(page.get_images(full=True))

    if text_chars > 30:  # 페이지에 의미 있는 텍스트가 있다면 텍스트 기반
        return "text"
    elif image_count > 0:
        return "image"
    else:
        raise ValueError("Unable to determine PDF type.")

# Camelot으로 추출한 테이블 필터링 함수 
def filter_valid_tables(tables: camelot.core.TableList):
    # Camelot 사용시 일반 문단도 talbe로 오인될 가능성 존재하기 때문에 필터링을 거침
    # 현재 필터링 조건:
    # 1) 최소한의 열이 있는지 확인 (2열 이상) -> 모든 자산 테이블에는 자산의 명칭과 그 값이 있기 때문에 최소 2열 이상이 되어야함.
    # 2) 왼쪽 열의 평균 길이가 너무 길면 잘못 추출된 테이블로 간주 (100자 이상) -> 문단을 오인하는 경우는 해당 문장이 전부 왼쪽 열에 들어가기 때문.
    # 이외 필터링 조건은 추후 필요시 추가 가능.
    valid_tables = []
    for table in tables:
        df = table.df
        #필터링 조건1: 최소한의 열이 있는지 확인
        if df.shape[1] < 2:
            continue
        leftmost_col = df.iloc[:,0].astype(str) # 첫번째 열 + 문자열로 변환
        next_left_col = df.iloc[:,1].astype(str) # 두번째 열 + 문자열로 변환
        avg_len_1 = leftmost_col.apply(len).mean()
        avg_len_2 = next_left_col.apply(len).mean()
        if avg_len_1 > 70 or avg_len_2 > 70:  #필터링 조건2: 왼쪽 열의 평균 길이가 너무 길면 잘못 추출된 테이블로 간주
            continue
        valid_tables.append(table)
    return valid_tables

# 필터링된 테이블 후처리 함수
num_like = re.compile(r"^\s*[\$\(\)\-\+\d.,% ]+\s*$")  # 금액/숫자/퍼센트 등
def is_long_text(s: str, min_len=20, min_spaces=1):
    s = str(s)
    if not s or s.strip() == "":
        return False
    if num_like.match(s):          # 숫자/금액 형태면 제외
        return False
    if len(s) < min_len:           # 너무 짧으면 제외
        return False
    if s.count(" ") < min_spaces:  # 공백 거의 없으면(코드/약어) 제외
        return False
    return True

def spillback_to_col0(df: pd.DataFrame) -> pd.DataFrame:
    # 만일 pdf의 첫번째 열에 지나치게 긴 문장이 오는 경우, 0번째 열이 비고 첫번째 열에 긴 문장이 오는 경우가 있어 이를 보정
    # 왜냐하면, 특정 값에 대한 설명이 0번째 열에 오는 것이 정상적이기 때문.
    df = df.copy()
    n_cols = df.shape[1]
    if n_cols < 2:
        return df

    # 0열이 비고, 다른 열 중 "긴 문장"이 있는 경우 → 가장 긴 문장을 0열로 이동
    col0_empty = df.iloc[:, 0].astype(str).str.strip().eq("")

    def pick_longest_text(row):
        candidates = []
        for j in range(1, n_cols):
            sj = str(row[j])
            if is_long_text(sj):
                candidates.append((len(sj), j))
        if not candidates:
            return row
        # 가장 긴 텍스트가 있는 열 선택
        _, jmax = max(candidates, key=lambda x: x[0])

        # 0열이 비어있으면 이동, 비어있지 않으면 앞에 합치기(안전)
        left = str(row[0]).strip()
        right = str(row[jmax]).strip()
        if left == "":
            row[0] = right
        else:
            row[0] = (left + " " + right).strip()
        row[jmax] = ""  # 원래 위치 비우기
        return row

    df.loc[col0_empty, :] = df.loc[col0_empty, :].apply(pick_longest_text, axis=1)
    return df

def drop_lowercase_start(df: pd.DataFrame) -> pd.DataFrame:
    # 첫글자가 소문자라면, 표가 아님에도 불구하고 잘못된 인식으로 표에 포함되어 있는 경우로 볼 수 있음.
    # 따라서, 0번째 열, 0번째 행의 첫글자가 소문자라면 해당 행을 제거.
    if df.empty:
        return df.copy()
    
    def starts_lower(s) -> bool:
        if not isinstance(s, str) or not s:
            return False
        ch = s.strip()[0]
        return 'a' <= ch <= 'z'
    
    if starts_lower(df.iat[0,0]):
        df = df.drop(index=df.index[0]).reset_index(drop=True)
    return df

def post_process_first_row(df: pd.DataFrame) -> pd.DataFrame:
    # 가장 흔한 오류 중 하나는, 표의 일부가 아닌 다른 문단 혹은 다른 표가 첫번째 행에 포함되는 경우.
    # 이러한 경우를 보정하기 위한 후처리 함수.
    # 1) 0번째 행, 0번째 열이 소문자로 시작하는 경우 해당 행 제거
    # 2) 0번째 행
    pass

def eliminate_footnotes(df: pd.DataFrame) -> pd.DataFrame:
    # 표 내에 각주(footnote) 등이 포함되는 경우가 있음.
    # 이러한 각주 부분을 제거하기 위한 후처리 함수.
    # 각주는 대개 항목명 뒤에 위치하며 일반적으로 해당 문자열의 맨 마지막에 숫자로 인식됨.
    # 따라서, 띄어쓰기로 구분된 마지막 단어의 마지막 한 문자 혹은 두 문자가 숫자라면, 해당 숫자만 제거. (주석이 100개가 넘는 상황은 가정하지 않음)
    if df.empty:
        return df.copy()
    
    def remove_footnote_from_cell(s: str) -> str:
        if not isinstance(s, str) or not s:
            return s
        try:
            float(s.replace(",","")) # 전체가 숫자인 경우는 그대로 반환
        except ValueError:
            last_word = s.rstrip().rsplit(" ",1)[-1]
            if last_word[-1] >= '0' and last_word[-1] <= '9':
                if len(last_word) >=2:
                    if last_word[-2] >= '0' and last_word[-2] <= '9':
                        # 마지막 단어의 마지막 두 글자가 숫자인 경우
                        return s[:-2]
                # 마지막 단어의 마지막 한 글자가 숫자인 경우
                return s[:-1]
            else:
                return s
        return s
    df[0] = df[0].apply(remove_footnote_from_cell)
    return df 

def post_process_tables(tables: camelot.core.TableList) -> list[pd.DataFrame]:
    processed_tables = []
    for table in tables:
        df = table.df
        df = spillback_to_col0(df)
        df = drop_lowercase_start(df)
        df = eliminate_footnotes(df)
        processed_tables.append(df)
        
    return processed_tables

def get_tables_from_pdf(pdf_path: str) -> list[pd.DataFrame]:
    pdf_format = get_pdf_style(pdf_path)
    if pdf_format == "text":
        tables = camelot.read_pdf(
            pdf_path,
            pages = '2-end',
            flavor = 'lattice',
            strip_text='\n',
        )
        tables = filter_valid_tables(tables)
        tables = post_process_tables(tables)
        return tables
    else:
        raise NotImplementedError("Image-based PDF parsing not implemented yet.")


def llm_vote_amounts(amounts_list: list[AmountsOnly]) -> AssetTable:
    if amounts_list is None or len(amounts_list) == 0:
        return AssetTable(total_amount=0.0)
    # 홀수 개의 모델의 응답을 받아 해당 자산별로 중간값(median) 산출
    ASSET_NAMES = [
        "cash_bank_deposits", "us_treasury_bills", "gov_mmf",
        "repo_overnight_term", "non_us_treasury_bills", "us_treasury_other_notes_bonds",
        "coporate_bonds", "precious_metals", "digital_assets",
        "secured_loans", "custodial_concentration", "total_amount"
    ] 
    # total_amount는 포함
    # other investments 제외 : 자세하게 파악되지 않는 자산의 경우로 판단하여 총액 및 모든 자산의 합으로 역산 => 데이터 통일성 확보
    voted_assets = {}
    asset_sum = 0.0

    # Voting by median
    for asset_name in ASSET_NAMES:
        asset_amounts:list[float] = []
        none_count = 0
        for amounts in amounts_list:
            val:Optional[float] = getattr(amounts, asset_name)
            if val is not None or val == 0.0:
                asset_amounts.append(float(val))
            else:
                none_count += 1
                #asset_amounts.append(-1.0)  # None 값을 -1.0으로 대체하여 정렬에 포함시킴.
        
        asset_amounts.sort()
        n = len(amounts_list) - none_count
        if n == 0:
            median_amount = 0.0
        elif n == 1: # 하나의 모델이라도 잡은 경우, 이유가 있기 때문에 해당값을 채택
            median_amount = asset_amounts[0]
        else:
            median_amount = asset_amounts[n // 2] # n이 짝수여도 같은 방식 적용 : 더 작은 값을 선택하여 더 보수적으로 접근
        
        voted_assets[asset_name] = median_amount
        if asset_name != "total_amount":
            asset_sum += median_amount 
    
    voted_assets["other_investments"] = max(voted_assets["total_amount"],asset_sum) - asset_sum
    result:AssetTable =  AmountsOnly.model_validate(voted_assets).to_asset_table()

    return result
    



tables = get_tables_from_pdf(USDT_PDF_PATH)


json_tables = []
for idx, df in enumerate(tables):
    # Keep up to 100 rows per table to avoid oversized prompts (adjust as needed)
    sample = df.head(MAX_ROWS_PER_TABLE).fillna("").astype(str)
    json_tables.append({
        "table_index": idx,
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "rows": sample.values.tolist()
    })

json_tables_str = json.dumps(json_tables, ensure_ascii=False)

user_content = (
    USER_PROMPT_TEMPLATE
    .replace("_tablenum_", str(len(tables)))
    .replace("__tables__", json_tables_str)
)

print("=== User Prompt ===")
print(user_content.lower())
print("=== Sending to LLM ===")


models = ["martain7r/finance-llama-8b:q4_k_m","llama3.1:8b","phi4"]
amounts_only_list = []
for model in models:
    response: ChatResponse = chat(
        model = model,
        format = AmountsOnly.model_json_schema(), # json schema 강제
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        options = Options(temperature=0.0)
    )
    print(f"=== {model} Response ===")
    print(type(response.message.content))
    print(response.message.content)

    amounts_only = AmountsOnly.model_validate_json(response.message.content)
    amounts_only_list.append(amounts_only)

asset_table = llm_vote_amounts(amounts_only_list)
print(f"=== Voted Extracted Asset Table ===")
print(asset_table)