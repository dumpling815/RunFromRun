# For getting onchain data from API
from common.settings import API_KEYS, API_URLS, CHAIN_RPC_URLS
from common.schema import OnChainData
from data_pulling.onchain import evm, tron, solana, sui, coingecko_api, DEX_simulate
import asyncio, yaml, logging

# Target Chain: Ethereum, Solana, Tron, Arbitrum, Base, BSC, SUI, 
# evm 기반: Ethereum, BSC, Arbitrum, Base
# tron      : trc20
# solana    : ABI 없기 때문에 직접 구현
# sui       : ABI 없기 때문에 직접 구현
# 추후 추가 가능 chain: Avalanche, Optimism, Polygon

# ERC20_ABI: 스마트 컨트랙트와 상호작용하기 위해 필요한 함수 및 이벤트의 정의를 담고 있는 JSON 형식의 배열
# 즉 아래 리스트에 사용할 함수의 정의들을 JSON 형식으로 담는 것.
# 아래 예시의 totalSupply 함수는 토큰의 총 공급량을 반환하는 함수 정의임.
# Decimal 같은 경우는 토큰의 소수점 자릿수를 반환하는 함수 정의임.
# 컨트랙트 안에서는 정수 형태로 저장하기 때문에, 소수점 자릿수를 따로 알아야 실제 토큰 수량을 계산할 수 있음.

logger = logging.getLogger("RunFromRun.Analyze.Onchain")
logger.setLevel(logging.DEBUG)


async def get_supply_each_chain(coin_chain_info:dict, ABI_dict: dict) -> dict[str, float]:    
    chains: list[str] = coin_chain_info.keys()
    coros: list[asyncio.Future] = []

    for chain, cfg in coin_chain_info.items():
        # EVM 기반 체인 처리 - Ethereum, BSC, Arbitrum, Base
        if cfg['type'] == 'evm':
            coros.append(evm.get_total_supply(chain, cfg, ABI_dict["ERC20"]))
        elif cfg['type'] == 'tron':
            coros.append(tron.get_total_supply(chain, cfg))
        elif cfg['type'] == 'solana':
            coros.append(solana.get_total_supply(chain, cfg))
        elif cfg['type'] == 'sui':
            coros.append(sui.get_total_supply(chain, cfg))
        else:
            raise NotImplementedError(f"Unsupported chain type: {cfg['type']}")
    
    # 병렬 실행으로 성능 향상
    logger.debug("Request to each chains RPC node.")
    supplies = await asyncio.gather(*coros)
    logger.debug("Chain RPC Completed")
    results: dict[str,float] = {chain: supply for chain, supply in zip(chains, supplies)}

    return results


async def get_onchain_data(stablecoin: str) -> OnChainData:
    with open("./data_pulling/onchain/chain_config.yaml", 'r') as f:
        coin_chain_info_all:dict = yaml.full_load(f)
    with open("./data_pulling/onchain/ABI.yaml", 'r') as f:
        ABI_dict = yaml.full_load(f)
    supply_per_chain_coro = get_supply_each_chain(coin_chain_info=coin_chain_info_all[stablecoin], ABI_dict=ABI_dict)
    variation_coro = coingecko_api.historical_supplies_charts_by_coin(stablecoin=stablecoin)
    holder_info_coro = coingecko_api.holder_concentration(coin_chain_info=coin_chain_info_all[stablecoin])
    supply_per_chain, variation_data, holder_info_per_chain = await asyncio.gather(supply_per_chain_coro, variation_coro, holder_info_coro)
    # supply_per_chain, holder_info_per_chain => dict[str, float] str: chain, float: 해당하는 값 
    # variation_data는 dict[str,list] 형식임.
    # DEX simulate의 경우는 위 두 가지 변수에 dependency가 있기 때문에 이후에 접근.
    
    slippage_per_chain = await coingecko_api.stablecoin_DEX_aggregator_simulation(
        stablecoin=stablecoin,
        coin_chain_info_all=coin_chain_info_all, 
        stress_test_value=sum(supply_per_chain.values()) * 0.0001
    )
    return OnChainData(
        supply_per_chain=supply_per_chain,
        variation_data=variation_data,
        holder_info_per_chain=holder_info_per_chain,
        slippage_per_chain=slippage_per_chain
    )

