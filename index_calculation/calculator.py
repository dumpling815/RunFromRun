from common.schema import Index, Indices, AssetTable, Asset, CoinData
# from base_calculator import BaseIndexCalculator 이후 코드 확장 시 고려할 수 있음.
from common.settings import THRESHOLDS
from numpy import log
import logging

logger = logging.getLogger("Calculator")
logger.setLevel(logging.DEBUG)

def _calculate_RQS(asset_table: AssetTable) -> float:
    logger.info("RQS Calculation Initialized")
    asset_list: list[(str,Asset)] = asset_table.to_list()
    for asset in asset_list:
        if asset[0] != "total":
            RQS += asset[1].ratio * asset[1].qls_score
    logger.info("RQS Calculation Completed")
    return float(RQS)

def calculate_FRRS(coin_data: CoinData) -> Index:
    logger.info("RQS Calculation Initialized")
    RQS = _calculate_RQS(asset_table=coin_data.asset_table)
    TA_score :float = 1.00 if coin_data.asset_table.cusip_appearance else 0.85 # Transparency Adjustment Score
    collateralization_ratio :float = coin_data.asset_table.total.amount / coin_data.onchain_data.outstanding_token
    SA_score :float = 1.0 + 0.05 * log(collateralization_ratio - 1.0) * 100 + 1 if collateralization_ratio > 1 else 0
    FRRS = min(100,100 * RQS * TA_score * SA_score)
    logger.info("FRRS Calculation Completed")
    return Index(name="FRRS", value=FRRS, threshold=THRESHOLDS.FRRS)

def calculate_OHS(coin_data: CoinData) -> Index:
    pass
    # return Index(name="ohs", value=ohs, threshold=THRESHOLDS.OHS)

def calculate_TRS(FRRS: Index, OHS: Index) -> Indices:
    TRS: Index = Index(name="TRS", value=0.7 * FRRS.value + 0.3 * OHS.value, threshold=THRESHOLDS.TRS)
    return Indices(FRRS=FRRS,OHS=OHS,TRS=TRS)
    