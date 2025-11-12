from common.schema import Indices, Index, RfRResponse, RfRRequest
from mcp.server.fastmcp import FastMCP
from datetime import datetime
from app.tools import analyze_risk
import asyncio, json, logging

# Initialize FastMCP server
rfr_server = FastMCP("RfR Server")

logger = logging.getLogger("RFR SERVER")
logger.setLevel(logging.DEBUG)

@rfr_server.tool(
    name="analyze_stablecoin_risk",
    description="Analyze the risk of a stablecoin based on its reserve report.",
    # structured_output=True
)
def analyze(request: dict) -> dict:
    request = RfRRequest(**request)
    try:
        request.validate()
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {"error": str(e)}
    try:
        response: RfRResponse = analyze_risk(request)
    except Exception as e:
        logger.error(f"Error during risk analysis: {e}")
        response = RfRResponse()
        return response
    return response

if __name__ == "__main__":
    logger.info("RfR Server Initiated")
    if input("Hi: ") == "hi":
        print("Your welcome")
    #rfr_server.run(transport="stdio") # TODO -> Docker 활용 시 transport 계층 수정 필요할 수 있음.





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