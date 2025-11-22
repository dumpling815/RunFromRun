from common.schema import Index, Indices, AssetTable, Asset, OnChainData, CoinData
from common.settings import THRESHOLDS
from datetime import datetime
import numpy as np
import logging

logger = logging.getLogger("RunFromRun.Analyze.Calculation")
logger.setLevel(logging.DEBUG)

def _calculate_RQS(asset_table: AssetTable) -> float:
    logger.info("RQS Calculation Initialized")
    asset_list: list[(str,Asset)] = asset_table.to_list()
    RQS = 0.0
    for asset in asset_list:
        if asset[0] != "total":
            RQS += asset[1].ratio * asset[1].qls_score
    logger.info(f"RQS Calculation Completed: {RQS}")
    return float(RQS)

def calculate_FRRS(coin_data: CoinData) -> Index:
    logger.info("FRRS Calculation Initialized")
    RQS = _calculate_RQS(asset_table=coin_data.asset_table)
    TA_score :float = 1.00 if coin_data.asset_table.cusip_appearance else 0.85 # Transparency Adjustment Score
    logger.debug(f"Total amount: {coin_data.asset_table.total.amount}, Total supply: {sum(coin_data.onchain_data.supply_per_chain.values())}")
    collateralization_ratio :float = coin_data.asset_table.total.amount / sum(coin_data.onchain_data.supply_per_chain.values())
    SA_score :float = 1.0 + 0.05 * np.log((collateralization_ratio - 1) * 100 + 1) if collateralization_ratio >= 1 else 0
    logger.debug(f"TA_score: {TA_score}, SA_score: {SA_score}, Collateralization Ratio: {collateralization_ratio}")
    FRRS = min(100,100 * RQS * TA_score * SA_score)
    logger.info(f"FRRS Calculation Completed : {FRRS}")
    return Index(name="FRRS", value=FRRS, threshold=THRESHOLDS.FRRS)

# def _calculate_EFPS(shifting_data) -> float:
#     # Exchange Flow Pressure Score
#     logger.info("EFPS Calculation Initialized")
#     circulation_shift_list = []
#     for t in range(len(shifting_data['prices']) - 1):
#         circulation_shift_list.append((shifting_data['market_caps'][t+1][1] / shifting_data['prices'][t+1][1]) - (shifting_data['market_caps'][t][1] / shifting_data['prices'][t][1]))
    
#     simple_moving_average = sum(circulation_shift_list) / len(circulation_shift_list)
#     standard_deviation = np.sqrt(sum((variates - simple_moving_average)**2 for variates in circulation_shift_list) / len(circulation_shift_list))

#     z_score = ((circulation_shift_list[-1] - circulation_shift_list[-2]) - simple_moving_average) / standard_deviation
#     z_clipped = max(-2.0,min(3.0,z_score))

#     if z_clipped <= 0:
#         EFPS = max(0,min(100,80 - (z_clipped * 10)))
#     else:
#         EFPS = max(0,min(100,80 - (z_clipped * 80 / 3)))
#     logger.info("EFPS Calculation Completed")
#     return EFPS

def _calculate_PMCS(variation_data: dict[str,list]) -> float:
    logger.info("PMCS Calculation Initialized")
    supply_shift_rate_list = []
    for t in range(len(variation_data['prices']) - 1):
        supply_shift_rate_list.append((variation_data['market_caps'][t+1][1] / variation_data['prices'][t+1][1]) / (variation_data['market_caps'][t][1] / variation_data['prices'][t][1]) - 1)

    moving_avg = sum(supply_shift_rate_list) / len(supply_shift_rate_list)
    moving_std = np.sqrt(sum((variates - moving_avg)**2 for variates in supply_shift_rate_list) / (len(supply_shift_rate_list) - 1))

    z_score = (supply_shift_rate_list[-1] - moving_avg) / moving_std
    if z_score >= 0:
        return 100
    PMCS = max(0, 100 - 8 * (abs(z_score)**1.32))
    logger.info(f"PMCS Calculation Completed: {PMCS}")
    return PMCS

def _calculate_HCR(supply_per_chain:dict[str,float], holder_info_per_chain:dict[str,dict]) -> float:
    logger.info("HCR Calculation Initialized")
    total_supply = sum(supply_per_chain.values()) 
    if 'tron' in supply_per_chain: 
        total_supply - supply_per_chain['tron']
    logger.info(f"Total supply is {total_supply}")
    ratio_dict = {chain: supply_per_chain[chain] / total_supply for chain in holder_info_per_chain.keys()}
    weighted_C_50 = 0
    for chain in ratio_dict.keys():
        logger.info(f"{holder_info_per_chain[chain]['distribution_percentage']}")
        C_50_str_list = holder_info_per_chain[chain]['distribution_percentage'].values()
        C_50_float_list = [float(C_50_str) for C_50_str in C_50_str_list]
        weighted_C_50 += sum(C_50_float_list) * ratio_dict[chain]
    logger.info(f"Weighted C_50 is {weighted_C_50}")
    if weighted_C_50 >= 0 and weighted_C_50 <= 30:
        HCR = 100 - (weighted_C_50 / 1.5)
    elif weighted_C_50 > 30 and weighted_C_50 <= 60:
        HCR = 80 - (weighted_C_50 - 30) / 1.5
    else: # weighted_C_50 > 60. 위험구간
        HCR = 60 - (weighted_C_50 - 60) * 1.5
    logger.info(f"HCR Calculation Completed: {HCR}")
    return HCR

def _calculate_SMLS(supply_per_chain:dict[str,float], slippage_per_chain:dict[str,float]) -> float:
    logger.info("SMLS Calculation Initialized")
    weighted_slippage = 0.0
    for chain, supply in supply_per_chain.items():
        weighted_slippage += supply * slippage_per_chain.get(chain, 0.0)
    weighted_slippage = weighted_slippage / sum(supply_per_chain.values())

    if weighted_slippage <= 0.5:
        SMLS = max(0,min(100,100-((weighted_slippage - 0.2)/(0.5 - 0.2)*20)))
    elif weighted_slippage > 0.5:
        SMLS = max(0,min(100,80-((weighted_slippage - 0.5)/(0.25 - 0.5)*80)))
    logger.info(f"SMLS Calculation Completed: {SMLS}")
    return SMLS

def calculate_OHS(onchain_data: OnChainData) -> Index:
    logger.info("OHS Calculation Initialized")
    PMCS : float = _calculate_PMCS(onchain_data.variation_data)
    HCR : float = _calculate_HCR(supply_per_chain=onchain_data.supply_per_chain,holder_info_per_chain=onchain_data.holder_info_per_chain)
    SMLS :float = _calculate_SMLS(supply_per_chain=onchain_data.supply_per_chain, slippage_per_chain=onchain_data.slippage_per_chain)   # TODO: Not implemented yet.
    OHS = 0.5 * PMCS + 0.3 * HCR + 0.2 * SMLS
    logger.info(f"OHS Calculation Completed: {OHS}")
    return Index(name='OHS', value=OHS, threshold=THRESHOLDS.OHS)

def calculate_TRS(FRRS: Index, OHS: Index, coin_data: CoinData) -> Indices:
    logger.info("TRS Calculation Initialized")
    time_delta = datetime.now() - coin_data.asset_table.pdf_analysis_time
    if time_delta.days <= 30:
        offline_weight = 0.7 - time_delta.days / 150
    elif time_delta.days <= 180 and time_delta.days > 30:
        offline_weight = 0.5 - (time_delta.days - 30) / 300
    else:
        offline_weight = 0.0
    logger.info(f"Offline Weight: {offline_weight}")
    TRS: Index = Index(name="TRS", value=offline_weight * FRRS.value + (1-offline_weight) * OHS.value, threshold=THRESHOLDS.TRS)
    logger.info(f"TRS Calculation Completed: {TRS}")
    return Indices(FRRS=FRRS,OHS=OHS,TRS=TRS)