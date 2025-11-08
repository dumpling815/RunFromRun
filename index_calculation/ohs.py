from common.schema import Index
# from base_calculator import BaseIndexCalculator 이후 코드 확장 시 고려할 수 있음.
from common.settings import thresholds, api_keys

def ohs_calculator() -> Index:
    print("OHS Calculator Initialized")
    # TODO : Implement OHS calculation logic here
    value = 80
    return Index(name="ohs", value=value, threshold=thresholds.OHS_THRESHOLD)