from app.tools import analyze
from common.schema import RfRRequest, Provenance
import asyncio, logging

logger = logging.getLogger("RunFromRun")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

async def main():
    logger.debug("start testing overall logic")
    request = RfRRequest(
        stablecoin_ticker="USDT",
        provenance=Provenance(
            report_issuer="dummy",
            report_pdf_url="https://assets.ctfassets.net/vyse88cgwfbl/6GbUTVK4tTYAytefu5daIi/6cac18eb4b526c9c52640a3d2bed9642/ISAE_3000R_-_Opinion_Tether_International_Financial_Figure_31-10-2025.pdf"
        ),
        mcp_version="v1.0.0"
    )
    response = await analyze(request=request)
    logger.debug(response)
    return response

if __name__ == "__main__":
    response = asyncio.run(main())
    # logger.debug(response)