from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from common.settings import AVAILABLE

class Asset(BaseModel):
    tier: Literal[0, 1, 2, 3, 4, 5] = Field(..., frozen=True) # 0 is for total amount
    qls_score: float = Field(..., ge=0, le=1, frozen=True)
    amount: float = Field(...,) # US dollar amount (부채의 경우 음수로 표기되는 경우도 있으므로 ge=0 삭제)
    ratio: float = Field(..., ge=0, le=100)

class AssetTable(BaseModel):
    # Tier 1 Assets
    cash_bank_deposits: Asset = Asset(tier=1, qls_score=1.0, amount=0.0, ratio=0.0)
    us_treasury_bills: Asset = Asset(tier=1, qls_score=1.0, amount=0.0, ratio=0.0)
    gov_mmf: Asset = Asset(tier=1, qls_score=0.95, amount=0.0, ratio=0.0)
    other_deposits: Asset = Asset(tier=1, qls_score=0.95, amount=0.0, ratio=0.0) 
    # Tier 2 Assets
    repo_overnight_term: Asset = Asset(tier=2, qls_score=0.9, amount=0.0, ratio=0.0)
    non_us_treasury_bills: Asset = Asset(tier=2, qls_score=0.85, amount=0.0, ratio=0.0)
    us_treasury_other_notes_bonds: Asset = Asset(tier=2, qls_score=0.8, amount=0.0, ratio=0.0)
    # Tier 3 Assets
    corporate_bonds: Asset = Asset(tier=3, qls_score=0.7, amount=0.0, ratio=0.0)
    precious_metals: Asset = Asset(tier=3, qls_score=0.6, amount=0.0, ratio=0.0)
    digital_assets: Asset = Asset( tier=3, qls_score=0.4, amount=0.0, ratio=0.0)
    # Tier 4 Assets 
    secured_loans: Asset = Asset(tier=4, qls_score=0.2, amount=0.0, ratio=0.0)
    other_investments: Asset = Asset(tier=4, qls_score=0.1, amount=0.0, ratio=0.0)
    custodial_concentrated_asset: Asset = Asset(tier=4, qls_score=0.0, amount=0.0, ratio=0.0)
    # Correction Value
    # LLM Voting으로 총액이 산출된 후, 자산별 합계가 총액과 일치하지 않는 경우 이를 보정하기 위한 항목.
    # 1 - correction_value.ratio를 신뢰도 지표로 사용할 수 있음 (보정치로 계산된 비율이 높다 => 신뢰도가 낮다)
    correction_value: Asset = Asset(tier=5, qls_score=0.0, amount=0.0, ratio=0.0)
    # Total Amount
    total: Asset = Asset(tier=0, qls_score=0.0, amount=0.0, ratio=100)

    # CUSIP이 공개되었는지 여부
    cusip_appearance: bool = False
    # PDF hash : 분석한 pdf의 hash 결과
    pdf_hash: str = Field(..., description="Downloaded PDF file hash (e.g., sha256). Same hash => same report.")

    # Pretty-printing helpers and __str__ override
    _FIELD_ORDER = [
        "cash_bank_deposits", "us_treasury_bills", "gov_mmf", "other_deposits",
        "repo_overnight_term", "non_us_treasury_bills", "us_treasury_other_notes_bonds",
        "corporate_bonds", "precious_metals", "digital_assets",
        "secured_loans", "other_investments", "custodial_concentrated_asset", 
        "correction_value"
    ]

    @staticmethod
    def _fmt_amount(v) -> str:
        if v is None:
            return "—"
        try:
            return f"{float(v):,.2f}"
        except Exception:
            return str(v)

    @staticmethod
    def _fmt_ratio(v) -> str:
        if v is None:
            return "—"
        try:
            return f"{float(v):.2f}%"
        except Exception:
            return str(v)

    @staticmethod
    def _title(name: str) -> str:
        return name.replace("_", " ")

    def __str__(self) -> str:
        header = ["Asset", "Tier", "QLS", "Amount (USD)", "Ratio"]
        rows = []
        for key in self._FIELD_ORDER:
            a: Asset = getattr(self, key)
            rows.append([
                self._title(key),
                str(a.tier),
                f"{a.qls_score:.2f}",
                self._fmt_amount(a.amount),
                self._fmt_ratio(a.ratio),
            ])

        total_line = ["TOTAL", "", "", self._fmt_amount(self.total.amount), ""]

        # Compute column widths
        cols = list(zip(*([header] + rows + [total_line])))
        widths = [max(len(str(x)) for x in col) for col in cols]

        def fmt_row(row):
            return " | ".join(str(val).ljust(widths[i]) for i, val in enumerate(row))

        sep = "-+-".join("-" * w for w in widths)
        lines = [fmt_row(header), sep] + [fmt_row(r) for r in rows] + [sep, fmt_row(total_line)]
        return "\n".join(lines)
    
    def to_list(self) -> list[(str,Asset)]:
        """Return a list of all Asset objects in the AssetTable."""
        result = [(key,getattr(self,key)) for key in self._FIELD_ORDER]
        result.append(('total',self.total))
        return result

    def to_dict(self) -> dict[str,Asset]:
        """Return a list of all Asset objects in the AssetTable."""
        result = {}
        for key in self._FIELD_ORDER:
            result[key] = getattr(self,key)
        result["total"] = self.total
        return result

# LLM 입력용 모델. to_asset_table 메서드를 통해 llm_voting 이후 AssetTable로 변환
class AmountsOnly(BaseModel):
    cash_bank_deposits: Optional[float] = Field(None)
    us_treasury_bills: Optional[float] = Field(None)
    gov_mmf: Optional[float] = Field(None)
    other_deposits: Optional[float] = Field(None)
    
    repo_overnight_term: Optional[float] = Field(None)
    non_us_treasury_bills: Optional[float] = Field(None)
    us_treasury_other_notes_bonds: Optional[float] = Field(None)
    
    corporate_bonds: Optional[float] = Field(None)
    precious_metals: Optional[float] = Field(None)
    digital_assets: Optional[float] = Field(None)
    
    secured_loans: Optional[float] = Field(None)
    other_investments: Optional[float] = Field(None) 
    custodial_concentrated_asset: Optional[float] = Field(None)

    # correction value는 LLM 응답 후 계산되므로 입력 모델에는 포함하지 않음.

    total: float = Field(..., ge=0)

    def to_asset_table(self, cusip_appearance: bool, pdf_hash: str) -> AssetTable:
        asset_table = AssetTable(cusip_appearance=cusip_appearance, pdf_hash=pdf_hash)
        cumulative = 0.0
        for field_name, value in self.model_dump().items():
            if field_name != "total" and value is not None:
                cumulative += value
                getattr(asset_table, field_name).amount = value
                getattr(asset_table, field_name).ratio = (value / self.total) * 100 if self.total > 0 else 0
        asset_table.correction_value.amount = max(0.0, self.total - cumulative)
        asset_table.correction_value.ratio = (asset_table.correction_value.amount / self.total) * 100 if self.total > 0 else 0
        asset_table.total.amount=self.total
        return asset_table

class OnChainData(BaseModel):
    outstanding_token: float = Field(..., ge=0)
    shifting_data: dict[list] = Field(..., description="Changes in price, market cap, total volume.(30 Days default)")
    CEX_flow_in: float = Field(..., ge=0)
    CEX_flow_out: float = Field(..., ge=0)
    liquidity_pool_size: float = Field(..., ge=0) # liquidity pool depth
    whale_asset_change: float = Field(..., description="Change in whale assets (in USD)")
    mint_burn_ratio: float = Field(..., ge=0, description="Ratio of minting to burning activities")
    TVL: float = Field(..., ge=0, description="Total Value Locked in USD")
    
class CoinData(BaseModel):
    stablecoin_ticker: str = Field(..., pattern="^[A-Z]{3,5}$", description="Stablecoin symbol (3-5 uppercase letters)")
    description: str | None = None
    asset_table: AssetTable
    onchain_data: OnChainData

class Index(BaseModel):
    name : str = Field(..., pattern="^[A-Z]*$", min_length=3, max_length=4)
    value: float = Field(..., ge=0, le=100, description="Index value between 0 and 100")
    threshold: float = Field(..., ge=0, le=100, description="Threshold value between 0 and 100")
    def threshold_check(self) -> bool:
        """Check if the index value exceeds the threshold."""
        return self.value > self.threshold

class Indices(BaseModel):
    index_list: list[Literal['FRRS', 'OHS', 'TRS']] = ['FRRS', 'OHS', 'TRS']
    FRRS: Index
    OHS: Index
    TRS: Index

class RiskResult(BaseModel):
    coin_data: CoinData
    indices: Indices
    analysis: str

class Provenance(BaseModel):
        report_issuer: str = Field(..., pattern=r"^[\w -]{3,50}$", description="Issuer of the report (3-50 characters)")
        report_pdf_url: str = Field(..., pattern=r"^https?://[^\s/$.?#].[^\s]*$", description="URL of the coin issuer's official report pdf")

class RfRRequest(BaseModel):
    stablecoin_ticker: str = Field(..., pattern=r"^[A-Z]{3,5}$", description="Stablecoin symbol (3-5 uppercase letters)")
    provenance: Provenance

    # mcp_version의 경우, 처음 도커 컨테이너 이미지 빌드 시점에 사용되고, 이후 서버 내부에서는 디버깅 용도로만 사용될 예정.
    mcp_version: str = Field(..., pattern=r"^v\d+\.\d+\.\d+$", description="MCP version in semantic versioning format")

    def validate(self):
        # Check if the request data is avilable and valid
        if self.stablecoin_ticker not in AVAILABLE.COINS:
            raise ValueError(f"Unsupported stablecoin symbol: {self.stablecoin_ticker}. Supported symbols: {AVAILABLE.COINS}")
        # [Deprecated]
        # if self.chain not in AVAILABLE.CHAINS:
        #     raise ValueError(f"Unsupported chain: {self.chain}. Supported chains: {AVAILABLE.CHAINS}")
        
class RfRResponse(BaseModel):
    id: str                     # 에러시 uuid 대신 일반 string 들어감
    err_status: str | None = None
    evaluation_time: datetime = datetime.now()

    stablecoin_ticker: str = Field(..., pattern=r"^[A-Z]{3,5}$", description="Stablecoin symbol (3-5 uppercase letters)")
    provenance: Provenance

    risk_result: RiskResult | None = None
    mcp_version: str = Field(..., pattern=r"^v\d+\.\d+\.\d+$", description="MCP version in semantic versioning format")