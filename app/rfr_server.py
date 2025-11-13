from common.schema import Indices, Index, RfRResponse, RfRRequest
from mcp.server.fastmcp import FastMCP
from datetime import datetime
from app.tools import analyze
import asyncio, json, logging

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





    # parameters={
    #     "type": "object",
    #     "properties": {
    #         "symbol": {"type": "string", "description": "Coin symbol (ex: USDC, USDT)"},
    #         "chain": {"type": "string", "description": "Blockchain name"},
    #         "mcp_version": {"type": "string", "description": "MCP version (ex: v1.0.0)"},
    #         "provenance": {
    #             "type": "object",
    #             "properties": {
    #                 "reports_issuer": {"type": "string", "description": "Issuer of the report"},
    #                 "reports_url": {"type": "string", "description": "URL of the report"},
    #             },
    #             "required": ["reports_issuer", "reports_url"],
    #         },
    #     },
    #     "required": ["symbol", "chain", "mcp_version", "provenance"],
    # },