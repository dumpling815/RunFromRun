from index_calculation.calculator import calculate_FRRS, calculate_OHS, calculate_TRS
from common.schema import AssetTable, Asset, CoinData, OnChainData
import logging

logger = logging.getLogger("CalculatorTest")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def main():
    test_asset_table = AssetTable(
        cash_bank_deposits= Asset(tier=1,amount=300000, ratio=30.0, qls_score=1.0),
        us_treasury_bills= Asset(tier=1,amount=200000, ratio=20.0, qls_score=1.0),
        gov_mmf= Asset(tier=1,amount=100000, ratio=10.0, qls_score=0.9),
        other_deposits= Asset(tier=2,amount=50000, ratio=5.0, qls_score=0.95),
        repo_overnight_term= Asset(tier=2,amount=80000, ratio=8.0, qls_score=0.9),
        non_us_treasury_bills= Asset(tier=2,amount=60000, ratio=6.0, qls_score=0.85),
        us_treasury_other_notes_bonds= Asset(tier=2,amount=40000, ratio=4.0, qls_score=0.8),
        corporate_bonds= Asset(tier=3,amount=30000, ratio=3.0, qls_score=0.7),
        precious_metals= Asset(tier=3,amount=20000, ratio=2.0, qls_score=0.6),
        digital_assets= Asset(tier=3,amount=10000, ratio=1.0, qls_score=0.4),
        secured_loans= Asset(tier=4,amount=5000, ratio=0.5, qls_score=0.2),
        other_investments= Asset(tier=4,amount=3000, ratio=0.3, qls_score=0.1),
        custodial_concentrated_asset= Asset(tier=5,amount=2000, ratio=0.2, qls_score=0.0),
        correction_value= Asset(tier=5,amount=0, ratio=0.0, qls_score=0.0),
        total= Asset(tier=0,amount=1000000, ratio=100.0, qls_score=0.0),
        cusip_appearance=True,
        pdf_hash="dummyhashvalue1234567890abcdef"
    )
    test_onchain_data = OnChainData(
        outstanding_token=1000000,
        CEX_flow_in=50000,
        CEX_flow_out=30000,
        liquidity_pool_size=200000,
        whale_asset_change=10000,
        mint_burn_ratio=1.2,
        TVL=1500000
    )
    coin_data = CoinData(
        stablecoin_ticker="TEST",
        description="Test Stablecoin",
        asset_table=test_asset_table,
        onchain_data=test_onchain_data
    )
    logger.debug(f"Asset Table set as :{test_asset_table}")
    FRRS = calculate_FRRS(coin_data=coin_data)
    OHS = calculate_OHS(coin_data=coin_data)
    print(f"FRRS: {FRRS}")
    logger.debug(f"Calculated FRRS: {FRRS}")
    logger.debug(f"Calculated OHS: {OHS}")
    

if __name__ == "__main__":
    main()