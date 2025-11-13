from data_pulling.openfigi_api import replace_cusip_openfigi
from data_pulling.dataframe_process import get_tables_from_pdf

if __name__ == "__main__":
    USDC_PDF_PATH = "./test/report/USDC.pdf"
    USDT_PDF_PATH = "./test/report/USDT.pdf"
    FDUSD_PDF_PATH = "./test/report/FDUSD.pdf"
    PYUSD_PDF_PATH = "./test/report/PYUSD.pdf"
    TUSD_PDF_PATH = "./test/report/TUSD.pdf"
    USDP_PDF_PATH = "./test/report/USDP.pdf"
   
    df_list = get_tables_from_pdf(pdf_path=USDC_PDF_PATH, stablecoin="USDC")
    result = []
    for table in df_list:
        print(f"################before################")
        print(table)
        print(f"################before################")
        table_out = table.map(replace_cusip_openfigi)
        print(f"################after################")
        print(table_out)
        print(f"################after################")
    



