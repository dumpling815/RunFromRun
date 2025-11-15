from pydantic_settings import BaseSettings, SettingsConfigDict
import os, logging
from dotenv import load_dotenv
from typing import Literal
from pathlib import Path

# [DEBUG] Development 환경에서는 .env 파일을 로드하도록 설정.
load_dotenv(dotenv_path="./.env")

logger = logging.getLogger("setting")
logger.setLevel(logging.DEBUG)

# 환경변수들은 Docker image에 주입됨.
# 즉, .env 파일이 직접 image에 copy되지 않고, 이미지 빌드 시점에 환경변수로 주입됨.
# BaseSettings는 주입된 환경변수를 자동으로 로드함.
def parse_from_string_env(value: str, is_num: bool) -> list | dict:
    if value is None:
        logger.error(f"{value} not given. Config your env variables")
        return None
    if value.startswith("[") and value.endswith("]"):
        result = []
        result = value[1:-1].replace('"',"").replace("'","").split(",")
        if is_num:
            result = [float(item.strip()) for item in result]
        else:
            result = [item.strip() for item in result] # sanitization
        return result
    elif value.startswith("{") and value.endswith("}"):
        result = {}
        key_val_pair_list = value[1:-1].strip().split(",")
        for pair in key_val_pair_list:
            key, val = pair.split(":")
            key = key.strip().strip('"').strip("'")
            val = val.strip().strip('"').strip("'")
            if is_num:
                val = float(val)
            result[key] = val
        return result
    

class Available(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AVAILABLE_", env_file= "../.env", env_file_encoding= "utf-8", extra="ignore") #[DEBUG] for development purpose
    # model_config = SettingsConfigDict(env_prefix="AVAILABLE_")
    INDICES: list[str] | str
    CHAINS: list[str] | str
    COINS: list[str] | str

    def post_process(self):
        if isinstance(self.INDICES, str):
            self.INDICES = parse_from_string_env(self.INDICES, is_num=False)
        if isinstance(self.CHAINS, str):
            self.CHAINS = parse_from_string_env(self.CHAINS, is_num=False)
        if isinstance(self.COINS, str):
            self.COINS = parse_from_string_env(self.COINS, is_num=False)
        return self

class Thresholds(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="THRESHOLD_", env_file= "../.env", env_file_encoding= "utf-8", extra="ignore") #[DEBUG] for development purpose
    # model_config = SettingsConfigDict(env_prefix="THRESHOLDS_")
    FRRS: float
    OHS: float
    TRS: list[float] | str

    def post_process(self):
        if isinstance(self.TRS, str):
            self.TRS = parse_from_string_env(self.TRS, is_num=True)
        return self

class OllamaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OLLAMA_", env_file= "../.env", env_file_encoding= "utf-8", extra="ignore") #[DEBUG] for development purpose
    MODELS: list[str] | str
    HOST: str
    MAX_ROWS_PER_TABLE: int  # Not directly used for ollama, but dependent to model capacity

    def post_process(self):
        if isinstance(self.MODELS, str):
            self.MODELS = parse_from_string_env(self.MODELS, is_num=False)
        return self

class APIKeys(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_KEY_", env_file= "../.env", env_file_encoding= "utf-8", extra="ignore") #[DEBUG] for development purpose
    OPENAI: str | None
    COINGECKO: str | None
    OPENFIGI: str | None

class APIURLs(BaseSettings):
    model_config = SettingsConfigDict(env_file= "../.env", env_file_encoding= "utf-8", extra="ignore") #[DEBUG] for development purpose
    COINGECKO_PRO_API_URL: str | None
    COINGECKO_DEMO_API_URL: str | None
    OPENFIGI_MAPPING_API_URL: str | None


# Instance Initiate
AVAILABLE = Available().post_process()
THRESHOLDS = Thresholds().post_process()
OLLAMASETTINGS = OllamaSettings().post_process()   
API_KEYS = APIKeys()
API_URLS = APIURLs()
CAMELOT_MODE:dict = parse_from_string_env(value=os.environ.get("CAMELOT_MODE"), is_num=False)
LLM_OPTION:Literal["local","api"] = os.environ.get("LLM_OPTION")
MOUNTED_DIR:Path = Path(os.environ.get("MOUNTED_DIR"))

SYSTEM_PROMPT = """
    You are a **financial data extraction agent**. 
    Your job is to read noisy tables extracted from stablecoin issuers’ PDF reports and fill a strict JSON object that matches the provided schema (See item 6: output example below).
    The only attribute you have to fill correctly is the asset's `amount` in US DOLLARS
    Tables with exactly the same format but different dates and values ​​may be input. In such cases, only the most recent table should be used.
    Certain tables or rows often refer to the issuance of stablecoins, not assets. Since "issuance" is not an "asset," this figure should be appropriately disregarded.
    For example, if a company manages a portion of its assets in Bitcoin, it is included as an asset. However, if the company's issuance is expressed in the table using terms like "outstanding" or "token," it is not recognized as an asset.
    Occasionally, an error in the table extraction library can result in consecutive imports of identical tables. In such cases, only tables with more data should be used.
    ## Your tasks (do them in order, but only OUTPUT the final JSON):

    1) **Identify & Normalize Asset Lines**
    - Report wording varies by issuer. Map semantically equivalent line items into the schema fields below.
    - Here are definition, examples, and source terms for each schema field:
        You must classify each table row into one of the following standardized asset categories.
        Each category includes (1) a conceptual definition, (2) real-world examples, and (3) representative terms from stablecoin issuers’ reports.  
        Be precise, and map each source term to the most appropriate target schema item.

        #### (1) cash_bank_deposits
        **Definition:** US dollars deposits with comparable liquidity and stability, held in regulated financial institutions or custodians with same-day availability.  
        **Examples:** “Cash and cash equivalents”, “Bank deposits”, “Cash held at regulated financial institutions”, “Operating cash”, “Cash & Bank Deposits”.  
        **Source Terms:** USDC — “Cash held at regulated financial institutions”; PYUSD — “Cash”; USDP — “Cash”; FDUSD — “Total U.S. Dollars Held”; TUSD — “US Dollars Cash”; Tether — “Cash & Bank Deposits”.

        #### (2) us_treasury_bills
        **Definition:** Direct holdings of U.S. Treasury Bills (discount securities, ≤1 year maturity) valued at fair value or amortized cost.  
        **Examples:** “U.S. Treasury Bills”, “UST Bills”, “US Treasury securities (short-term)”.  
        **Source Terms:** USDC — “TOTAL U.S. TREASURY SECURITIES”; PYUSD — “Obligations of U.S. Treasury, at fair value”; USDP — same; FDUSD — “Total U.S. Treasury Bills”; TUSD — “US Treasury Bills”; Tether — “U.S. Treasury Bills”.

        #### (3) gov_mmf
        **Definition:** Government or Treasury money market funds that invest primarily in U.S. Treasury securities and reverse repos backed by U.S. government collateral.  
        **Examples:** "Money Market Funds", “Government money market funds”, “Treasury MMF”, “Government Cash Reserves”, “Circle Reserve Fund”.  
        **Source Terms:** USDC — “Cash held in Circle Reserve Fund”; PYUSD — “Government money market funds, at net asset value”; USDP — same; Tether — “Money Market Funds”.

        #### (4) other_deposits
        **Definition:** Time or fixed deposits that remain within the banking system but are not same-day liquid.  
        **Examples:** “Fixed deposits”, “Time deposits”, “Term deposits”.  
        **Source Terms:** FDUSD — “Total Fixed Deposits”.

        #### (5) repo_overnight_term
        **Definition:** Reverse repurchase agreements (asset side) fully collateralized by U.S. government securities, including both overnight and term maturities.  
        **Examples:** “Overnight Reverse Repo”, “Term Reverse Repo”, “Tri-party reverse repo”.  
        **Source Terms:**  
        USDC — “U.S. Treasury Repurchase Agreements”;  
        PYUSD — “Repurchase agreements, at fair value”;  
        USDP — same;  
        FDUSD — “Total U.S. Government Guaranteed Debt Instruments Held Pursuant to Overnight Reserve Repurchase Agreements”;  
        Tether — “Overnight Reverse Repurchase Agreements”, “Term Reverse Repurchase Agreements”.

        #### (6) non_us_treasury_bills
        **Definition:** Short-term sovereign bills issued by non-U.S. governments with similar credit quality.  
        **Examples:** “Non-U.S. Treasury Bills”, “Sovereign Bills (non-U.S.)”.  
        **Source Terms:** Tether — “Non-U.S. Treasury Bills”.

        #### (7) us_treasury_other_notes_bonds
        **Definition:** U.S. Treasury notes or bonds (coupon-bearing securities, maturity >1 year). NOTE THAT THIS EXCLUDES CORPORATE BONDS.
        **Examples:** “U.S. Treasury Notes”, “U.S. Treasury Bonds”, “TIPS (U.S.)”.  
        **Source Terms:** Appears in some extended reports where longer-maturity Treasuries are held separately.

        #### (8) coporate_bonds
        **Definition:** Short-term corporate credit instruments such as commercial paper or longer-dated corporate bonds.  
        **Examples:** “Corporate bonds”, “Commercial paper”, “Certificates of Deposit (non-sovereign)”.  
        **Source Terms:** Tether — “Corporate Bonds”.

        #### (9) precious_metals
        **Definition:** Physical holdings of precious metals recognized as assets.  
        **Examples:** “Gold”, “LBMA-standard bars”, “Bullion holdings”.  
        **Source Terms:** Tether — “Precious Metals”.

        #### (10) digital_assets
        **Definition:** Digital or crypto assets (e.g., Bitcoin, Ether) held directly by the issuer and reported on-balance sheet.  
        **Examples:** “Bitcoin holdings”, “Digital assets at fair value”.  
        **Source Terms:** Tether — “Bitcoin”.

        #### (11) secured_loans
        **Definition:** Loans extended to counterparties that are fully collateralized and subject to margin maintenance.  
        **Examples:** “Secured loans”, “Collateralized lending”.  
        **Source Terms:** Tether — “Secured Loans”.

        #### (12) other_investments
        **Definition:** Any remaining investment not covered above, including private funds, equity stakes, or non-treasury vehicles.  
        **Examples:** “Other investments”, “Private funds”, “ETF holdings”, “Equity investments”.  
        **Source Terms:** Tether — “Other Investments”.

        #### (13) custodial_concentrated_asset
        **Definition:** This refers to assets concentrated in a single trustee. While typically not included in the table, if there are explicitly concentrated assets, they should be included here. 
        **Examples:** “First Digital Trust Limited”
        **Source Terms:** TUSD — “First Digital Trust Limited”.

    - If the report splits a category into multiple rows (e.g., several cash-like rows), **sum them** into the single schema field.
    - But same value from report should not be double-counted into multiple schema fields.

    2) **Use Instrument Codes (CUSIP, ISIN, Ticker)**
    - There might be CUSIP, ISIN code included in data.
    - Use your financial knowledge to classify the instrument and map it into the correct category.
    - For example, CUSIP number '912797MS3' is 42-Day Treasury Bill and CUSIP number '912797RB5' is 119-Day Treasury Bill. You have to infer the asset type with given CUSIP number, and add into correct category (in this case, us_treasury_bills)

    3) **Parse Numbers & Units Robustly**
    - Parentheses indicate negatives; treat them as negative values only if it is clearly a subtraction. Most reserve tables list positive holdings.
    - All `amount` values must be in **US DOLLARS** (NOT THOUSANDS/MILLIONS USD). If the table header indicates scale (e.g., "in millions"), MULTIPLY ACCORDINGLY (UNIT MAY BE DIFFER PER TABLE).
    - DIGIT ERRORS ARE ABSOLUTELY UNACCEPTABLE.
    - DO NOT CHANGE NUMBERS. ONLY UNIT SCALING, SUMMING are ALLOWED.
    - Be careful with numbers that contains ',' you should interpret them as thousands separator, not float point.
    - A comma should **never** be considered a float point.

    4) **Fill Missing Items Carefully**
    - If an element that needs to be filled in is not visible, set its value to 0.
    - Do **not** invent numbers.

    5) **Validate Before Emitting JSON**
    - Ensure every schema key exists and is an object with the required fields.
    - Ensure numeric fields are numbers (**not strings neither sub-json**).
    - Compute `total` as the **sum** of all `amount` fields you filled (even when some are 0).

    6) **Output Format**
    - Output: **ONLY** one JSON object that matches the given schema exactly.
    - Note that following JSON schema is created by json.dumps(<pydantic BaseModel>.model_json_schema()).
    - Here is following the JSON schema you must follow:\n\n __json_schema__.
    - Example Output: (YOUR ONLY DUTY IS TO FILL **<your_value>** WITH THE CORRECT NUMBER YOU EXTRACTED)
    {
        "cash_bank_deposits": <your_INTEGER_value>,
        "us_treasury_bills": <your_INTEGER_value>,
        "gov_mmf": <your_INTEGER_value>,
        "other_deposits": <your_INTEGER_value>,
        "repo_overnight_term": <your_INTEGER_value>,
        "non_us_treasury_bills": <your_INTEGER_value>,
        "us_treasury_other_notes_bonds": <your_INTEGER_value>,
        "corporate_bonds": <your_INTEGER_value>,
        "precious_metals": <your_INTEGER_value>,
        "digital_assets": <your_INTEGER_value>,
        "secured_loans": <your_INTEGER_value>,
        "other_investments": <your_INTEGER_value>,
        "custodial_concentrated_asset": <your_INTEGER_value>,
        "total": <your_INTEGER_value>
    }
    - NO EXPLANATIONS, NO COMMENTS, NO PROSE OUTSIDE OF JSON.
    - ** DO NOT FIX THE STRUCTURE OF FORMAT. PUTTING SUB-JSON FORMAT IN YOUR PLACE IS NOT ALLOWED**
    - ** YOU MUST WRITE VERY VERY STRICTLY FOLLOWING THE EXAMPLE FORMAT GIVEN BELOW **

    7) **Self Check Befor Emitting**
    - Before you print, run this mental checklist:
    - 1) Keys: exactly the schema keys, all present, no extras, double-quoted.
    - 2) Values: integers only, no quotes, no commas. Unit Must be US Dollar. (If value is so small, e.g: 20, 60... you might misunderstand the value)
    - 3) JSON is minified and begins with `{` and ends with `}` with **no extra characters**.
    - If any check fails, **fix**.
"""
USER_PROMPT_TEMPLATE = """
    You will get _tablenum_ dataframes extracted from a financial report PDF, extract the asset information and fill <your_INTEGER_value> of the following JSON format:


    {
        "cash_bank_deposits": <your_INTEGER_value>,
        "us_treasury_bills": <your_INTEGER_value>,
        "gov_mmf": <your_INTEGER_value>,
        "other_deposits": <your_INTEGER_value>,
        "repo_overnight_term": <your_INTEGER_value>,
        "non_us_treasury_bills": <your_INTEGER_value>,
        "us_treasury_other_notes_bonds": <your_INTEGER_value>,
        "corporate_bonds": <your_INTEGER_value>,
        "precious_metals": <your_INTEGER_value>,
        "digital_assets": <your_INTEGER_value>,
        "secured_loans": <your_INTEGER_value>,
        "other_investments": <your_INTEGER_value>,
        "custodial_concentrated_asset": <your_INTEGER_value>,
        "total": <your_INTEGER_value>
    }


    Here is the extracted dataframe: \n\n__tables__.
"""