from data_pulling.onchain.coingecko_api import get_asset_platforms, token_lists_by_asset_platform
from common.settings import AVAILABLE
import asyncio

async def print_token_assetplatforms():
    platforms = await get_asset_platforms()
    for platform_id, platform_info in platforms.items():
        if platform_id in ['ethereum','solana','tron','base','sui', 'binance-smart-chain', 'arbitrum-one']:
            print(f"Platform ID: {platform_id}")
            token_list = await token_lists_by_asset_platform(platform_id)
            print(f"Number of tokens: {len(token_list)}")
            for token in token_list:
                if token['symbol'] in AVAILABLE.COINS:
                    print(f"  - Token Symbol: {token['symbol']}, Name: {token['name']}, Address: {token['address']}")
            #print(f"Details: {platform_info}")
            print("-" * 40)



async def main():
    await print_token_assetplatforms()

if __name__ == "__main__":
    asyncio.run(main())