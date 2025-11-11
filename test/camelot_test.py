# Pipeline for testing RfR server.
from datetime import datetime
from data_pulling.dataframe_process import get_tables_from_pdf, get_pdf_style
from pathlib import Path
from common.settings import CAMELOT_MODE
from rich import print
import pandas as pd


# paths = [USDC_PDF_PATH, USDT_PDF_PATH, FDUSD_PDF_PATH, PYUSD_PDF_PATH, TUSD_PDF_PATH, USDP_PDF_PATH]
# for i in paths:
#     pdf_format = get_pdf_style(i)
#     print(f"{Path(i).name}: {pdf_format}")
def markdownize_tables(tables: list[pd.DataFrame]) -> list[str]:
    markdown_tables = []
    for idx, df in enumerate(tables):
        # Keep up to MAX rows per table to avoid oversized prompts (adjust as needed)
        df = df.fillna("").astype(str)
        markdown_table = df.to_markdown(index=False)
        markdown_tables.append(markdown_table)
    return markdown_tables

if __name__ == "__main__":
    ["USDT","USDC","FDUSD","PYUSD","TUSD","USDP"]

    hybrid_list = ["USDC","FDUSD","TUSD"] 
    lattice_list = ["USDT","PYUSD","USDP"]
    for coin in ["FDUSD", "TUSD"]:
        tables = get_tables_from_pdf(f"./test/report/{coin}.pdf",coin)
        print(f"==================={coin}======================")
        print(f"++++++++++++++Camelot Mode: {CAMELOT_MODE[coin]} ++++++++++++++++++")
        print(f"===================Total {len(tables)} tables extracted==============================")
        for table in tables:
            print(markdownize_tables([table])[0])
            print(f"###############################################")
        print(f"==================={coin}======================")
        print("=========================================================")
        a = input("continue?")
        if a == 'y':
            continue


