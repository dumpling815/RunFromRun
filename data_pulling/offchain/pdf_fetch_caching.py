# Download PDF via Given URL
from common.settings import MOUNTED_DIR
from common.schema import AssetTable
import os, requests, logging
from datetime import datetime
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
PDF_POOL_DIRECTORY = BASE_DIR / "pdfs"
PDF_POOL_DIRECTORY.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("pdf_fetch")
logger.setLevel(logging.DEBUG)

def download_and_hash_pdf(report_pdf_url: str, stablecoin: str) -> tuple[str,Path]: 
    # PDF_POOL_DIRECTORY에 pdf 다운받고, 다운받은 pdf path 반환
    # PDF는 마운트 디렉토리에 저장하지 않고, 컨테이너에 저장 => 마운트 디렉토리에는 로그 파일과 결과 파일만 저장.
    try:
        resp = requests.get(report_pdf_url, stream=True)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Exception occured while downloading pdf: {e}")
        raise RuntimeError(f"Failed to download pdf via requests: {e}")
        
    content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if content_type not in ("application/pdf", "application/octet-stream"):
        raise ValueError(f"URL is not for valid PDF file: Content-Type={content_type!r}")
    
    file_name = stablecoin.upper() + "-" + str(datetime.now()).split()[0] + ".pdf"
    pdf_path:Path = PDF_POOL_DIRECTORY / file_name

    with open(pdf_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    pdf_bytes:bytes = Path(pdf_path).read_bytes()
    pdf_hash:str = sha256(pdf_bytes).hexdigest()

    return (pdf_hash, pdf_path)

def cache_result(id:str, pdf_hash:str, asset_table:AssetTable):
    # Log file에 hash-id 기록
    # 현재 구현으로는 id는 필요 없으나, 이후 구현을 고려하여 id도 추가
    # 예를 들어, 이후 데이터 양이 많아져 DB 도입하는 경우 id 필요할 가능성 높아짐
    log_file:Path = MOUNTED_DIR / "pdfHash_id.log"
    log_line: str = pdf_hash + "_" + id + "\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

    # asset_tables 디렉토리에 (hash).json으로 asset_table 기록
    asset_table_file:Path = MOUNTED_DIR / "asset_tables" / f"{pdf_hash}.json"
    asset_table_json_str: str = asset_table.model_dump_json()
    with open(asset_table_file, "w", encoding="utf-8") as f:
        f.write(asset_table_json_str)
    
    logger.info(
        f"Cached AssetTable for pdf_hash={pdf_hash}, id={id} "
        f"to {asset_table_file} and logged to {log_file}" 
    )

def search_log(pdf_hash: str) -> bool:
    # log file에 pdf_hash가 기록되어 있으면 True 반환
    log_file:Path = MOUNTED_DIR / "pdfHash_id.log"
    if not log_file.exists():
        return False
    
    with log_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            hash_part = line.split("_",1)[0]
            if hash_part == pdf_hash:
                return True
    return False

def get_AssetTable_from_cache(pdf_hash: str) -> AssetTable:
    asset_table_file:Path = MOUNTED_DIR / "asset_tables" / f"{pdf_hash}.json"
    if not asset_table_file.exists():
        raise FileNotFoundError(f"Cached AssetTable not found for pdf_hash={pdf_hash}")
    
    json_str = asset_table_file.read_text(encoding="utf-8")
    asset_table = AssetTable.model_validate_json(json_str)

    logger.info(f"Loaded AssetTable from cache for pdf_hash={pdf_hash} ({asset_table_file})")
    return asset_table