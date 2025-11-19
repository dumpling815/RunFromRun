import os
from pathlib import Path
from datetime import datetime

def cleanup_pdf(stablecoin:str):
    file_path = Path("../data_pulling/offchain/pdf") / stablecoin.upper() / "-" / str(datetime.now()).split()[0] / ".pdf"
    if Path.exists(file_path):
        os.remove(file_path)