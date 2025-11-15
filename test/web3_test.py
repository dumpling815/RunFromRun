import requests, os
from web3 import Web3
from decimal import Decimal
ETH_RPC='https://ethereum-rpc.publicnode.com'

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

CHAINS = {
    "ethereum": {
        "type": "evm",
        "rpc_env": "ETH_RPC",
        "contract": "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    }
}

def get_total_supply_evm(cfg: dict) -> Decimal:
    rpc_url = ETH_RPC
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(cfg["contract"]),
        abi=ERC20_ABI,
    )
    raw_supply = contract.functions.totalSupply().call()
    decimals = contract.functions.decimals().call()

    return Decimal(raw_supply) / (Decimal(10) ** decimals)

def get_usdt_supply_by_chain():
    results = {}
    total = Decimal(0)

    for name, cfg in CHAINS.items():
        t = cfg["type"]
        if t == "evm":
            supply = get_total_supply_evm(cfg)
        else:
            continue  # 아직 안 구현한 타입이면 일단 패스

        results[name] = supply
        total += supply

    return results, total


if __name__ == "__main__":
    supplies, total = get_usdt_supply_by_chain()

    print("=== USDT total supply by chain ===")
    for chain, value in supplies.items():
        print(f"{chain:10s}: {value:,.6f} USDT")

    print(f"\n== Global total (approx) ==\n{total:,.6f} USDT")