from data_pulling.onchain.coingecko_api import get_asset_platforms, token_lists_by_asset_platform, historical_supplies_charts_by_coin, stablecoin_DEX_aggregator_simulation
from data_pulling.onchain.get_onchain import get_supply_each_chain
from common.settings import AVAILABLE
import matplotlib.pyplot as plt
import asyncio, yaml
from datetime import datetime, timezone
from rich import print # DEBUG

async def print_token_assetplatforms():
    platforms = await get_asset_platforms()
    for platform_id, platform_info in platforms.items():
        if platform_id in ['ethereum','solana','tron','base','sui', 'binance-smart-chain', 'arbitrum-one']:
            print(f"Platform ID: {platform_id}")
            token_list = await token_lists_by_asset_platform(platform_id)
            print(f"Number of tokens: {len(token_list)}")
            for token in token_list:
                if token['symbol'] in AVAILABLE.COINS:
                    print(f"  - Token Symbol: {token['symbol']}, Name: {token['name']}, ID: {token['id']}, Address: {token['address']}")
            #print(f"Details: {platform_info}")
            print("-" * 40)



async def main():
    with open("./data_pulling/onchain/chain_config.yaml", 'r') as f:
        coin_chain_info_all:dict = yaml.full_load(f)
    with open("./data_pulling/onchain/ABI.yaml", 'r') as f:
        ABI_dict = yaml.full_load(f)

    stablecoin = "USDC"
    total_supply_per_chain = await get_supply_each_chain(coin_chain_info=coin_chain_info_all[stablecoin], ABI_dict=ABI_dict)
    stress_test_value = sum(total_supply_per_chain.values()) * 0.000001
    result = await stablecoin_DEX_aggregator_simulation(
        stablecoin=stablecoin,
        coin_chain_info_all=coin_chain_info_all, 
        stress_test_value=stress_test_value
    )
    print(result)

    print("Weigted slippage per chain:")
    weighted_slippage = 0.0
    for chain, total_supply in total_supply_per_chain.items():
        print(f"total supply of {chain}: {total_supply}, slippage: {result.get(chain, 0.0)}")
        weighted_slippage += total_supply * result.get(chain, 0.0)
    print(weighted_slippage / sum(total_supply_per_chain.values()))




if __name__ == "__main__":
    asyncio.run(main())

    # await print_token_assetplatforms()
    # time, charts = await historical_supplies_charts_by_coin("USDT")
    # times = []
    # for ts_ms in time:
    #     times.append(datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc))
    # plt.figure(figsize=(10,6))
    # plt.plot(times,charts,color='red')
    # plt.title(f"supply changes")
    # plt.xlabel('time')
    # plt.ylabel('supply')
    # plt.xticks(rotation=30, ha='right')
    # plt.tight_layout()
    # plt.savefig(f'supply_changes')