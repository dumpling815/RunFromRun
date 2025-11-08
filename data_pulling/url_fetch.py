import hashlib
import json, os, re
from typing import Iterable, Optional, TypeVar
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from common.settings import urls

PDF_URL = 'https?:\/\/[^\s"]+\.pdf'

USDT_TETHER_REPORT_URL = "https://tether.to/ru/transparency/?tab=reports "
USDT_PDF_URL = "https://assets.ctfassets.net/vyse88cgwfbl/2SGAAXnsb1wKByIzkhcbSx/9efa4682b3cd4c62d87a4c88ee729693/ISAE_3000R_-_Opinion_Tether_International_Financial_Figure_RC187322025BD0201.pdf"

Html = TypeVar('Html', bool, str)

def _get_html(target_url:str) -> Html:
    try:
        response = requests.get(url=target_url)
        return response.text
    except requests.exceptions as e:
        print(f"Exception occurs: {e}")
        return False
    except requests.HTTPError as he:
        print(f"Error during HTTP: {he}")
        return False

def extract_pdf_links(target_url: str):
    # Extract all PDF links from given URL's HTML file
    html = _get_html(target_url=target_url)
    if isinstance(html,str):
        soup = BeautifulSoup(html, 'html.parser')
    else:
        print(f"Invalid URL... can't get html source")