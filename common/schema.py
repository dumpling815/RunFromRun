from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from common.settings import AVAILABLE
# from uuid import uuid4 # timestamp가 아닌 unique id가 필요한가? -> 만일 DB에 저장한다면 필요할 수 있음.

class Asset(BaseModel):
    tier: Literal[1, 2, 3, 4, 5] = Field(..., frozen=True)
    qls_score: float = Field(..., ge=0, le=1, frozen=True)
    amount: float | None = Field(..., ge=0) # US dollar amount
    ratio: float | None = Field(..., ge=0, le=100)

class AssetTable(BaseModel):
    # Tier 1 Assets
    cash_bank_deposits: Asset = Asset(tier=1, qls_score=1.0, amount=None, ratio=None)
    us_treasury_bills: Asset = Asset(tier=1, qls_score=1.0, amount=None, ratio=None)
    gov_mmf: Asset = Asset(tier=1, qls_score=0.95, amount=None, ratio=None)
    other_deposits: Asset = Asset(tier=1, qls_score=0.95, amount=None, ratio=None) 
    # Tier 2 Assets
    repo_overnight_term: Asset = Asset(tier=2, qls_score=0.9, amount=None, ratio=None)
    non_us_treasury_bills: Asset = Asset(tier=2, qls_score=0.85, amount=None, ratio=None)
    us_treasury_other_notes_bonds: Asset = Asset(tier=2, qls_score=0.8, amount=None, ratio=None)
    # Tier 3 Assets
    corporate_bonds: Asset = Asset(tier=3, qls_score=0.7, amount=None, ratio=None)
    precious_metals: Asset = Asset(tier=3, qls_score=0.6, amount=None, ratio=None)
    digital_assets: Asset = Asset(tier=3, qls_score=0.4, amount=None, ratio=None)
    # Tier 4 Assets 
    secured_loans: Asset = Asset(tier=4, qls_score=0.2, amount=None, ratio=None)
    other_investments: Asset = Asset(tier=4, qls_score=0.1, amount=None, ratio=None)
    custodial_concentrated_asset: Asset = Asset(tier=4, qls_score=0.0, amount=None, ratio=None)
    # Correction Value
    # LLM Voting으로 총액이 산출된 후, 자산별 합계가 총액과 일치하지 않는 경우 이를 보정하기 위한 항목.
    # 1 - correction_value.ratio를 신뢰도 지표로 사용할 수 있음 (보정치로 계산된 비율이 높다 => 신뢰도가 낮다)
    correction_value: Asset = Asset(tier=5, qls_score=0.0, amount=None, ratio=None)
    # Total Amount
    total_amount: float = Field(..., ge=0) 
    
    tier_table: dict[int, list[str]] = {
        1: ["cash_bank_deposits", "us_treasury_bills", "gov_mmf", "other_deposits"],
        2: ["repo_overnight_term", "non_us_treasury_bills", "us_treasury_other_notes_bonds"],
        3: ["corporate_bonds", "precious_metals", "digital_assets"],
        4: ["secured_loans", "other_investments", "custodial_concentrated_asset"],
    }

    # Pretty-printing helpers and __str__ override
    _FIELD_ORDER = [
        "cash_bank_deposits", "us_treasury_bills", "gov_mmf", "other_deposits",
        "repo_overnight_term", "non_us_treasury_bills", "us_treasury_other_notes_bonds",
        "corporate_bonds", "precious_metals", "digital_assets",
        "secured_loans", "other_investments", "custodial_concentrated_asset", "correction_value"
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

        total_line = ["TOTAL", "", "", self._fmt_amount(self.total_amount), ""]

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
        return [(key,value) for key, value in self.dict().items() if isinstance(value, Asset)]


# LLM 입력용 모델
class AmountsOnly(BaseModel):
    cash_bank_deposits: Optional[float] = Field(None, ge=0)
    us_treasury_bills: Optional[float] = Field(None, ge=0)
    gov_mmf: Optional[float] = Field(None, ge=0)
    other_deposits: Optional[float] = Field(None, ge=0)
    
    repo_overnight_term: Optional[float] = Field(None, ge=0)
    non_us_treasury_bills: Optional[float] = Field(None, ge=0)
    us_treasury_other_notes_bonds: Optional[float] = Field(None, ge=0)
    
    corporate_bonds: Optional[float] = Field(None, ge=0)
    precious_metals: Optional[float] = Field(None, ge=0)
    digital_assets: Optional[float] = Field(None, ge=0)
    
    secured_loans: Optional[float] = Field(None, ge=0)
    other_investments: Optional[float] = Field(None, ge=0) 
    custodial_concentrated_asset: Optional[float] = Field(None, ge=0)

    # correction value는 LLM 응답 후 계산되므로 입력 모델에는 포함하지 않음.

    total_amount: Optional[float] = Field(..., ge=0)

    def to_asset_table(self) -> AssetTable:
        asset_table = AssetTable(total_amount=self.total_amount)
        sum = 0.0
        for field_name, value in self.dict().items():
            if field_name != "total_amount" and value is not None:
                sum += value
                getattr(asset_table, field_name).amount = value
                getattr(asset_table, field_name).ratio = (value / self.total_amount) * 100 if self.total_amount > 0 else 0
        asset_table.correction_value.amount = max(0.0, self.total_amount - sum)
        asset_table.correction_value.ratio = (asset_table.correction_value.amount / self.total_amount) * 100 if self.total_amount > 0 else 0
        return asset_table

class OnChainData(BaseModel):
    CEX_flow_in: float = Field(..., ge=0)
    CEX_flow_out: float = Field(..., ge=0)
    liquidity_pool_size: float = Field(..., ge=0) # liquidity pool depth
    whale_asset_change: float = Field(..., description="Change in whale assets (in USD)")
    mint_burn_ratio: float = Field(..., ge=0, description="Ratio of minting to burning activities")
    TVL: float = Field(..., ge=0, description="Total Value Locked in USD")
    

class CoinData(BaseModel):
    stablecoin_ticker: str = Field(..., pattern="^[A-Z]{3,5}$", description="Stablecoin symbol (3-5 uppercase letters)")
    description: str | None
    asset_table: AssetTable
    onchain: OnChainData
    evaluation_date: datetime

class Index(BaseModel):
    name : str = Field(..., pattern="^[a-z]*$", min_length=3, max_length=3)
    value: float = Field(..., ge=0, le=100, description="Index value between 0 and 100")
    threshold: float = Field(..., ge=0, le=100, description="Threshold value between 0 and 100")
    def threshold_check(self) -> bool:
        """Check if the index value exceeds the threshold."""
        return self.value > self.threshold

class Indices(BaseModel):
    index_list: list[Literal['rcr', 'rqs', 'ohs', 'trs']] = ['rcr', 'rqs', 'ohs', 'trs']
    rcr: Index
    rqs: Index
    ohs: Index
    trs: Index = None

class RfRRequest(BaseModel):
    stablecoin_ticker: str = Field(..., pattern="^[A-Z]{3,5}$", description="Stablecoin symbol (3-5 uppercase letters)")
    chain: str = Field(..., pattern="^[a-zA-Z0-9_ -]{3,20}$", description="Blockchain name (3-20 characters)")

    # mcp_version의 경우, 처음 도커 컨테이너 이미지 빌드 시점에 사용되고, 이후 서버 내부에서는 디버깅 용도로만 사용될 예정.
    mcp_version: str = Field(..., pattern="^v\d+\.\d+\.\d+$", description="MCP version in semantic versioning format")
    class Provenanve(BaseModel):
        reports_issuer: str = Field(..., pattern="^[a-zA-Z0-9_ -]{3,50}$", description="Issuer of the report (3-50 characters)")
        reports_url: str = Field(..., pattern="^https?://[^\s/$.?#].[^\s]*$", description="URL of the report")
    provenance: Provenanve

    def _check_url_format(self, url: str) -> bool:
        # Basic URL format validation, file existence is checked during data preprocessing
        import re
        PDF_URL_PATTERN = re.compile(r"^https?:\/\/[^\s]+\.pdf(?:\?.*)?$", re.IGNORECASE)
        if bool(PDF_URL_PATTERN.match(url)) is False:
            raise ValueError(f"Invalid URL format: {url}")

    def validate(self):
        # Check if the request data is avilable and valid
        if self.stablecoin_ticker not in AVAILABLE.COINS:
            raise ValueError(f"Unsupported stablecoin symbol: {self.stablecoin_ticker}. Supported symbols: {AVAILABLE.COINS}")
        if self.chain not in AVAILABLE.CHAINS:
            raise ValueError(f"Unsupported chain: {self.chain}. Supported chains: {AVAILABLE.CHAINS}")
        if self._check_url_format(self.provenance.reports_url) is False:
            raise ValueError(f"Invalid URL Format: {self.provenance.reports_url}\nIt should start with https://")
        

class RfRResponse(BaseModel):
    id: str = Field(default_factory=lambda: datetime.utcnow().strftime('%Y%m%d%H%M%S%f'), description="Unique ID based on timestamp")
    timestamp: datetime
    stablecoin_symbol: str = Field(..., pattern="^[A-Z]{3,5}$", description="Stablecoin symbol (3-5 uppercase letters)")
    chain: str = Field(..., pattern="^[a-zA-Z0-9_ -]{3,20}$", description="Blockchain name (3-20 characters)")
    mcp_version: str = Field(..., pattern="^v\d+\.\d+\.\d+$", description="MCP version in semantic versioning format")
    class Provenanve(BaseModel):
        reports_issuer: str = Field(..., pattern="^[a-zA-Z0-9_ -]{3,50}$", description="Issuer of the report (3-50 characters)")
        reports_url: str = Field(..., pattern="^https?://[^\s/$.?#].[^\s]*$", description="URL of the report")
