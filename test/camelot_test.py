from common.settings import CAMELOT_MODE
from data_pulling.dataframe_process import get_tables_from_pdf, get_pdf_style
from data_pulling.pdf_analysis import markdownize_tables
from rich import print

if __name__ == "__main__":
    ["USDT","USDC","FDUSD","PYUSD","TUSD","USDP"]

    hybrid_list = ["USDC","FDUSD","TUSD"] 
    lattice_list = ["USDT","PYUSD","USDP"]
    for coin in lattice_list:
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


