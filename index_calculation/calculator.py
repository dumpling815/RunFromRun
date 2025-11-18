from common.schema import Index, Indices, AssetTable, Asset, OnChainData, CoinData
from common.settings import THRESHOLDS
import numpy as np
import logging

logger = logging.getLogger("RunFromRun.Analyze.Calculation")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def _calculate_RQS(asset_table: AssetTable) -> float:
    logger.info("RQS Calculation Initialized")
    asset_list: list[(str,Asset)] = asset_table.to_list()
    RQS = 0.0
    for asset in asset_list:
        if asset[0] != "total":
            RQS += asset[1].ratio * asset[1].qls_score
    logger.debug(f"RQS Intermediate Value: {RQS}")
    logger.info("RQS Calculation Completed")
    return float(RQS)

def calculate_FRRS(coin_data: CoinData) -> Index:
    logger.info("FRRS Calculation Initialized")
    RQS = _calculate_RQS(asset_table=coin_data.asset_table)
    TA_score :float = 1.00 if coin_data.asset_table.cusip_appearance else 0.85 # Transparency Adjustment Score
    collateralization_ratio :float = coin_data.asset_table.total.amount / coin_data.onchain_data.outstanding_token
    SA_score :float = 1.0 + 0.05 * np.log((collateralization_ratio - 1) * 100 + 1) if collateralization_ratio >= 1 else 0
    logger.debug(f"TA_score: {TA_score}, SA_score: {SA_score}, Collateralization Ratio: {collateralization_ratio}")
    FRRS = min(100,100 * RQS * TA_score * SA_score)
    logger.info("FRRS Calculation Completed")
    return Index(name="FRRS", value=FRRS, threshold=THRESHOLDS.FRRS)

def _calculate_EFPS(shifting_data) -> float:
    # Exchange Flow Pressure Score
    logger.info("EFPS Calculation Initialized")
    circulation_shift_list = []
    for t in range(len(shifting_data['prices']) - 1):
        circulation_shift_list.append((shifting_data['market_caps'][t+1][1] / shifting_data['prices'][t+1][1]) - (shifting_data['market_caps'][t][1] / shifting_data['prices'][t][1]))
    
    simple_moving_average = sum(circulation_shift_list) / len(circulation_shift_list)
    standard_deviation = np.sqrt(sum((variates - circulation_shift_list)**2 for variates in circulation_shift_list) / len(circulation_shift_list))

    z_score = ((circulation_shift_list[-1] - circulation_shift_list[-2]) - simple_moving_average) / standard_deviation
    z_clipped = max(-2.0,min(3.0,z_score))

    if z_clipped <= 0:
        EFPS = max(0,min(100,80 - (z_clipped * 10)))
    else:
        EFPS = max(0,min(100,80 - (z_clipped * 80 / 3)))
    logger.info("EFPS Calculation Completed")
    return EFPS

def calculate_OHS(onchain_data: OnChainData) -> Index:
    logger.info("OHS Calculation Initialized")
    EFPS : float = _calculate_EFPS(onchain_data.shifting_data)
    # TODO: Not implemented yet.
    OHS = EFPS

    logger.info("OHS Calculation Completed")
    return Index(name='OHS', value=OHS, threshold=THRESHOLDS.OHS)

def calculate_TRS(FRRS: Index, OHS: Index) -> Indices:
    logger.info("TRS Calculation Initialized")
    TRS: Index = Index(name="TRS", value=0.7 * FRRS.value + 0.3 * OHS.value, threshold=THRESHOLDS.TRS)
    logger.info("TRS Calculation Completed")
    return Indices(FRRS=FRRS,OHS=OHS,TRS=TRS)
    