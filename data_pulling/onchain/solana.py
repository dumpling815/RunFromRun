from common.settings import CHAIN_RPC_URLS
import httpx
# https://solana.com/ko/docs/rpc/json-structures

async def _call_contract(rpc_url: str, contract_address: str, function_selector: str) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": function_selector,
        "params": [contract_address],
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(rpc_url, json=payload)
    response.raise_for_status()
    data = response.json()
    return data

async def get_total_supply(chain: str, cfg: dict) -> float:
    rpc_url = getattr(CHAIN_RPC_URLS,chain.upper())
    total_supply_dict: dict = await _call_contract(rpc_url, cfg["contract"], "getTokenSupply")
    try:
        total_supply = float(total_supply_dict['result']["value"]["amount"]) / (10 ** total_supply_dict['result']["value"]["decimals"])
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"Unexpected Solana total supply response for {cfg['contract']}: {total_supply_dict}") from e
    return total_supply