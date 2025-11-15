from data_pulling.onchain.get_onchain import get_total_supply_each_chain
from common.settings import AVAILABLE
import asyncio
async def main():
    for stablecoin in AVAILABLE.COINS:
        total_supplies = await get_total_supply_each_chain(stablecoin)
        print(total_supplies)
        outstanding_token = sum(total_supplies.values())
        print(f"Outstanding {stablecoin} token: {outstanding_token}")
        print("#" * 30)


if __name__ == "__main__":
    asyncio.run(main())