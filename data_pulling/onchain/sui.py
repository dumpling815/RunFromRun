from common.settings import API_KEYS, API_URLS, CHAIN_RPC_URLS
import httpx
# https://docs.sui.io/sui-api-ref#suix_getallbalances

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
    total_supply_dict: str = await _call_contract(rpc_url, cfg["contract"], "suix_getTotalSupply")
    decimals_dict: str = await _call_contract(rpc_url, cfg["contract"], "suix_getCoinMetadata")

    try:
        total_supply_raw = int(total_supply_dict['result']['value'])
        decimals_raw = int(decimals_dict['result']['decimals'])
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"Unexpected Sui total supply or decimals response for {cfg['contract']}: {total_supply_dict}, {decimals_dict}") from e

    total_supply = float(total_supply_raw) / (10 ** decimals_raw)
    return total_supply

