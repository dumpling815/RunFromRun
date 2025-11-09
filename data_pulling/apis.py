import os, json, re
import urllib.request
import urllib.parse

from common.settings import API_KEYS, URLS
from data_pulling.dataframe_process import get_tables_from_pdf

# CUSIP은 9자, I, O를 제외한 알파벳과 숫자 조합으로 공백이 없고, 마지막 한 글자는 체크 디지트로 숫자가 오게됨.
# CUSIP_RE = re.compile(r'\b[A-HJ-NP-Z0-9]{8}[0-9]\b')
# CUSIP_RE = re.compile(
#     r'(?<![A-Z0-9])[A-HJ-NP-Z0-9]{8}[0-9](?![A-Z0-9])',
#     flags=re.ASCII
# )

SEPS = r"[\s,|'\"\n]"  # 공백(스페이스/탭/개행), 쉼표, |, ', "
CUSIP_CORE = r'(?<![A-Z0-9])[A-HJ-NP-Z0-9]{8}[0-9](?![A-Z0-9])'  # I,O 제외 + 마지막 숫자(체크디지트)

# 좌측: 문자열 시작 ^ 또는 SEPS
# 본체: CUSIP_CORE
# 우측: 문자열 끝 $ 또는 SEPS
CUSIP_BOUNDED = re.compile(rf"(^|{SEPS})({CUSIP_CORE})(?=$|{SEPS})", flags=re.ASCII)

def _char_val(ch: str) -> int:
    if ch.isdigit():
        return ord(ch) - ord('0')
    return ord(ch) - ord('A') + 10  # A=10 ... Z=35

def cusip_check_digit_ok(cusip: str) -> bool:
    #CUSIP 체크디지트(Mod 10 Double-Add-Double) 검증. 입력은 이미 정규식으로 9자 보장.
    c = cusip.strip().upper()
    # 1~8번째 합계
    s = 0
    for i in range(8):                           # i = 0..7  (좌→우)
        v = _char_val(c[i])
        if (i + 1) % 2 == 0:                     # 2,4,6,8번째 글자만 ×2
            v *= 2
        s += (v // 10) + (v % 10)                # 자릿수 합
    check = (10 - (s % 10)) % 10
    return check == _char_val(c[8])

def find_cusips(text: str) -> list[str]:
    # 문자열에서 모든 CUSIP 토큰 후보를 찾고, 체크디지트로 최종 필터. 
    up = text.upper()
    raw = [m.group(0) for m in CUSIP_BOUNDED.finditer(up)]
    # 중복 제거 + 검증
    seen = set()
    out: list[str] = []
    for tok in raw:
        if tok in seen:
            continue
        if cusip_check_digit_ok(tok):
            out.append(tok.strip())
            seen.add(tok)
    return out

def openfigi_api_call(data: dict | None = None, method: str = "POST") -> str:
    api_key = API_KEYS.OPENFIGI
    url = URLS.OPENFIGI_MAPPING_API_URL

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers |= {"X-OPENFIGI-APIKEY": api_key}

    request = urllib.request.Request(
        url=url,
        data=data and bytes(json.dumps(data), encoding="utf-8"),
        headers=headers,
        method=method
    )

    with urllib.request.urlopen(request) as response:
        json_response_as_string = response.read().decode("utf-8")
        json_obj:list[dict] = json.loads(json_response_as_string)
        try:
            result = json_obj[0]["data"]
            final_result = result[0]
            final_result = final_result["name"] + " : " + final_result["securityType"] + " " + final_result["securityType2"]  
        except KeyError:
            final_result = "UNVALID CUSIP"
        return final_result

def replace_cusip_openfigi(target_str: str) -> str:
    # OPENFIGI를 이용하여 CUSIP으로 표기된 자산을 자연어 설명으로 변경
    # See https://www.openfigi.com/api for more information.
    api_key = API_KEYS.OPENFIGI

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers |= {"X-OPENFIGI-APIKEY": api_key}
    

    candidates = find_cusips(target_str)

    #candidates = ['912797NA1'] #[DEBUG]
    for cusip_code in candidates:
        mapping_request = [
            {"idType": "ID_CUSIP", "idValue": f"{cusip_code}"},
        ]
        response = openfigi_api_call(data=mapping_request,method="POST")
        target_str = target_str.replace(f"{cusip_code}",response)
    
    return target_str
