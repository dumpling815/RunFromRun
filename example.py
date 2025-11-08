# main.py
from mcp.server.fastmcp import FastMCP

# MCP 서버 인스턴스 생성
mcp = FastMCP("Example MCP Server")


# 'add'라는 이름의 도구(Tool) 정의
@mcp.tool()
def add(a: int, b: int) -> int:
    """두 숫자를 더합니다."""
    return a + b

@mcp.tool()
def echo(text: str) -> str:
    """입력된 텍스트를 그대로 반환합니다."""
    return text

if __name__ == "__main__":
    mcp.run(transport="stdio")

# 서버 실행 (uvicorn과 같은 ASGI 서버와 함께 사용)
# 이 파일을 직접 실행하기보다는 ASGI 서버를 통해 실행합니다.