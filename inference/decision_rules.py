"""
Rule-based mapping from model outputs to a human-readable maintenance
recommendation. Deliberately simple and inspectable (not learned) since
this is the last-mile text an MSME technician acts on -- it must be
auditable, not a black box on top of a black box.
"""

_FAULT_ACTION_HINTS = {
    "healthy": "No fault indicators present.",
    "inner_race": "Inner race defect signature detected -- inspect bearing inner raceway and lubrication.",
    "outer_race": "Outer race defect signature detected -- inspect bearing outer raceway and housing alignment.",
    "ball": "Ball/roller defect signature detected -- inspect rolling elements for pitting or spalling.",
    "combined": "Combined inner+outer race defect signature detected -- bearing replacement likely required.",
}


def recommend_action(predicted_fault: str, health_score: float) -> str:
    if health_score >= 85:
        urgency = "Continue normal operation; no immediate action required."
    elif health_score >= 60:
        urgency = "Schedule inspection during the next planned maintenance window."
    elif health_score >= 30:
        urgency = "Schedule inspection soon and monitor trend closely."
    else:
        urgency = "Immediate inspection recommended -- elevated risk of failure."

    hint = _FAULT_ACTION_HINTS.get(predicted_fault, "")
    if predicted_fault == "healthy" or not hint:
        return urgency
    return f"{urgency} {hint}"
