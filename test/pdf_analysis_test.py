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
    # report_pdf_url ="https://assets.ctfassets.net/vyse88cgwfbl/6GbUTVK4tTYAytefu5daIi/6cac18eb4b526c9c52640a3d2bed9642/ISAE_3000R_-_Opinion_Tether_International_Financial_Figure_31-10-2025.pdf" # [DEBUG] 테스트용 PDF 경로 => USDT 정상 작동 확인
    # result_table = asyncio.run(analyze_pdf(id='1', report_pdf_url=report_pdf_url, stablecoin="USDT"))
    # plotit_asset_tables(stablecoin="USDT", asset_table=result_table)
    
    report_pdf_url = "https://6778953.fs1.hubspotusercontent-na1.net/hubfs/6778953/USDCAttestationReports/2025/2025%20USDC_Examination%20Report%20September%2025.pdf"# [DEBUG] 테스트용 PDF 경로
    result_table = asyncio.run(analyze_pdf(id='1', report_pdf_url=report_pdf_url, stablecoin="USDC"))
    plotit_asset_tables(stablecoin="USDC", asset_table=result_table)

    # report_pdf_url =  "https://cdn.prod.website-files.com/675ab99bf1f7ea944d49a55b/691ae730c0002ec5197b3cf0_FDUSD%20Reserve%20accounts%20Report_%20OCT%202025%20(signed%20by%20Accountant).pdf" # [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(id='1', report_pdf_url=report_pdf_url, stablecoin="FDUSD"))
    # plotit_asset_tables(stablecoin="FDUSD", asset_table=result_table)

    # report_pdf_url =  "https://file.notion.so/f/f/48c66553-99de-4e90-bfba-b5f37a8bcb0d/c02bd50d-423f-4e03-9272-6913a43c87e8/Download.pdf?table=block&id=289ca642-a48a-8064-8f01-c9c8bc246616&spaceId=48c66553-99de-4e90-bfba-b5f37a8bcb0d&expirationTimestamp=1763942400000&signature=YBiqi8NHWvb60Icptovx_Q16IkYnc8bHWVyFh4ILZJU&downloadName=Download.pdf"# [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(id='1', report_pdf_url=report_pdf_url, stablecoin="PYUSD"))
    # plotit_asset_tables(stablecoin="PYUSD", asset_table=result_table)

    # report_pdf_url = "https://truecurrencies-reports-prod.s3.us-east-2.amazonaws.com/TrueUSD/2025/11/22/2025-11-22-692174bc026550d129e542c5.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIARF65NSSFYULTP6DF%2F20251122%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20251122T182711Z&X-Amz-Expires=900&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGIaCXVzLWVhc3QtMiJHMEUCIDh4aBOXvdIkfVG7QXVNpd1dFdOQ4NWcK3UB1HilsI4pAiEAwtV8ATRxzCehQwQPW%2BZawTiYtBjm4aBY87W3i5VbGT8qrwMILBABGgwwODE1MzE4NjgyOTkiDOy%2FTB8G1HSF%2Bv5oNCqMAzxCSl4TfxkCsdBM0YjBb1eaRwmNaoorPop4utheq1PX2EOxLwveKZOFTVUeT70UXmoc5%2FhMlf4xM%2FV3blI6IZyq17LSNz3%2FjItYHiblzbL30YI0MRLWUARXRFh2dxWi3V2AU%2BdefjQ87G7Tb3gyHv58WotR1B0Z3Gj2gxS3AF8A4%2B3j7NXzpeuqmS9byGyVW36eUglHm7d5BifXD1A3%2FpckXZ0ids2DzD%2BGFCtYyS8O9cDcDGK1ard7k5%2FiWlkXXBcwOnMXbXp0yEpGH0HEUxK%2F8VuTXsvo2Xf%2BomaYBPxhWW8KxK2TMHRcgwAOQ1HQxlr4WfbtEqzsLRXt8hSmLWL6x4uUeuH%2BT5FMk3INvGOUaOlrWtxtxrAbfpoXYUVAAckgcufqSxlK8L%2F5BFsrT3VCsJYYpMFeMT36MueUAnHRERbhfb%2BtYIU%2BUJsL7TNE14jRtRLgnKyXY5P4vlGJdR8fIhBhgYNLKSRiNU2kdliMZpVHfKdgpTh9DLzh2azxH%2Frqht%2BeAZd%2FPTfJ4zD6gIjJBjqdARGoecs7rzJnJ%2FCE4Pol6ZSpXPgaKK%2FPpx8v14WbaX%2FXF2SGv7Sf%2FZAvQbJmwdcBkxEE33w3R8vE9omMPmY8nP9gjKyALBFbn3wfY%2BjxdPfn%2F6L5d7V2ntGn%2FCjst4w38KEkjoEpf3vsWiT87ruo0MK4hc3tRUND6fS5amR3siUbFYIO%2Fyux0Mi%2BQKrQYpx49J0PVKSTra%2Bv8LmBViQ%3D&X-Amz-Signature=0da26f200195832128a96ea73e5136284e80893f46587646c6a556fcbcce84f7&X-Amz-SignedHeaders=host&x-id=GetObject"# [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(id='1', report_pdf_url=report_pdf_url, stablecoin="TUSD"))
    # plotit_asset_tables(stablecoin="TUSD", asset_table=result_table)

    # report_pdf_url =  "file:///Users/minuk-0815/Downloads/Download%20(2).pdf"# [DEBUG] 테스트용 PDF 경로
    # result_table = asyncio.run(analyze_pdf(id='1', report_pdf_url=report_pdf_url, stablecoin="USDP"))
    # plotit_asset_tables(stablecoin="USDP", asset_table=result_table)