from common.settings import CAMELOT_MODE, OLLAMASETTINGS, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from common.schema import AssetTable, AmountsOnly
from typing import Optional
import pandas as pd
from data_pulling.dataframe_process import get_tables_from_pdf
from  pathlib import Path
import json, logging
from ollama import chat, ChatResponse, Options


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def markdownize_tables(tables: list[AssetTable]) -> str:
    markdown_tables = []
    for idx, df in enumerate(tables):
        # Keep up to MAX rows per table to avoid oversized prompts (adjust as needed)
        markdown_table = df.to_markdown(index=False)
        markdown_tables.append(markdown_table)

    return markdown_tables

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

    return json_tables

def complete_user_prompt(str_tables_list: list[str], template: str) -> str:
    tables_str = "\n\n".join(str_tables_list)
    user_prompt = template.replace("__tables__", tables_str).replace("_tablenum_", str(len(str_tables_list)))
    
    return user_prompt

def llm_vote_amounts(amounts_list: list[AmountsOnly]) -> AssetTable:
    # 홀수 개의 모델의 응답을 받아 해당 자산별로 중간값(median) 산출
    # 기본적으로 명확하지 않은 value에 대해서는 보수적으로 접근하여 더 작은 값을 선택하도록 함.
    # 왜냐하면 더 작은 값을 선택하면 total_amount를 맞추기 위해 correction_value가 더 커짐.
    # 그리고 correction_value의 ratio는 추출된 데이터의 신뢰도를 나타내기 때문에 더욱 보수적인 접근을 수행함.
    # 모델이 None으로 응답한 것과, 0.0으로 응답한 것은 구별되어야 함.
    # 0.0은 해당 자산이 없다는 의미이나, None은 모델이 해당 자산에 대해 판단하지 못했다는 의미이기 때문.
    if amounts_list is None or len(amounts_list) == 0:
        return AssetTable(total_amount=0.0)
    ASSET_NAMES = [
        "cash_bank_deposits", "us_treasury_bills", "gov_mmf", "other_deposits",
        "repo_overnight_term", "non_us_treasury_bills", "us_treasury_other_notes_bonds",
        "corporate_bonds", "precious_metals", "digital_assets",
        "secured_loans", "other_investments", "custodial_concentrated_asset", "total_amount"
    ] 
    # 
    voted_assets = {}
    asset_sum = 0.0

    # Voting by median
    for asset_name in ASSET_NAMES:
        asset_amounts:list[float] = []
        for amounts in amounts_list:
            val:Optional[float] = getattr(amounts, asset_name)
            if val is not None:
                asset_amounts.append(float(val))

        valid_votes_num = len(asset_amounts)        
        asset_amounts.sort()
        logger.debug(f"Asset: {asset_name}, Valid votes: {valid_votes_num}, Values: {asset_amounts}")
        if valid_votes_num == 0:
            median_amount = 0.0
        elif valid_votes_num == 1: # 하나의 모델이라도 잡은 경우, 이유가 있기 때문에 해당값을 채택 TODO: 유효 개수가 1이라면 신뢰도가 낮은 값일 가능성도 존재함. 추후 보완 필요.
            # deprecated: median_amount = asset_amounts[0]
            median_amount = 0.0 # 더 보수적으로 판단하는 것이 맞다고 여겨짐.
        else:
            median_amount = asset_amounts[(valid_votes_num - 1) // 2] # n이 짝수여도 같은 방식 적용 : 더 작은 값을 선택하여 더 보수적으로 접근
        
        voted_assets[asset_name] = median_amount
        if asset_name != "total_amount":
            asset_sum += median_amount 
    
    voted_assets["correction_value"] = max(voted_assets["total_amount"],asset_sum) - asset_sum
    result:AssetTable =  AmountsOnly.model_validate(voted_assets).to_asset_table()

    return result


# Main PDF 분석 함수
def analyze_pdf_api_call(pdf_path: Path, stablecoin: str) -> AssetTable:
    raise NotImplementedError("API call method is not implemented yet.")

def analyze_pdf_local_llm(pdf_path: Path, stablecoin: str) -> AssetTable:
    # PDF에서 데이터프레임 추출
    try:
        tables: list[pd.DataFrame] = get_tables_from_pdf(pdf_path, stablecoin)
    except Exception as e:
        logger.error(f"Error extracting tables from PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"PDF table extraction failed for {pdf_path.name}") from e
    logger.info(f"Extracted {len(tables)} tables from PDF: {pdf_path.name}")
    
    # 데이터프레임들을 LLM 입력용 JSON 혹은 Mardown으로 변환
    try:
        #json_tables_str: str = jsonize_tables(tables)
        markdown_tables_str: str = markdownize_tables(tables)
    except Exception as e:
        logger.error(f"Error converting tables to JSON for PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"Table JSON conversion failed for {pdf_path.name}") from e
    logger.info(f"Converted tables to JSON format for LLM input.")


    # user_prompt = (
    #     USER_PROMPT_TEMPLATE
    #     .replace("_tablenum_", str(len(tables)))
    #     # .replace("__tables__", json_tables_str)
    # )
    user_prompt = complete_user_prompt(markdown_tables_str, USER_PROMPT_TEMPLATE)
    logger.info(f"Constructed user prompt for LLM.")  

    # LLM 호출 및 응답 수집
    amounts_only_list: list[AmountsOnly] = []
    for model in OLLAMASETTINGS.MODELS:
        try:
            response: ChatResponse = chat(
                model=model,
                format = AmountsOnly.model_json_schema(),
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                options = Options(temperature=0.0)
            )
        except Exception as e:
            logger.error(f"LLM call failed for model {model} on PDF {pdf_path.name}: {e}")
            continue
        content = response.message.content.strip()
        if not content:
            logger.warning(f"Empty response from model {model}. Skipping.")
            continue

        try:
            amounts_only = AmountsOnly.model_validate_json(content)
        except Exception as e:
            logger.error(f"Invalid JSON from model {model}: {e}")
            logger.debug(f"Raw response content:\n{content}")
            continue
        logger.info(f"=== From {model} ===")
        logger.info(f"{response.message.content}")
        # amounts_only = AmountsOnly.model_validate_json(response.message.content)
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