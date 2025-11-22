from data_pulling.onchain.get_onchain import get_total_supply_each_chain
from common.settings import AVAILABLE
import asyncio, yaml
async def main():
    with open("./data_pulling/onchain/chain_config.yaml", 'r') as f:
        coin_chain_info:dict = yaml.full_load(f)
    with open("./data_pulling/onchain/ABI.yaml", 'r') as f:
        ABI_dict = yaml.full_load(f)
    for stablecoin in AVAILABLE.COINS:
        total_supplies = await get_total_supply_each_chain(coin_chain_info=coin_chain_info[stablecoin], ABI_dict=ABI_dict)
        print(total_supplies)
        outstanding_token = sum(total_supplies.values())
        print(f"Outstanding {stablecoin} token: {outstanding_token}")
        for chain, supply in total_supplies.items():
            print(f"{chain} ratio: {supply / outstanding_token * 100:.2f}%")
        print("#" * 30)


if __name__ == "__main__":
    asyncio.run(main())