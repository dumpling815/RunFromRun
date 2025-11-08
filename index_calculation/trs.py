from common.schema import Indices,Index
from common.settings import thresholds

def _calculate_total_risk_score(indices: dict) -> float:
    # TODO : 만일 weight를 training 할 경우, 데이터베이스 연결 필요할 수 있음
    # DB 연결 시 PostgreSQL 우선 고려.
    # 현재는 정적으로 가중치 1/3로 설정.
    total_risk_score = (indices["ohs"] + indices["rcr"] + indices["rqs"]) / 3
    return total_risk_score

def risk_calculator(indices:Indices) -> Index:
    tsr = _calculate_total_risk_score(indices)
    return Index(name="tsr", value=tsr, threshold=thresholds.TSR_THRESHOLD)
    
   