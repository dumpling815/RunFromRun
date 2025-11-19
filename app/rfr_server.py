from common.schema import RfRResponse, RfRRequest
from mcp.server.fastmcp import FastMCP
from app.tools import analyze
import logging

# Initialize FastMCP server
mcp = FastMCP(
    name="RfR Server",
    host="0.0.0.0"
    )

logger = logging.getLogger("RFR SERVER")
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
file_handler = logging.FileHandler('rfr.log')

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)

@mcp.tool(
        name="RunFromRun-MCP-SERVER",
        description="Analyze Stable Coin Risk with given Report PDF."
)
async def analyze_stablecoin_risk(request: RfRRequest) -> RfRResponse:
    try:
        request.validate()
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return RfRResponse(
            id="Request validation error", 
            err_status=str(e), 
            stablecoin_ticker=request.stablecoin_ticker, 
            chain=request.chain, 
            provenance=request.provenance, 
            mcp_version=request.mcp_version
        )
    response: RfRResponse = await analyze(request)
    return response

def main():
    logger.info("RfR Server Initiating...")
    mcp.run(transport="streamable-http")
    logger.info("Finished")

if __name__ == "__main__":
    main()