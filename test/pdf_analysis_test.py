import logging, asyncio
from pathlib import Path
from data_pulling.offchain.pdf_analysis import analyze_pdf, plotit_asset_tables
if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    pdf_path = Path("./test/report/USDT.pdf") # [DEBUG] 테스트용 PDF 경로 => USDT 정상 작동 확인
    result_table = asyncio.run(analyze_pdf(pdf_path, stablecoin="USDT"))
    plotit_asset_tables(stablecoin="USDT", asset_table=result_table)
    
    # pdf_path = Path("./test/report/USDC.pdf") # [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(pdf_path, stablecoin="USDC"))
    # plotit_asset_tables(stablecoin="USDC", asset_table=result_table)

    # pdf_path = Path("./test/report/FDUSD.pdf") # [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(pdf_path, stablecoin="FDUSD"))
    # plotit_asset_tables(stablecoin="FDUSD", asset_table=result_table)

    # pdf_path = Path("./test/report/PYUSD.pdf") # [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(pdf_path, stablecoin="PYUSD"))
    # plotit_asset_tables(stablecoin="PYUSD", asset_table=result_table)

    # pdf_path = Path("./test/report/TUSD.pdf") # [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(pdf_path, stablecoin="TUSD"))
    # plotit_asset_tables(stablecoin="TUSD", asset_table=result_table)

    # pdf_path = Path("./test/report/USDP.pdf") # [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(pdf_path, stablecoin="USDP"))
    # plotit_asset_tables(stablecoin="USDP", asset_table=result_table)