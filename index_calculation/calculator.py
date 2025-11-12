from common.schema import Index, Indices, AssetTable, Asset, CoinData
# from base_calculator import BaseIndexCalculator 이후 코드 확장 시 고려할 수 있음.
from common.settings import THRESHOLDS
import logging

logger = logging.getLogger("Calculator")
logger.setLevel(logging.DEBUG)

def calculate_rqs(coin_data: CoinData) -> Index:
    logger.info("RQS Calculation Initialized")
    asset_list: list[(str,Asset)] = coin_data.asset_table.to_list()
    for asset in asset_list:
        if asset[0] != "total":
            rqs += asset[1].ratio * asset[1].qls_score
    logger.info("RQS Calculation completed")
    return Index(name="rqs", value=rqs, threshold=THRESHOLDS.RQS)

def calculate_rrs(coin_data: CoinData) -> Index:
    return Index(name="rrs", value=rrs, threshold=THRESHOLDS.RRS)

def calculate_ohs(coin_data: CoinData) -> Index:
    pass
    # return Index(name="ohs", value=ohs, threshold=THRESHOLDS.OHS)

def calculate_trs(rqs: Index, rrs: Index, ohs: Index) -> Indices:
    trs: Index = Index(name="trs", value=rqs.value * 0.55 + rrs.value * 0.30 + ohs.value * 0.15, threshold=THRESHOLDS.TRS)
    return Indices(rrs=rrs,rqs=rqs,ohs=ohs,trs=trs)
    