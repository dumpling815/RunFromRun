from common.schema import Indices, Index, RfRResponse, RfRRequest
from mcp.server.fastmcp import FastMCP
from datetime import datetime
from tools import analyze_risk
import asyncio, json

# Initialize FastMCP server
app = FastMCP("RfR Server")


@app.tool(
    name="analyze_stablecoin_risk",
    description="Analyze the risk of a stablecoin based on its reserve report.",
    input_schema={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Coin symbol (ex: USDC, USDT)"},
            "chain": {"type": "string", "description": "Blockchain name"},
            "mcp_version": {"type": "string", "description": "MCP version (ex: v1.0.0)"},
            "provenance": {
                "type": "object",
                "properties": {
                    "reports_issuer": {"type": "string", "description": "Issuer of the report"},
                    "reports_url": {"type": "string", "description": "URL of the report"},
                },
                "required": ["reports_issuer", "reports_url"],
            },
        },
        "required": ["symbol", "chain", "mcp_version", "provenance"],
    },
)
def analyze(request: dict) -> dict:
    request = RfRRequest(**request)
    try:
        request.validate()
    except ValueError as e:
        print(f"Validation error: {e}")
        return {"error": str(e)}
    try:
        response: RfRResponse = analyze_risk(request)
    except Exception as e:
        print(f"Error during risk analysis: {e}")
        return {"error": "Internal server error during risk analysis."}
    return response.dict()

if __name__ == "__main__":
    app.run(transport="stdio") # TODO -> Docker 활용 시 transport 계층 수정 필요할 수 있음.