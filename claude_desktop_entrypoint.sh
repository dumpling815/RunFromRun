#!/usr/bin/env bash
set -euo pipefail

# 1) 프로젝트 디렉토리로 이동
cd $HOME/Trading/RunFromRun

# 2) 도커 컨테이너들 (rfr_mcp_server, ollama) 백그라운드로 올리기
docker compose up -d

# 3) 브릿지 실행: Claude <-> HTTP MCP 서버
#    여기 URL은 MCP 서버가 실제로 리슨하는 포트/경로에 맞춰야 함
exec npx mcp-remote http://127.0.0.1:8000/mcp