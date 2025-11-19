from common.settings import API_KEYS, API_URLS
import httpx

# https://docs.rango.exchange/api-integration/terminology#asset-token
# SWAP simulating을 통해 Slippage 측정으로 매도 압력 분석.
# 기본 to_swap은 USDC를 가정하고, USDC의 slippage 측정 시에는 to_swap을 USDT로 설정
# Rango Docs => 전체 Chain cover

# DEX aggregator는 코인 간 스왑을 할 때, 어떤 경로로 스왑해야 가장 손해를 덜 볼 지 탐색하는 역할.
# DEX aggregotor로 정해진 경로로 실제 스왑을 하는 경우에만 gas prices가 부과됨.
# 따라서, 시뮬레이션만 하는 행위 자체는 gasless라고 할 수 있음

RANGO_CHAIN_ID = {
    "arbirtum-one" : "ARBITRUM",
    "binance-smart-chain" : "BSC",
    "base" : "BASE",
    "ethereum" : "ETH",
    "solana" : "SOLANA",
    "tron" : "TRON",
    "sui" : "SUI"
}

async def httpx_request_to_rango(url:str, headers:dict, querystring:dict) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
    return data


async def DEX_aggregator_simulation(stablecoin: str, coin_chain_info_all: dict):
    chains:list[str] = coin_chain_info_all[stablecoin].keys()
    url = 'https://api.rango.exchange/path/to/resource?apiKey=<YOUR-API-KEY>'
    for chain in chains:
        from_asset_format: str = f"{RANGO_CHAIN_ID[chain]}--{coin_chain_info_all[stablecoin][chain]['contact_address']}"
        to_asset_format: str = f"{RANGO_CHAIN_ID[chain]}--{coin_chain_info_all["USDC"][chain]['contact_address']}" if stablecoin != "USDC" else f"{RANGO_CHAIN_ID[chain]}--{coin_chain_info_all["USDT"][chain]['contact_address']}"
