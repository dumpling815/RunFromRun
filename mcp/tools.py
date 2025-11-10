from RunFromRun.index_calculation import rrs
from data_pulling import get_macro, get_onchain, slm_ocr
from index_calculation import ohs, rqs, trs
from common.schema import Indices, Index, Request, Response
from datetime import datetime
import asyncio

async def _preprocess() -> None:
    # TODO : Implement any necessary preprocessing steps here
    pass

async def _get_indices() -> dict:
    """Calculate OHS, RCR, RQS indices."""
    ohs_index: Index = await ohs.ohs_calculator()
    rcr_index: Index = await rrs.rcr_calculator()
    rqs_index: Index = await rqs.rqs_calculator()
    return Indices(rcr=rcr_index, ohs=ohs_index, rqs=rqs_index)

def analyze_risk(request: Request) -> Response:
    """메인 프로세스: 지수 계산, 임계값 확인, 총 위험 점수 계산 및 응답 반환."""
    asyncio.run(_preprocess())
    indices: Indices = asyncio.run(_get_indices())
    indices.trs = trs.risk_calculator(indices)
    return Response(
        stablecoin_symbol = request.stablecoin_symbol,
        chain = request.chain,
        timestamp=datetime.utcnow(),
        mcp_version=request.mcp_version,
        provenance=request.provenance,
        indices=indices
    )