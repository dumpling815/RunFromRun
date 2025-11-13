from index_calculation import calculator
from data_pulling.pdf_analysis import analyze_pdf_local_llm
from data_pulling.get_onchain import get_onchain_data
from common.schema import Indices, Index, AssetTable, OnChainData, CoinData, RiskResult, RfRRequest, RfRResponse
from datetime import datetime
import asyncio, logging

logger = logging.getLogger("Tools")
logger.setLevel(logging.DEBUG)

async def _preprocess(pdf_path: str, stablecoin: str) -> CoinData:
    asset_table: AssetTable = await analyze_pdf_local_llm(pdf_path=pdf_path,stablecoin=stablecoin)
    onchain_data: OnChainData = await get_onchain_data()
    coin_data = CoinData(
        stablecoin_ticker=stablecoin, 
        asset_table=asset_table, 
        onchain_data=onchain_data,  
        evaluation_date=datetime.now()
    )
    return coin_data

def _calculate_indices(coin_data: CoinData) -> Indices:
    """Calculate OHS, RCR, RQS indices."""
    ohs_index: Index = calculator.calculate_ohs(coin_data=coin_data)
    rrs_index: Index = calculator.calculate_rrs(coin_data=coin_data)
    rqs_index: Index = calculator.calculate_rqs(coin_data=coin_data)
    result_indices: Indices = calculator.calculate_trs(rqs=rqs_index,rrs=rrs_index,ohs=ohs_index)
    return result_indices

def _final_conclusion(coin_data: CoinData, indices: Indices):
    # TODO analysis 문장 완성
    risk_result = RiskResult(
        indices=indices,
        coin_data=coin_data,
        analysis="Caution Required"
    )
    return risk_result

def analyze(request: RfRRequest) -> RfRResponse:
    # 메인 프로세스: 지수 계산, 임계값 확인, 총 위험 점수 계산 및 응답 반환
    try:
        coin_data: CoinData = asyncio.run(_preprocess())
        indices: Indices =_calculate_indices(coin_data=coin_data)
        risk_result: RiskResult = _final_conclusion(coin_data=coin_data,indices=indices)
    except Exception as e:
        logger.error(f"Error during analyzing {e}")
        return RfRResponse(
            evaluation_time=datetime.now(),
            stablecoin_ticker = request.stablecoin_ticker,
            chain = request.chain,
            mcp_version=request.mcp_version,
            provenance=request.provenance,
            risk_result=None
        )
    return RfRResponse(
        evaluation_time=datetime.now(),
        stablecoin_ticker = request.stablecoin_ticker,
        chain = request.chain,
        provenance=request.provenance,
        risk_result=risk_result,
        mcp_version=request.mcp_version
    )