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

@mcp.tool(
        name="RunFromRun-MCP-SERVER",
        description="Analyze Stable Coin Risk with given Report PDF."
)
def analyze_stablecoin_risk(request: RfRRequest) -> RfRResponse:
    try:
        request.validate()
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return RfRResponse(
            id="Request validation error", 
            err_status=e, 
            stablecoin_ticker=request.stablecoin_ticker, 
            chain=request.chain, 
            provenance=request.provenance, 
            mcp_version=request.mcp_version
        )
    response: RfRResponse = analyze(request)
    return response

def main():
    logger.info("RfR Server Initiating...")
    mcp.run(transport="streamable-http")
    logger.info("Finished")

if __name__ == "__main__":
    main()