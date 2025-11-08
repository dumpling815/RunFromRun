from common.settings import CAMELOT_MODE, OLLAMASETTINGS, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from common.schema import AssetTable, AmountsOnly
from typing import Optional
import pandas as pd
from data_pulling.dataframe_process import get_tables_from_pdf
from  pathlib import Path
import json, logging
from ollama import chat, ChatResponse, Options


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def jsonize_tables(tables: list[AssetTable]) -> str:
    json_tables = []
    for idx, df in enumerate(tables):
        # Keep up to MAX rows per table to avoid oversized prompts (adjust as needed)
        sample = df.head(OLLAMASETTINGS.MAX_ROWS_PER_TABLE).fillna("").astype(str)
        json_tables.append({
            "table_index": idx,
            "n_rows": int(df.shape[0]),
            "n_cols": int(df.shape[1]),
            "rows": sample.values.tolist()
        })
    json_tables_str = json.dumps(json_tables, ensure_ascii=False)

    return json_tables_str

def llm_vote_amounts(amounts_list: list[AmountsOnly]) -> AssetTable:
    if amounts_list is None or len(amounts_list) == 0:
        return AssetTable(total_amount=0.0)
    # 홀수 개의 모델의 응답을 받아 해당 자산별로 중간값(median) 산출
    ASSET_NAMES = [
        "cash_bank_deposits", "us_treasury_bills", "gov_mmf",
        "repo_overnight_term", "non_us_treasury_bills", "us_treasury_other_notes_bonds",
        "coporate_bonds", "precious_metals", "digital_assets",
        "secured_loans", "other_investments", "custodial_concentration", "total_amount"
    ] 
    # 
    voted_assets = {}
    asset_sum = 0.0

    # Voting by median
    for asset_name in ASSET_NAMES:
        asset_amounts:list[float] = []
        none_count = 0
        for amounts in amounts_list:
            val:Optional[float] = getattr(amounts, asset_name)
            if val is not None:
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
    
    voted_assets["correction_value"] = max(voted_assets["total_amount"],asset_sum) - asset_sum
    result:AssetTable =  AmountsOnly.model_validate(voted_assets).to_asset_table()

    return result


# Main PDF 분석 함수
def analyze_pdf_api_call(pdf_path: Path) -> AssetTable:
    pass

def analyze_pdf_local_llm(pdf_path: Path, stablecoin: str) -> AssetTable:
    # PDF에서 데이터프레임 추출
    try:
        tables: list[pd.DataFrame] = get_tables_from_pdf(pdf_path, camelot_mode=CAMELOT_MODE[stablecoin])
    except Exception as e:
        logger.error(f"Error extracting tables from PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"PDF table extraction failed for {pdf_path.name}") from e
    logger.info(f"Extracted {len(tables)} tables from PDF: {pdf_path.name}")
    
    # 데이터프레임을 LLM 입력용 JSON 테이블로 변환
    try:
        json_tables_str: str = jsonize_tables(tables)
    except Exception as e:
        logger.error(f"Error converting tables to JSON for PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"Table JSON conversion failed for {pdf_path.name}") from e
    logger.info(f"Converted tables to JSON format for LLM input.")


    user_content = (
        USER_PROMPT_TEMPLATE
        .replace("_tablenum_", str(len(tables)))
        .replace("__tables__", json_tables_str)
    )

    # LLM 호출 및 응답 수집
    amounts_only_list: list[AmountsOnly] = []
    for model in OLLAMASETTINGS.MODELS:
        try:
            response: ChatResponse = chat(
                model=model,
                format = AmountsOnly.model_json_schema(),
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                options = Options(temperature=0.0)
            )
        except Exception as e:
            logger.error(f"LLM call failed for model {model} on PDF {pdf_path.name}: {e}")
            continue
        logger.info(f"=== From {model} ===")
        logger.info(f"{response.message.content}")
        amounts_only = AmountsOnly.model_validate_json(response.message.content)
        amounts_only_list.append(amounts_only)
    
    try:
        asset_table = llm_vote_amounts(amounts_only_list)
    except Exception as e:
        logger.error(f"Error during LLM voting for PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"LLM voting failed for {pdf_path.name}") from e
    logger.info(f"Completed LLM voting for PDF: {pdf_path.name}")
    logger.info(f"\n{asset_table}")
    return asset_table



if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    pdf_path = Path("./test/report/USDT.pdf") # [DEBUG] 테스트용 PDF 경로
    result_table = analyze_pdf_local_llm(pdf_path, stablecoin="USDT")