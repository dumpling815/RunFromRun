from index_calculation import calculator
from data_pulling.pdf_analysis import analyze_pdf_local_llm
from data_pulling.get_onchain import get_onchain_data
from common.schema import Indices, Index, AssetTable, OnChainData, CoinData, RfRRequest, RfRResponse
from datetime import datetime
import asyncio

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

def _get_indices(coin_data: CoinData) -> Indices:
    """Calculate OHS, RCR, RQS indices."""
    ohs_index: Index = calculator.calculate_ohs(coin_data=coin_data)
    rrs_index: Index = calculator.calculate_rrs(coin_data=coin_data)
    rqs_index: Index = calculator.calculate_rqs(coin_data=coin_data)
    result_indices: Indices = calculator.calculate_trs(rqs=rqs_index,rrs=rrs_index,ohs=ohs_index)
    return result_indices

def analyze_risk(request: RfRRequest) -> RfRResponse:
    """메인 프로세스: 지수 계산, 임계값 확인, 총 위험 점수 계산 및 응답 반환."""
    coin_data: CoinData = asyncio.run(_preprocess())
    indices: Indices =_get_indices(coin_data=coin_data)
    return RfRResponse(
        stablecoin_symbol = request.stablecoin_symbol,
        chain = request.chain,
        timestamp=datetime.now(),
        mcp_version=request.mcp_version,
        provenance=request.provenance,
        indices=indices
    )