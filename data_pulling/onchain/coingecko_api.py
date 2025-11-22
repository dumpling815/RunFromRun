import httpx, logging, asyncio, math
from common.settings import API_KEYS, API_URLS
from rich import print


logger = logging.getLogger("RunFromRun.Analyze.Onchain.Coingecko")
logger.setLevel(logging.DEBUG)

coingecko_token_id_dict: dict ={
    "USDT" : "tether",
    "USDC" : "usd-coin",
    "FDUSD": "first-digital-usd",
    "PYUSD": "paypal-usd",
    "TUSD" : "true-usd",
    "USDP" : "paxos-standard"
}
coingecko_network_id_dict: dict = {
    "ethereum" : "eth",
    "binance_smart_chain" : "bsc",
    "arbirtum_one" : "arbitrum",
    "base" : "base",
    "solana" : "solana",
    "tron" : "tron",
    "sui" : "sui-network"
}


PRIORITY_STABLECOINS = ["USDC", "USDT", "FDUSD", "TUSD", "PYUSD", "USDP"]

async def httpx_request_to_coingecko(url:str, headers:dict, querystring:dict | None) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
    return data

def _get_target_quote_token(base_token:str, chain: str, coin_chain_info_all: dict) -> str:
    if base_token == "USDC":
        # USDC 분석 시에는 USDT를 최우선으로, 그 뒤는 나머지 순서대로
        candidates = ["USDT"] + [c for c in PRIORITY_STABLECOINS if c not in ["USDC", "USDT"]]
    else:
        # 그 외 코인 분석 시에는 USDC를 최우선으로
        candidates = ["USDC"] + [c for c in PRIORITY_STABLECOINS if c not in  ["USDC", base_token]]

    for quote_candidate in candidates:
        # 해당 후보 코인이 '이 체인'에 존재하는지 확인
        # coin_chain_info_all[코인] 딕셔너리에 'chain' 키가 있는지 확인
        if chain in coin_chain_info_all.get(quote_candidate, {}):
            return quote_candidate 

    return None

def filter_by_quote_token(pools:dict[str,list[dict]], target_base_token:str, coin_chain_info_all: dict) -> dict[str,list[dict]]:
    # pools는 chain별로 pool list를 담고 있는 dict
    filtered_pools_per_chain: dict[str,list[dict]] = {}
    for chain in pools.keys():
        target_quote_token = _get_target_quote_token(base_token=target_base_token, chain=chain, coin_chain_info_all=coin_chain_info_all)
        if target_quote_token is None:
            # 해당 체인에서 스왑 대상 토큰이 없으면 패스
            continue
        target_address_list = [coingecko_network_id_dict[chain] + "_" + coin_chain_info_all[target_quote_token][chain]['contract_address'].lower(), coingecko_network_id_dict[chain] + "_" + coin_chain_info_all[target_base_token][chain]['contract_address'].lower()]
        # 기본적으로 컨트랙트 주소는 대소문자 구분을 하지 않지만, 파이썬 안에서는 문자열이 대소문자를 구별하므로 lower() 처리하여 값 비교.
        for pool in pools[chain]:
            # pools[chain]: list[dict], pool: dict
            if pool['relationships']['quote_token']['data']['id'].lower() in target_address_list and \
                pool['relationships']['base_token']['data']['id'].lower() in target_address_list:
                 if chain not in filtered_pools_per_chain:
                      filtered_pools_per_chain[chain] = []
                 filtered_pools_per_chain[chain].append(pool)
    return filtered_pools_per_chain

def aggregate_in_one_chain_CPMM(filtered_pools: list[dict], target_token:str, stress_test_value: float) -> float:
    # 해당 pool의 전체 유동성 => 예를들어, USDT-USDC pool이라면, USDT와 USDC의 합산 금액    
    total_liquidity = 0.0
    weighted_price_sum = 0.0
    valid_pools_data = []

    for pool in filtered_pools:
        try:
            reserve_usd = float(pool["attributes"].get("reserve_in_usd", 0))
            if reserve_usd <= 0:
                continue

            base_token = pool['attributes']['name'].split('/')[0].strip().upper()
            if base_token == target_token:
                # 여기서 보는 price는 분석 대상 코인을 quote token으로 살 때의 가격.
                # 예를 들어, USDT를 분석 대상 코인으로 보는 경우, USDT가 base token인 pool에서는 base_token_price_quote_token 값을 사용해야 함.
                # e.g., USDT / USDC 에서 분석 대상이 USDT인 경우는 응답에서 USDT가 base token. USDC가 quote token
                # 분석 대상 코인이 분자에 와야함. => USDT가 현재 0.XX USDC 이구나! => USDT를 매도하면 얻는 USDC 양이구나!   
                price = float(pool['attributes'].get('base_token_price_quote_token', 0))
            else:
                price = float(pool['attributes'].get('quote_token_price_base_token', 0))
            if price <= 0:
                continue
            
            total_liquidity += reserve_usd
            weighted_price_sum += reserve_usd * price # 가중평균 가격 계산용
            valid_pools_data.append({
                "reserve_usd": reserve_usd,
                "price": price
            })
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Skipping pool due to missing or invalid data: {e}")
            continue
    if total_liquidity == 0:
        return 100.0 # 유동성이 없는 경우 슬리피지를 100%로 간주
    
    # total_liquidity는 달러 단위, weighted_price_sum은 스왑 결과 토큰 단위 
    # 스왑 결과 토큰의 usd 가격 * weighted_price_sum / total_liquidity
    # 하지만, 스왑 결과 토큰은 안정된 스테이블 코인으로 간주하므로 따로 곱할 필요는 없음.
    weighted_price = weighted_price_sum / total_liquidity

    AMPLIFICATION_FACTOR = 100.0  # Uniswap V2의 경우 1.0

    # Uniswap V2의  곡선 적분 => 수량 곱이 일정하고, 가치는 정확히 반반.
    # 1. 풀의 초기 상태 역산
    y_virtual = total_liquidity / 2 * AMPLIFICATION_FACTOR# 양쪽 토큰이 절반씩 있다고 가정 y_virtual의 단위는 usd, 스왑대상 토큰 단위 둘 다 됨(안정된 스테이블 코인 가정)
    x_virtual = y_virtual / weighted_price # 즉, y_virtual을 토큰 단위로 보면, x_virtual도 토큰 단위.

    # 2. AMM 공식 대입 (output 계산)
    delta_x = stress_test_value
    delta_y = y_virtual * (delta_x / (x_virtual + delta_x))

    # 3. 슬리피지 계산
    # 우리가 받게 되길 기대한 양은 현재가로 전체를 받을 양.
    ideal_output = stress_test_value * weighted_price # 즉, 스왑대상 토큰의 단위.

    slippage = (ideal_output - delta_y) / ideal_output * 100  # 백분율로 표현

    return slippage

def solve_stable_swap_y(x_new: float, D: float, A: float, n: int=2) -> float:
    """
    Curve Finance Stableswap Y Solver (Corrected Newton-Raphson)
    Based on Curve's Vyper implementation.
    """
    # Ann = A * n^n (n=2 이므로 n^n = 4)
    Ann = A * 4 
    
    # c calculation
    # c = (D^(n+1)) / (n^n * product(x_i) * A * n^n)
    # n=2 일 때: c = D^3 / (4 * x_new * Ann)
    c = (D ** 3) / (4 * x_new * Ann)
    
    # b calculation
    # b = S + D / Ann  (여기서 S는 x_new를 의미)
    b = x_new + (D / Ann)
    
    # 초기값 y = D
    y = D
    
    # Newton-Raphson Iteration
    for _ in range(255):
        y_prev = y
        
        # y_next = (y^2 + c) / (2y + b - D)
        y_numerator = (y ** 2) + c
        y_denominator = (2 * y) + b - D
        
        if y_denominator == 0:
            return y
            
        y = y_numerator / y_denominator
        
        # 수렴 체크 (1 미만 차이면 종료)
        if abs(y - y_prev) <= 1:
            return y
            
    return y

def aggregate_in_one_chain_CURVE_STABLESWAP(filtered_pools: list[dict], target_token:str) -> float:
    # 해당 pool의 전체 유동성 => 예를들어, USDT-USDC pool이라면, USDT와 USDC의 합산 금액 (USD 단위) 
    total_liquidity = 0.0
    weighted_price_sum = 0.0
    valid_pools_data = []

    # 데이터 집계
    for pool in filtered_pools:
        try:
            reserve_usd = float(pool["attributes"].get("reserve_in_usd", 0))
            if reserve_usd <= 0:
                continue

            base_token = pool['attributes']['name'].split('/')[0].strip().upper()
            if base_token == target_token:
                # 여기서 보는 price는 분석 대상 코인을 quote token으로 살 때의 가격.
                # 예를 들어, USDT를 분석 대상 코인으로 보는 경우, USDT가 base token인 pool에서는 base_token_price_quote_token 값을 사용해야 함.
                # e.g., USDT / USDC 에서 분석 대상이 USDT인 경우는 응답에서 USDT가 base token. USDC가 quote token
                # 분석 대상 코인이 분자에 와야함. => USDT가 현재 0.XX USDC 이구나! => USDT를 매도하면 얻는 USDC 양이구나!
               
                price = float(pool['attributes'].get('base_token_price_quote_token', 0))
            else:
                price = float(pool['attributes'].get('quote_token_price_base_token', 0))
            if price <= 0:
                continue
            
            total_liquidity += reserve_usd
            weighted_price_sum += reserve_usd * price # 가중평균 가격 계산용
            valid_pools_data.append({
                "reserve_usd": reserve_usd,
                "price": price
            })
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Skipping pool due to missing or invalid data: {e}")
            continue
    if total_liquidity == 0:
        return 100.0 # 유동성이 없는 경우 슬리피지를 100%로 간주
    
    # total_liquidity는 달러 단위, weighted_price_sum은 스왑 결과 토큰 단위 
    # 스왑 결과 토큰의 usd 가격 * weighted_price_sum / total_liquidity
    # 하지만, 스왑 결과 토큰은 안정된 스테이블 코인으로 간주하므로 따로 곱할 필요는 없음.
    weighted_price = weighted_price_sum / total_liquidity

    # StableSwap의 곡선 적분 
    # Parameter Setting
    A = 50  # Amplification coefficient (100~1000 사이 값이 일반적)

    # 초기 상태는 Balanced 상태로 가정
    # D = total invariant
    # y_old: quote token 양
    # x_old: base token 양
    y_old = total_liquidity / 2  # quote token 양 (안정 스테이블 코인이므로, USD, 토큰 단위 모두 가능)
    # x_old = y_old / weighted_price  # base token 양 (토큰 단위)
    x_old = total_liquidity / 2
    # Curve 에서는 초기 상태가 50:50이라고 가정한다면 D ≈ x_amount + y_amount *주의 => 여기에서는 단위 통일 피ㄹ요함.
    D = (x_old) + y_old  # USD 단위로 invariant 계산

    delta_x = total_liquidity * 0.01
    x_new = x_old + delta_x

    # 공식에 넣을 때는 x,y 단위 통일이 필요하지만, curve는 보통 같은 가치를 토큰끼리 하므로 그냥 raw amount 사용
    # A를 100으로 두었으므로 미세한 차이는 무시 가능
    y_new = solve_stable_swap_y(x_new=x_new, D=D, A=A, n=2)
    delta_y = y_old - y_new

    # 슬리피지 계산
    ideal_output = delta_x * weighted_price 
    real_output = delta_y

    if ideal_output > 0:
        slippage = (ideal_output - real_output) / ideal_output * 100  # 백분율로 표현
    else:
        slippage = 0.0
    
    if slippage < 0:
        slippage = 0.0
    
    return slippage

async def stablecoin_DEX_aggregator_simulation(stablecoin: str, coin_chain_info_all: dict, stress_test_value: float) -> dict:
    # 상위 20개의 pool에 대해서 리스크 측정 대상 스테이블 코인의 DEX 스왑 시뮬레이션 수행: Slippage 측정
    # 매도 스트레스 테스트 밸류는 전체 공급량의 0.01%로 설정하여 슬리피지 정보를 파악.
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}
    # 주의: 분석 대상 스테이블 코인은 당연히 목표 체인 위에 있지만, quote token(즉, 스왑 대상 토큰)은 반드시 그렇다는 보장이 없음.
    # 현재 coin_chain_info_all dict에는 각 코인별로 지원하는 체인 정보를 담아놓음
    # 역으로, 체인별로 지원하는 토큰 리스트를 생성하여 만일 USDC, USDT가 지원되지 않는 체인이라면, 다른 quote token을 선택하도록 해야 함. => _target_quote_token 함수 참조  
    coros:list[asyncio.Future] = []
    for chain in coin_chain_info_all[stablecoin].keys():
        url = f"https://api.coingecko.com/api/v3/onchain/networks/{coingecko_network_id_dict[chain]}/tokens/{coin_chain_info_all[stablecoin][chain]['contract_address']}/pools"
        querystring = {'include': 'base_token,quote_token,dex'}
        coros.append(httpx_request_to_coingecko(url=url,headers=headers,querystring=querystring))
    dex_simulation_response = await asyncio.gather(*coros)
    pools: dict[str,list[dict]] = {chain: dex_simulation_response[i]['data'] for i, chain in enumerate(coin_chain_info_all[stablecoin].keys())}
    filtered_pools_per_chain: dict[str,list[dict]] = filter_by_quote_token(pools=pools, target_base_token=stablecoin, coin_chain_info_all=coin_chain_info_all)
    slippage_per_chain: dict[str, float] = {}
    for chain, filtered_pools in filtered_pools_per_chain.items():
        slippage_per_chain[chain] = aggregate_in_one_chain_CURVE_STABLESWAP(filtered_pools=filtered_pools, target_token=stablecoin)

    return slippage_per_chain

async def holder_concentration(coin_chain_info: dict) -> dict:
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}
    chains = []
    coros:list[asyncio.Future] = []
    for chain in coin_chain_info.keys():
        if chain != 'tron':
            url = f"https://api.coingecko.com/api/v3/onchain/networks/{coingecko_network_id_dict[chain]}/tokens/{coin_chain_info[chain]['contract_address']}/info"
            chains.append(chain)
            coros.append(httpx_request_to_coingecko(url=url,headers=headers,querystring=None))
    token_infos = await asyncio.gather(*coros)
    
    results: dict[str,dict] = {chain: token_info['data']['attributes']['holders'] for chain, token_info in zip(chains,token_infos)}
    return results

async def historical_supplies_charts_by_coin(stablecoin: str) -> dict[list]:
    DAYS = '31' # 최근 7일간의 데이터
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}
    querystring = {"vs_currency":"usd","days":DAYS,"interval":"daily","precision":"full"}
    
    url = f"https://api.coingecko.com/api/v3/coins/{coingecko_token_id_dict[stablecoin]}/market_chart"
    logger.info(f"Request to Coingecko API...")
    data = await httpx_request_to_coingecko(url=url,headers=headers,querystring=querystring)
    logger.info(f"Coingecko API responsed")    
    return data

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
