from common.settings import API_KEYS, API_URLS, CHAIN_RPC_URLS
import httpx 
# https://developers.tron.network/v4.4.0/reference/method

async def _call_contract(rpc_url: str, contract_address: str, function_selector: str) -> dict:
    headers = {"Content-Type": "application/json"}
    payload = {
        'contract_address': contract_address,
        'owner_address': contract_address,
        'function_selector': function_selector,
        'parameter': '',
        'visible': True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(rpc_url, headers=headers, json=payload)

    response.raise_for_status()
    data = response.json()
    return data

async def get_total_supply(chain: str, cfg: dict) -> float:
    rpc_url = getattr(CHAIN_RPC_URLS,chain.upper())
    endpoint = rpc_url.rstrip('/') + '/wallet/triggerconstantcontract'
    total_supply_dict: dict = await _call_contract(endpoint, cfg["contract"], "totalSupply()")
    decimals_dict: int = await _call_contract(endpoint, cfg["contract"], "decimals()")
    try:
        total_supply_raw = int(total_supply_dict['constant_result'][0],16)
        decimals_raw = int(decimals_dict['constant_result'][0],16)
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"Unexpected Tron total supply or decimals response for {cfg['contract']}: {total_supply_dict}, {decimals_dict}") from e
    total_supply = float(total_supply_raw) / (10 ** decimals_raw)

    return total_supply
