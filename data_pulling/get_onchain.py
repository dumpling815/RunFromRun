# For getting onchain data from API
from common.settings import api_keys, urls
from coingecko_sdk import Coingecko
from coingecko_sdk.types.onchain import CategoryGetResponse, CategoryGetPoolsResponse
from typing import Dict, Any
from pydantic import BaseModel

USD_STABLECOIN_CATEGORY = "USD Stablecoin"

class CoinInfo(BaseModel):
    id: str
    symbol: str
    name: str


# Coingecko client leverages httpx under the hood.
client = Coingecko(
    #pro_api_key = api_keys.COINGECKO_PRO_API_KEY, # pro is for paid API plans.
    demo_api_key = api_keys.COINGECKO_DEMO_API_KEY,
    environment="demo",
    base_url = urls.COINGECKO_DEMO_API_URL
    # timeout, max_retries, default_headers, default query, http_client can be set here as well.
)

res = client.coins.get_id("usd-coin")


print(res.detail_platforms)



#api_list = client.get_api_list("")


# def _is_in_coingecko_coin_lists(id: str) -> bool:
#     try:
#         coins_list = client.get(path="/coins/categories/list", cast_to=dict(str,Any))
#     except Exception as e:
#         print(f"Error fetching coins list: {e}")
#         return False
#     for coin in coins_list:
#         if coin['id'] == id:
#             return coin    
    
# #_is_in_coingecko_coin_lists("usd-coin")
# res = client.get(path="/coins/categories/list", cast_to="APIResponse[Any]")
# print(res)
