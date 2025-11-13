import hashlib
import json, os, re
from typing import Iterable, Optional, TypeVar
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from common.settings import urls

Html = TypeVar('Html', bool, str)

# [TODO] URL로 PDF 다운하는것 필요

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