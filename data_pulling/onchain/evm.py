from common.settings import API_KEYS, API_URLS, CHAIN_RPC_URLS
from web3 import AsyncWeb3


async def get_total_supply(chain: str, cfg: dict, ERC20_ABI: list) -> float:
    rpc_url = getattr(CHAIN_RPC_URLS,chain.upper())
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
    try:
        contract = w3.eth.contract(
            address=AsyncWeb3.to_checksum_address(cfg["contract"]),
            abi=ERC20_ABI,
        )
        raw_supply = await contract.functions.totalSupply().call()
        decimals = await contract.functions.decimals().call()
        total_supply = float(raw_supply) / (10 ** decimals)
        return total_supply
    finally:
        await w3.provider.disconnect()