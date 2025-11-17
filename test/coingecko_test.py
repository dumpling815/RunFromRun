from data_pulling.onchain.coingecko_api import get_asset_platforms, token_lists_by_asset_platform, historical_supplies_charts_by_coin
from common.settings import AVAILABLE
import matplotlib.pyplot as plt
import asyncio
from datetime import datetime, timezone

ts_ms = 1754697600000
dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
print(dt)  # 2025-xx-xx 00:00:00+00:00 이런 식으로 나옴

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
    # await print_token_assetplatforms()
    time, charts = await historical_supplies_charts_by_coin("USDT")
    times = []
    for ts_ms in time:
        times.append(datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc))
    plt.figure(figsize=(10,6))
    plt.plot(times,charts,color='red')
    plt.title(f"supply changes")
    plt.xlabel('time')
    plt.ylabel('supply')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(f'supply_changes')


if __name__ == "__main__":
    asyncio.run(main())