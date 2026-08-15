"""Deterministic analysis of 15-Day Alert expedited reports."""

from typing import Any, Dict, List, Tuple
import pandas as pd

from genar.analyses.registry import register_analysis
from genar.config import DatasetConfig
from genar.models.analysis import AnalysisCategory


@register_analysis(
    name="fifteen_day_alerts",
    category=AnalysisCategory.ALERTS,
    description="Analyzes 15-day expedited alert cases from source expedite criteria flags.",
    version="1.0",
)
def compute_15_day_alerts(
    cases_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    config: DatasetConfig,
    **kwargs
) -> Tuple[Dict[str, Any], List[str]]:
    """Compute 15-day alert totals and top associated adverse events."""
    total_cases = len(cases_df)
    alert_cases_df = cases_df[cases_df["is_15_day_alert"]] if "is_15_day_alert" in cases_df.columns else pd.DataFrame()
    alert_count = len(alert_cases_df)
    alert_pct = round((alert_count / total_cases) * 100, 2) if total_cases > 0 else 0.0

    # Associated reactions in 15-day alert cases
    alert_case_ids = set(alert_cases_df["safety_report_id"].astype(str)) if not alert_cases_df.empty else set()
    alert_rxns = reactions_df[reactions_df["safety_report_id"].astype(str).isin(alert_case_ids)]
    top_alert_pts = alert_rxns["reaction_pt"].value_counts().head(10).to_dict()

    metrics = {
        "total_cases": total_cases,
        "fifteen_day_alerts_count": alert_count,
        "fifteen_day_alerts_percent": alert_pct,
        "top_reactions_in_alerts": top_alert_pts,
        "source_criteria_basis": "fulfillexpeditecriteria",
    }

    contributing_cases = list(alert_case_ids)
    return metrics, contributing_cases
