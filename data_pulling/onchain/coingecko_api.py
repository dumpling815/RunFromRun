import json, re
import httpx
from common.settings import API_KEYS, API_URLS
import asyncio

coingecko_id_dict: dict ={
    "USDT" : "tether",
    "USDC" : "usd-coin",
    "FDUSD": "first-digital-usd",
    "PYUSD": "paypal-usd",
    "TUSD" : "true-usd",
    "USDP" : "paxos-standard"
}

async def httpx_request_to_coingecko(url:str, headers:dict, querystring:dict) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
    return data

async def historical_supplies_charts_by_coin(stablecoin: str) -> list:
    DAYS = '30' # 최근 7일간의 데이터
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}
    querystring = {"vs_currency":"usd","days":DAYS,"interval":"daily","precision":"full"}
    
    url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id_dict[stablecoin]}/market_chart"
    data = await httpx_request_to_coingecko(url=url,headers=headers,querystring=querystring)
    # coros: list[asyncio.Future] = []
    # for chain, cfg in coin_chain_info.items():
    #     url = f"{API_URLS.COINGECKO_DEMO_API_URL}/coins/{chain}/contract/{cfg['contract']}/market_chart"
    #     coros.append(httpx_request_to_coingecko(url, headers, querystring))
    # response = await asyncio.gather(*coros)
    # history: dict[str, dict] = {chain: data for chain, data in zip(coin_chain_info.keys(), response)}
    prices = data['prices']
    market_caps = data['market_caps']
    circulation_charts = []
    chart_time = []
    for t in range(int(DAYS)):
        chart_time.append(market_caps[t][0])
        circulation_charts.append(market_caps[t][1]/prices[t][1])
    return (chart_time,circulation_charts)

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
