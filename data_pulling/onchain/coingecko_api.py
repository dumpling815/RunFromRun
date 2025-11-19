import httpx, logging, asyncio
from common.settings import API_KEYS, API_URLS

logger = logging.getLogger("RunFromRun.Analyze.Onchain.Coingecko")
logger.setLevel(logging.DEBUG)

coingecko_id_dict: dict ={
    "USDT" : "tether",
    "USDC" : "usd-coin",
    "FDUSD": "first-digital-usd",
    "PYUSD": "paypal-usd",
    "TUSD" : "true-usd",
    "USDP" : "paxos-standard"
}

async def httpx_request_to_coingecko(url:str, headers:dict, querystring:dict | None) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
    return data

async def holder_concentration(stablecoin: str, coin_chain_info: dict) -> dict:
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}
    chains = []
    coros:list[asyncio.Future] = []
    for chain in coin_chain_info.keys():
        if chain != 'tron':
            url = f"https://api.coingecko.com/api/v3/onchain/networks/{chain}/tokens/{coin_chain_info[chain]['contract_address']}/info"
            chains.append(chain)
            coros.append(httpx_request_to_coingecko(url=url,headers=headers))
    token_infos = await asyncio.gather(*coros)
    
    results: dict[str,dict] = {chain: token_info['data']['attributes']['holders'] for chain, token_info in zip(chains,token_infos)}
    return results

async def historical_supplies_charts_by_coin(stablecoin: str) -> dict[list]:
    DAYS = '91' # 최근 7일간의 데이터
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}
    querystring = {"vs_currency":"usd","days":DAYS,"interval":"daily","precision":"full"}
    
    url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id_dict[stablecoin]}/market_chart"
    logger.info(f"Request to Coingecko API...")
    data = await httpx_request_to_coingecko(url=url,headers=headers,querystring=querystring)
    logger.info(f"Coingecko API responsed")    
    return data

async def supply_portions(stablecoin:str, coin_chain_info: dict) -> dict:
    pass



# 아래 두 함수는 chain_config.yaml 파일이 없을 때 Coingecko API를 통해 토큰 리스트를 가져오기 위한 함수들임.
async def get_asset_platforms() -> dict:
    url = f"{API_URLS.COINGECKO_DEMO_API_URL}/asset_platforms"
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url, headers=headers) 
        response.raise_for_status()
        data = response.json()

    platforms = {item['id']: item for item in data}
    return platforms

async def token_lists_by_asset_platform(asset_platform_id: str) -> list:
    url = f"{API_URLS.COINGECKO_DEMO_API_URL}/token_lists/{asset_platform_id}/all.json"
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data['tokens']
