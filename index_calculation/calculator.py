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
    return Index(
        name="FRRS", 
        value=FRRS, 
        threshold=THRESHOLDS.FRRS,
        description="""
        FRRS (Final Reserve Risk Score) quantifies the off-chain reserve soundness of a fiat-backed stablecoin.
        It measures how safe the issuer’s disclosed reserves are relative to the outstanding issuance.

        FRRS is computed by a multiplicative model of three components:
        FRRS = min(100, 100 × RQS × TA_score × SA_score)

        Because TA_score and SA_score are near 1.0 (minor adjustments), the overall scale of FRRS
        is primarily determined by RQS, which is computed on a 0–100-like base scale.

        Where:

        1) RQS (Reserve Quality Score):
        RQS aggregates the reserve portfolio quality using the standardized AssetTable.
        For each reserve asset i:
            - Ratio_i: share of total reserves (%) from the PDF
            - QLS_i: pre-defined Quality & Liquidity Score in [0,1] for that asset tier
        Calculation:
            RQS = Σ_i (Ratio_i × QLS_i)   over all assets except total/correction.
        Interpretation:
            Higher RQS means reserves are concentrated in high-liquidity, high-quality tiers
            (cash, T-bills, gov MMFs), while lower RQS indicates exposure to illiquid/opaque items.
        Scale note:
            Ratio_i is a percent value (0–100), so RQS itself serves as the base FRRS-scale score.

        2) TA_score (Transparency Adjustment Score):
        A discrete transparency bonus/penalty based on CUSIP disclosure.
            TA_score = 1.00  if cusip_appearance == True
                    = 0.85  otherwise
        Rationale:
            Disclosing CUSIPs enables third-party verification of counterparties and asset existence,
            so non-disclosure receives an immediate reliability penalty.

        3) SA_score (Stability Adjustment Score):
        A nonlinear buffer reward based on over-collateralization.
        First compute the Collateralization Ratio (CR):
            CR = Total_Reserve_USD / Total_Supply_USD
        where Total_Reserve_USD is AssetTable.total.amount and
        Total_Supply_USD = Σ_chain supply_per_chain[chain].
        Then:
            if CR < 1.0:
                SA_score = 0
            else:
                SA_score = 1.0 + 0.05 × ln( (CR − 1.0) × 100 + 1 )
        Interpretation:
            CR < 1 implies insolvency risk (immediate zeroing).
            CR > 1 provides a safety buffer with diminishing marginal benefit,
            hence the logarithmic form.

        Overall interpretation:
        - FRRS ranges from 0 to 100, where a higher score indicates lower reserve risk.
        - The score increases when reserves are high-quality (high RQS),
        transparently disclosed (high TA_score),
        and sufficiently over-collateralized (high SA_score).
        """
    )

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
        if chain not in slippage_per_chain.keys():
            weighted_slippage += supply * 100.0
            continue
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
    return Index(
        name='OHS', 
        value=OHS, 
        threshold=THRESHOLDS.OHS,
        description="""
        OHS (On-Chain Health Score) quantifies market/behavioral risk observable on-chain.
        It captures whether the stablecoin is being trusted and traded in a healthy way
        across supported chains and venues.

        OHS is computed as a weighted sum of three sub-scores:
        OHS = 0.5 × PMCS + 0.3 × HCR + 0.2 × SMLS

        Where:

        1) PMCS (Primary Market Confidence Score):
        PMCS measures confidence in the *primary market* by detecting abnormal contractions
        in effective circulating supply.

        Step 1 — infer daily supply from market cap and price:
            Supply_t = MarketCap_t / Price_t

        Step 2 — compute daily supply shift rate:
            R_t = (Supply_{t+1} / Supply_t) − 1
        using the last ~91 days of variation_data.

        Step 3 — compute mean and standard deviation over the window:
            μ = average(R_t)
            σ = std(R_t)

        Step 4 — z-score of the most recent shift:
            Z = (R_last − μ) / σ

        Scoring:
            if Z ≥ 0:
                PMCS = 100
            else:
                PMCS = max(0, 100 − 8 × |Z|^{1.32})

        Interpretation:
            Persistent negative supply shocks (redemptions / loss of confidence) reduce PMCS
            nonlinearly; large anomalies rapidly push PMCS toward 0.

        2) HCR (Holder Concentration Risk Score):
        HCR measures systemic risk from whale concentration across chains.

        For each chain i with holder data:
            - S_i: circulating supply on chain i
            - C_{i,50}: % of supply held by top-50 holders on chain i
            (derived by summing distribution buckets in holder_info_per_chain[i])

        Chain weights:
            w_i = S_i / Σ_j S_j   over chains with holder data

        Weighted top-50 concentration:
            C_weighted = Σ_i (C_{i,50} × w_i)

        Piecewise scoring:
            if 0 ≤ C_weighted ≤ 30:
                HCR = 100 − (C_weighted / 1.5)
            if 30 < C_weighted ≤ 60:
                HCR = 80 − ((C_weighted − 30) / 1.5)
            if C_weighted > 60:
                HCR = 60 − (C_weighted − 60) × 1.5

        Interpretation:
            Lower concentration implies healthier holder distribution.
            Above 60% top-50 ownership is treated as a high-risk regime.

        Note:
            Some chains (e.g., TRON) may not provide holder distribution data; such chains
            are excluded from concentration averaging by design.

        3) SMLS (Secondary Market Liquidity Score):
        SMLS measures the DEX secondary market’s ability to absorb sell pressure
        via expected slippage under a StableSwap-style AMM model.

        Slippage estimation (per chain):
        - For each chain, slippage is numerically estimated on a StableSwap pool using a
            Newton–Raphson solver.
        - Only the top-20 liquidity pools on that chain are considered.
        - If the target stablecoin does not appear in any of these top-20 pools,
            slippage for that chain is set to 100% (interpreted as “practically no usable liquidity”).

        Weighted average slippage across chains:
            Slip_weighted = Σ_i (S_i × Slip_i) / Σ_i S_i
        where Slip_i is the expected slippage (%) from the DEX simulation on chain i.

        Mapping slippage to score:
            if Slip_weighted ≤ 0.5%:
            SMLS = clamp( 100 − ((Slip_weighted − 0.2%) / (0.5% − 0.2%)) × 20 )
            else:
            SMLS = clamp( 80 − ((Slip_weighted − 0.5%) / (2.5% − 0.5%)) × 80 )

            clamp(x) = max(0, min(100, x))

        Interpretation:
            ~0.2% slippage ≈ near-perfect liquidity (≈100),
            0.5% ≈ neutral liquidity (≈80),
            2.5%+ ≈ severe fragility (≈0).

        Practical note:
            DEX volumes are structurally smaller than CEX volumes, so slippage can be noisy
            and spike even without fundamental stress. For this reason SMLS is assigned a
            smaller weight (20%) within OHS.

        Overall interpretation:
        - OHS ranges from 0 to 100, where a higher score indicates healthier on-chain status.
        - PMCS dominates (50%) as primary-market trust and supply stability are the earliest
        on-chain stress signals.
        - HCR (30%) captures whale-driven systemic fragility.
        - SMLS (20%) reflects DEX sell-side liquidity while acknowledging its inherent noise.
        """
    )

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
    TRS: Index = Index(
        name="TRS", 
        value=offline_weight * FRRS.value + (1-offline_weight) * OHS.value, 
        threshold=THRESHOLDS.TRS,
        description="""
        TRS (Total Risk Score) is the final integrated risk score combining off-chain reserve risk (FRRS)
        and on-chain market/behavioral risk (OHS) with a time-decaying weight.

        Rationale:
        Off-chain reserve data is the fundamental anchor for fiat-backed stablecoins, but it becomes stale
        as time passes after the issuer’s report. On-chain signals update continuously, so their weight
        should increase as the report ages.

        TRS is computed as a convex combination:
        TRS = W_off(t) × FRRS + (1 − W_off(t)) × OHS

        Where:
        - t = number of days since the latest PDF report was analyzed
            t = (current_time − pdf_analysis_time).days
        - W_off(t) is the offline (reserve) weight:

        W_off(t) =
            0.7 − t / 150                    for 0 ≤ t ≤ 30
            0.5 − (t − 30) / 300            for 30 < t ≤ 180
            0                               for t > 180

        Interpretation of the schedule:
        - At t = 0 (fresh report): W_off = 0.7 → reserves dominate (70% FRRS, 30% OHS).
        - By t = 30 days: W_off ≈ 0.5 → equal weighting (50/50).
        - By t = 90 days: W_off ≈ 0.3 → on-chain signals dominate (30% FRRS, 70% OHS).
        - After t > 180 days: W_off = 0 → report is treated as expired; TRS becomes OHS only.

        Overall interpretation:
        - TRS ranges from 0 to 100, where a higher score indicates lower overall risk.
        - TRS dynamically shifts its trust from reserve quality to on-chain health as information freshness changes,
        capturing both “fundamental solvency” and “real-time market stress” in one score.
        """
    )
    logger.info(f"TRS Calculation Completed: {TRS}")
    return Indices(FRRS=FRRS,OHS=OHS,TRS=TRS)