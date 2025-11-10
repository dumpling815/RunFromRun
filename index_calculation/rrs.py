from common.schema import Index
# from base_calculator import BaseIndexCalculator 이후 코드 확장 시 고려할 수 있음.
from common.settings import thresholds, api_keys

def rcr_calculator():
    print("RCR Calculator Initialized")
    # TODO : Implement RCR calculation logic here
    value = 1
    return Index(name="rcr", value=value, threshold=thresholds.RCR_THRESHOLD)