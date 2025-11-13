from common.schema import RfRResponse, RfRRequest
from mcp.server.fastmcp import FastMCP
from app.tools import analyze
import logging

# Initialize FastMCP server
mcp = FastMCP("RfR Server")

logger = logging.getLogger("RFR SERVER")
logger.setLevel(logging.DEBUG)

@mcp.tool(
        name="RunFromRun-MCP-SERVER",
        description="Analyze Stable Coin Risk with given Report PDF."
)
def analyze_stablecoin_risk(request: RfRRequest) -> dict:
    try:
        request.validate()
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {"error": str(e)}
    response: RfRResponse = analyze(request)
    return response

def main():
    logger.info("RfR Server Initiating...")
    mcp.run()
    logger.info("Finished")

if __name__ == "__main__":
    main()