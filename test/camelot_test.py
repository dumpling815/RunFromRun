# Pipeline for testing RfR server.
from datetime import datetime
from data_pulling.dataframe_process import get_tables_from_pdf
from pathlib import Path
from rich import print
import pandas as pd
import camelot, fitz, re  # PyMuPDF



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


def post_process_first_row(df: pd.DataFrame) -> pd.DataFrame:
    # 가장 흔한 오류 중 하나는, 표의 일부가 아닌 다른 문단 혹은 다른 표가 첫번째 행에 포함되는 경우.
    # 이러한 경우를 보정하기 위한 후처리 함수.
    # 1) 0번째 행, 0번째 열이 소문자로 시작하는 경우 해당 행 제거
    # 2) 0번째 행
    if df.empty:
        return df.copy()
    
    # 첫글자가 소문자라면, 표가 아님에도 불구하고 잘못된 인식으로 표에 포함되어 있는 경우로 볼 수 있음.
    # 따라서, 0번째 열, 0번째 행의 첫글자가 소문자라면 해당 행을 제거.
    def starts_lower(s) -> bool:
        if not isinstance(s, str) or not s:
            return False
        ch = s.strip()[0]
        return 'a' <= ch <= 'z'
    
    #  docusign이 표에 포함되는 경우가 많아 docusign이 포함된 첫번째 행만 제거
    def starts_docusign(s) -> bool:
        if not isinstance(s, str) or not s:
            return False
        return "Docusign" in s
    
    if starts_docusign(df.iat[0,0]) or starts_lower(df.iat[0,0]):
        df = df.drop(index=df.index[0]).reset_index(drop=True)
    return df

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
        df = post_process_first_row(df)
        df = eliminate_footnotes(df)
        processed_tables.append(df)
        
    return processed_tables


# paths = [USDC_PDF_PATH, USDT_PDF_PATH, FDUSD_PDF_PATH, PYUSD_PDF_PATH, TUSD_PDF_PATH, USDP_PDF_PATH]
# for i in paths:
#     pdf_format = get_pdf_style(i)
#     print(f"{Path(i).name}: {pdf_format}")
def markdownize_tables(tables: list[pd.DataFrame]) -> list[str]:
    markdown_tables = []
    for idx, df in enumerate(tables):
        # Keep up to MAX rows per table to avoid oversized prompts (adjust as needed)
        df = df.fillna("").astype(str)
        markdown_table = df.to_markdown(index=False)
        markdown_tables.append(markdown_table)
    return markdown_tables

if __name__ == "__main__":
    USDC_PDF_PATH = "./test/report/USDC.pdf"
    USDT_PDF_PATH = "./test/report/USDT.pdf"
    FDUSD_PDF_PATH = "./test/report/FDUSD.pdf"
    PYUSD_PDF_PATH = "./test/report/PYUSD.pdf"
    TUSD_PDF_PATH = "./test/report/TUSD.pdf"
    USDP_PDF_PATH = "./test/report/USDP.pdf"

    for coin in ["USDT","USDC","FDUSD","PYUSD","TUSD","USDP"]:
        tables = get_tables_from_pdf(f"./test/report/{coin}.pdf",coin)
        print(f"==================={coin}======================")
        print(f"===================Total {len(tables)} tables extracted==============================")
        for table in tables:
            print(markdownize_tables([table])[0])
            print(f"###############################################")
        print(f"==================={coin}======================")
        print("=========================================================")
        a = input("continue?")
        if a == 'y':
            continue


