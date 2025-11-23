from common.schema import Indices
from common.settings import SLACK_WEBHOOK_URL
import logging, requests
from datetime import datetime

logger = logging.getLogger("RunFromRun.Analyze.Threshold_Check_And_Alarm")
logger.setLevel(logging.DEBUG)


def alarm_with_slack_webhook(decision_string: str):
    if SLACK_WEBHOOK_URL == "your_slack_webhook_url":
        logger.info("Valid slack webhook url not given")
    else:
        try:
            decision_string = "Complete Time: " +str(datetime.now()) + "\n" + decision_string
            resp = requests.post(
                SLACK_WEBHOOK_URL,
                json={"text": decision_string},
                timeout=5,
            )
            resp.raise_for_status()
            if resp.status_code >= 400:
                logger.error("Slack webhook failed with status %s: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.exception("Failed to send Slack webhook: %s", exc)    

def check_thresholds_and_alarm(indices: Indices) -> str:
    decision_string_list: list[str] = []
    risk = {
        "FRRS": False,
        "OHS": False,
        "TRS": False
    }
    # FRRS Threshold check
    if indices.FRRS.value < indices.FRRS.threshold:
        FRRS_decision = """
        [Warning] The value of FRRS is unusual. This indicates that the issuer's asset management practices pose significant risks.
        """
        decision_string_list.append(FRRS_decision)
        risk["FRRS"] = True
    else:
        FRRS_decision = """
        The FRRS value is stable. The issuer's asset management method is judged to be relatively risk-free.
        """
        decision_string_list.append(FRRS_decision)

    # OHS Threshold check
    if indices.OHS.value < indices.OHS.threshold:
        OHS_decision = """
        [Warning] The value of OHS is unusual. The chain on which the stablecoin is issued may be experiencing liquidity shortages or a decline in net issuance, potentially leading to a contraction.
        """
        decision_string_list.append(OHS_decision)
        risk["OHS"] = True
    else:
        OHS_decision = """
        The OHS value is stable. It seems that the on-chain integrity is currently secured. 
        """
        decision_string_list.append(OHS_decision)
    
    if indices.TRS.value < indices.TRS.threshold[0]:
        TRS_decision = """
        [Warning] The TRS value is severely low!! Strongly recommended to quickly identify risks and make decisions.
        """
        decision_string_list.append(TRS_decision)
        risk["TRS"] = True
    elif indices.TRS.value < indices.TRS.threshold[1]:
        TRS_decision = """
        [Warning] The TRS value is unusual. Potential risks have been identified for the stablecoin in question.
        """
        decision_string_list.append(TRS_decision)
        risk["TRS"] = True
    else:
        TRS_decision = """
        The TRS value is stable. The potential risk of stablecoins is considered to be minimal.
        """
        decision_string_list.append(TRS_decision)
        if risk["FRRS"] or risk["OHS"]:
            additional_decision = """
            However, values ​​that imply potential risks were found among the subvariables of the TRS.
            """
            decision_string_list.append(additional_decision)
    if risk["FRRS"] or risk['OHS']:
        decision_string = decision_string_list[-2] + "\n" + decision_string_list[-1] + "\n" + decision_string_list[0] + "\n" + decision_string_list[1]
    else:
        decision_string = decision_string_list[-1] + "\n" + decision_string_list[0] + "\n" + decision_string_list[1]
    alarm_with_slack_webhook(decision_string)
    return decision_string