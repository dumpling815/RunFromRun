from common.settings import OLLAMASETTINGS, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, LLM_OPTION
from common.schema import AssetTable, AmountsOnly, Asset
from data_pulling.offchain.pdf_fetch_caching import download_and_hash_pdf, search_log, get_AssetTable_from_cache, cache_result
from data_pulling.offchain.dataframe_process import get_tables_from_pdf
from ollama import AsyncClient, ChatResponse, Options
from typing import Optional
import matplotlib.pyplot as plt
import pandas as pd
from  pathlib import Path
from decimal import Decimal
import json, logging, time 

# ollama client의 경우 default로 os.getenv('OLLAMA)

logger = logging.getLogger("pdf_analysis")
logger.setLevel(logging.DEBUG)

# 토큰 제한 확인
# from transformers import AutoTokenizer
# tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")
# text = SYSTEM_PROMPT.replace("__json_schema__", json.dumps(AmountsOnly.model_json_schema()))
# tokens = tokenizer.encode(text)
# print(len(tokens)+ 100)

def markdownize_tables(tables: list[pd.DataFrame]) -> list[str]:
    markdown_tables = []
    for idx, df in enumerate(tables):
        # Keep up to MAX rows per table to avoid oversized prompts (adjust as needed)
        df = df.fillna("").astype(str)
        markdown_table = df.to_markdown(index=False)
        markdown_tables.append(markdown_table)
    return markdown_tables

def jsonize_tables(tables: list[pd.DataFrame]) -> list[str]:
    json_tables = []
    for idx, df in enumerate(tables):
        # Keep up to MAX rows per table to avoid oversized prompts (adjust as needed)
        df = df.fillna("").astype(str)
        json_tables.append(
        {
            "n_rows": int(df.shape[0]),
            "n_cols": int(df.shape[1]),
            "rows": df.values.tolist()
        }
        )

    return json_tables

def cusip_check(tables: list[str]) -> bool:
    for table in tables:
        if "cusip" in table.lower():
            return True
    return False

def complete_user_prompt(str_tables_list: list[str], template: str) -> str:
    tables_str = "\n\n".join(str_tables_list)
    user_prompt = template.replace("__tables__", tables_str).replace("_tablenum_", str(len(str_tables_list)))
    
    return user_prompt

def llm_vote_amounts(amounts_list: list[AmountsOnly], cusip_appearance: bool, pdf_hash: str) -> AssetTable:
    # 홀수 개의 모델의 응답을 받아 해당 자산별로 중간값(median) 산출
    # 기본적으로 명확하지 않은 value에 대해서는 보수적으로 접근하여 더 작은 값을 선택하도록 함.
    # 왜냐하면 더 작은 값을 선택하면 total을 맞추기 위해 correction_value가 더 커짐.
    # 그리고 correction_value의 ratio는 추출된 데이터의 신뢰도를 나타내기 때문에 더욱 보수적인 접근을 수행함.
    # 모델이 None으로 응답한 것과, 0.0으로 응답한 것은 구별되어야 함.
    # 0.0은 해당 자산이 없다는 의미이나, None은 모델이 해당 자산에 대해 판단하지 못했다는 의미이기 때문.
    if amounts_list is None or len(amounts_list) == 0:
        raise RuntimeError("LLM did not return any valid AmountsOnly responses")
    ASSET_NAMES = [
        "cash_bank_deposits", "us_treasury_bills", "gov_mmf", "other_deposits",
        "repo_overnight_term", "non_us_treasury_bills", "us_treasury_other_notes_bonds",
        "corporate_bonds", "precious_metals", "digital_assets",
        "secured_loans", "other_investments", "custodial_concentrated_asset", "total"
    ] 
    voted_assets = {}
    asset_sum = 0.0

    # Voting by median
    for asset_name in ASSET_NAMES:
        asset_amounts:list[Decimal] = []
        for amounts in amounts_list:
            val:Optional[Decimal] = getattr(amounts, asset_name)
            if val is not None:
                asset_amounts.append(Decimal(val))

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
        if asset_name != "total":
            asset_sum += median_amount 

    # total이 표에서 추출 자체가 안되는 edge case 존재할 수 있기 때문에, total은 asset_sum과 비교하여 더 큰 값을 선택
    voted_assets["total"] = max(voted_assets["total"], asset_sum)
    result:AssetTable =  AmountsOnly.model_validate(voted_assets).to_asset_table(cusip_appearance=cusip_appearance, pdf_hash=pdf_hash)

    return result

def delay_dict_to_list(delay_dict: dict[str,Decimal]) -> list[(str,Decimal)]:
    result = []
    for key, value in delay_dict.items():
        result.append((key, value))
    return result

# Analysis 결과 시각화 함수
def plotit_asset_tables(stablecoin:str, asset_table: AssetTable):
    asset_list: list[(str,Asset)] = asset_table.to_list()
    asset_names = []
    asset_values = []
    for tup in asset_list:
        asset_names.append(tup[0])
        asset_values.append(tup[1].amount)
    plt.figure(figsize=(10, 6))
    plt.bar(asset_names, asset_values)
    plt.title(f'Asset proportion : {stablecoin}')
    plt.xlabel('Asset')
    plt.ylabel('US Dollar')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()   # 라벨 잘림 방지
    plt.savefig(f'{stablecoin}_pdf_analysis_assets.png')
        
def plotit_delay(stablecoin: str,delay_tup_list: list[(str,Decimal)], model_nums: int):
    delay_name=[]
    delay_time=[]
    COLOR = ['blue'] + ['green'] * model_nums + ['orange','red']
    for tup in delay_tup_list:
        delay_name.append(tup[0])
        delay_time.append(tup[1])
    plt.figure(figsize=(10, 6))
    plt.bar(delay_name, delay_time, color=COLOR)
    plt.title(f'Delay proportion : {stablecoin} PDF analysis in RTX 5070')
    plt.xlabel('Job')
    plt.ylabel('Seconds')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()   # 라벨 잘림 방지
    plt.savefig(f'{stablecoin}_pdf_analysis_delay.png')

# Main PDF 분석 함수
async def analyze_pdf_api_call(pdf_path: Path, stablecoin: str) -> AssetTable:
    raise NotImplementedError("API call method is not implemented yet.")

async def analyze_pdf_local_llm(pdf_hash: str, pdf_path: Path, stablecoin: str) -> AssetTable:
    # ============== 1. PDF에서 데이터프레임 추출 ==============
    delay_dict: dict[str,Decimal] = {}
    e2e_start_time = time.time()
    try:
        tables: list[pd.DataFrame] = get_tables_from_pdf(pdf_path, stablecoin)
    except Exception as e:
        logger.error(f"Error extracting tables from PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"PDF table extraction failed for {pdf_path.name}") from e
    logger.debug(f"Extracted {len(tables)} tables from PDF: {pdf_path.name}")
    
    # ============== 2. 데이터프레임들을 LLM 입력용 JSON 혹은 Mardown으로 변환 ==============
    # => 일반적으로 Markdown 형식이 더 안정적임. LLM 학습 시에 표 형식을 markdown 형태로 많이 접했을 가능성이 높음.
    try:
        #json_tables_str: list[str] = jsonize_tables(tables)
        markdown_tables_list: list[str] = markdownize_tables(tables)
    except Exception as e:
        logger.error(f"Error converting tables to Markdown(or JSON) for PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"Dataframe to Markdown(or JSON) conversion failed for {pdf_path.name}") from e
    logger.debug(f"Converted tables to Markdown(or JSON) format for LLM input.")

    # ============== 3. Table에 CUSIP 포함되어 있는지 확인 ==============
    cusip_appearance = cusip_check(markdown_tables_list)

    # ============== 4. User Prompt에 string으로 변환된 표 주입 ==============
    #user_prompt = complete_user_prompt(json_tables_str, USER_PROMPT_TEMPLATE)
    user_prompt = complete_user_prompt(markdown_tables_list, USER_PROMPT_TEMPLATE)
    logger.debug(f"Constructed user prompt for LLM.")  
    delay_dict["preprocess_delay"] = time.time() - e2e_start_time


    # ============== 5. LLM 호출 및 응답 수집 ==============
    amounts_list: list[AmountsOnly] = []
    try:
        ollama_client = AsyncClient(host=OLLAMASETTINGS.HOST)
    except Exception as e:
        logger.error(f"Failed to Initiate Ollama Client. {e}")
        raise RuntimeError(f"Ollama Initiate Failed from Host: {OLLAMASETTINGS.HOST}") from e
        
    for model in OLLAMASETTINGS.MODELS:
        logger.debug(f"Calling LLM model **{model}** for PDF: {pdf_path.name}")
        model_start_time = time.time()
        try:
            response: ChatResponse = await ollama_client.chat(
                model=model,
                format = "json",
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT.replace("__json_schema__", json.dumps(AmountsOnly.model_json_schema()))},
                    {"role": "user", "content": user_prompt}
                ],
                options = Options(temperature=0.0)
            )
        except Exception as e:
            logger.error(f"LLM call failed for model {model} on PDF {pdf_path.name}: {e}")
            continue
        delay_dict[model] = time.time() - model_start_time
        logger.info(f"{model} latency: {delay_dict[model]:.4f} seconds.")
        content = response.message.content.strip()
        if not content:
            logger.warning(f"Empty response from model {model}. Skipping.")
            continue

        # ============== 6. JSON 응답을 pydantic model 리스트에 append ==============
        try:
            amounts_only = AmountsOnly.model_validate_json(content)
        except Exception as e:
            logger.error(f"Invalid JSON from model {model}: {e}")
            logger.debug(f"Raw response content:\n{content}")
            continue
        logger.info(f"\n=== From {model} ===\n{response.message.content}")
        amounts_list.append(amounts_only)
    
    # ============== 7. LLM 응답 결과로 최종 결과물 산출 (voting) ==============
    voting_time_start = time.time()
    try:
        asset_table: AssetTable = llm_vote_amounts(amounts_list=amounts_list,cusip_appearance=cusip_appearance,pdf_hash=pdf_hash)
    except Exception as e:
        logger.error(f"Error during LLM voting for PDF {pdf_path.name}: {e}")
        raise RuntimeError(f"LLM voting failed for {pdf_path.name}") from e
    
    # ============== 8. Record delays and log results ==============
    delay_dict["voting_delay"] = time.time() - voting_time_start
    delay_dict["e2e_delay"] = time.time() - e2e_start_time
    logger.info(f"LLM voting completed in {delay_dict['voting_delay']:.4f} seconds.")
    logger.info(f"End-to-end processing time: {delay_dict['e2e_delay']:.4f} seconds")
    logger.info(f"Completed LLM voting for PDF: {pdf_path.name}")
    logger.info(f"\n{asset_table}")
    delay_list = delay_dict_to_list(delay_dict)
    logger.info(f"Delay breakdown: {delay_list}")

    # Comment it out if plotting is not desired
    plotit_delay(stablecoin, delay_list, len(OLLAMASETTINGS.MODELS))

    return asset_table

async def analyze_pdf(id: str, report_pdf_url: Path, stablecoin: str) -> AssetTable:
    pdf_hash, pdf_path = download_and_hash_pdf(report_pdf_url=report_pdf_url, stablecoin=stablecoin)
    try:
        cached: bool = search_log(pdf_hash=pdf_hash)
    except FileNotFoundError as e:
        logger.error(f"Something gone wrong while searching cache directory: {e}")
        cached = False
    if not cached: # 이전에 분석한 적이 없는 pdf의 경우
        if LLM_OPTION == "local":
            asset_table = await analyze_pdf_local_llm(pdf_hash=pdf_hash,pdf_path=pdf_path, stablecoin=stablecoin)
        else: # LLM_OPTION == "api"
            asset_table = await analyze_pdf_api_call(pdf_hash=pdf_hash,pdf_path=pdf_path, stablecoin=stablecoin)
        cache_result(id=id,pdf_hash=pdf_hash,asset_table=asset_table)
        return asset_table
    else: # log에 이미 분석한 적이 있다는 기록이 있는 경우. 새로운 id여도 로그 크기의 폭발적 증가를 막기 위해 새로 기록하지는 않음
        try:
            asset_table = get_AssetTable_from_cache(pdf_hash=pdf_hash)
        except FileNotFoundError as e:
            logger.error(f"There is not cached file. {e}")
            if LLM_OPTION == "local":
                asset_table = await analyze_pdf_local_llm(pdf_hash=pdf_hash,pdf_path=pdf_path, stablecoin=stablecoin)
            else: # LLM_OPTION == "api"
                asset_table = await analyze_pdf_api_call(pdf_hash=pdf_hash,pdf_path=pdf_path, stablecoin=stablecoin)
            cache_result(id=id,pdf_hash=pdf_hash,asset_table=asset_table)
        return asset_table