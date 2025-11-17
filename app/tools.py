from common.schema import AssetTable, OnChainData, CoinData, Index, Indices, RiskResult, RfRRequest, RfRResponse
from data_pulling.offchain.pdf_analysis import analyze_pdf
from data_pulling.onchain.get_onchain import get_onchain_data
from index_calculation import calculator
from datetime import datetime
import asyncio, logging
from uuid import uuid4 

logger = logging.getLogger("Tools")
logger.setLevel(logging.DEBUG)

async def _preprocess(id:str, report_pdf_url: str, stablecoin: str) -> CoinData:
    asset_table: AssetTable = await analyze_pdf(id=id, report_pdf_url=report_pdf_url, stablecoin=stablecoin) # 로그 기록을 위해 id 필요
    onchain_data: OnChainData = await get_onchain_data()
    coin_data = CoinData(
        stablecoin_ticker=stablecoin, 
        asset_table=asset_table, 
        onchain_data=onchain_data,  
    )
    return coin_data

def _calculate_indices(coin_data: CoinData) -> Indices:
    """Calculate OHS, RCR, RQS indices."""
    FRRS_index: Index = calculator.calculate_FRRS(coin_data=coin_data)
    OHS_index: Index = calculator.calculate_OHS(coin_data=coin_data)
    result_indices: Indices = calculator.calculate_TRS(FRRS=FRRS_index,OHS=OHS_index)
    return result_indices

def _alarm_and_complete(coin_data: CoinData, indices: Indices):
    # TODO analysis 문장 완성
    # TODO alarming 구현
    risk_result = RiskResult(
        coin_data=coin_data,
        indices=indices,
        analysis="Caution Required"
    )
    return risk_result

def analyze(request: RfRRequest) -> RfRResponse:
    # 메인 프로세스: 지수 계산, 임계값 확인, 총 위험 점수 계산 및 응답 반환
    id:str = uuid4().hex
    try:
        coin_data: CoinData = asyncio.run(_preprocess(id=id, report_pdf_url=request.provenance.report_pdf_url, stablecoin=request.stablecoin_ticker))
        indices: Indices =_calculate_indices(coin_data=coin_data)
        risk_result: RiskResult = _alarm_and_complete(coin_data=coin_data,indices=indices)
    except Exception as e:
        logger.error(f"Error during analyzing {e}")
        return RfRResponse(
            id="MCP Server Error",
            err_status=e,
            stablecoin_ticker = request.stablecoin_ticker,
            provenance=request.provenance,
            mcp_version=request.mcp_version,
        )
    return RfRResponse(
        id=id,
        evaluation_time=datetime.now(),
        stablecoin_ticker = request.stablecoin_ticker,
        provenance=request.provenance,
        risk_result=risk_result,
        mcp_version=request.mcp_version
    )