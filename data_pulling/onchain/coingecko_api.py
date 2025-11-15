import json, re
import httpx
import coingecko_sdk
from common.settings import API_KEYS, API_URLS

async def get_asset_platforms() -> dict:
    url = f"{API_URLS.COINGECKO_DEMO_API_URL}/asset_platforms"
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url, headers=headers) 
        response.raise_for_status()
        data = response.json()

    platforms = {item['id']: item for item in data}
    return platforms

async def token_lists_by_asset_platform(asset_platform_id: str) -> list:
    url = f"{API_URLS.COINGECKO_DEMO_API_URL}/token_lists/{asset_platform_id}/all.json"
    headers = {"x-cg-demo-api-key": API_KEYS.COINGECKO}

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data['tokens']
