"""Deterministic analysis of serious vs non-serious events and seriousness criteria."""

from typing import Any, Dict, List, Tuple
import pandas as pd

from genar.analyses.registry import register_analysis
from genar.config import DatasetConfig
from genar.models.analysis import AnalysisCategory


@register_analysis(
    name="seriousness_breakdown",
    category=AnalysisCategory.SERIOUSNESS,
    description="Calculates serious/non-serious split and specific seriousness criteria counts.",
    version="1.0",
)
def compute_seriousness_breakdown(
    cases_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    config: DatasetConfig,
    **kwargs
) -> Tuple[Dict[str, Any], List[str]]:
    """Compute serious vs non-serious case proportions and criteria frequencies."""
    total_cases = len(cases_df)
    serious_cases = int(cases_df["is_serious"].sum()) if "is_serious" in cases_df.columns else 0
    non_serious_cases = total_cases - serious_cases

    serious_pct = round((serious_cases / total_cases) * 100, 2) if total_cases > 0 else 0.0
    non_serious_pct = round((non_serious_cases / total_cases) * 100, 2) if total_cases > 0 else 0.0

    # Criteria counts
    criteria_map = [
        ("Death", "is_death", "death"),
        ("Life-Threatening", "is_life_threatening", "life_threatening"),
        ("Hospitalization / Prolonged", "is_hospitalization", "hospitalization"),
        ("Disability / Incapacity", "is_disabling", "disabling"),
        ("Congenital Anomaly", "is_congenital_anomaly", "congenital_anomaly"),
        ("Other Medically Important Condition", "is_other_medically_important", "other_medically_important"),
    ]

    criteria_metrics = {}
    criteria_table = []

    for label, col, key_name in criteria_map:
        count = int(cases_df[col].sum()) if col in cases_df.columns else 0
        pct_total = round((count / total_cases) * 100, 2) if total_cases > 0 else 0.0
        pct_serious = round((count / serious_cases) * 100, 2) if serious_cases > 0 else 0.0
        
        criteria_metrics[f"{key_name}_count"] = count
        criteria_metrics[f"{key_name}_percent"] = pct_total

        criteria_table.append({
            "criteria": label,
            "key": key_name,
            "count": count,
            "percent_of_total": pct_total,
            "percent_of_serious": pct_serious,
        })

    metrics = {
        "total_cases": total_cases,
        "serious_cases": serious_cases,
        "serious_percent": serious_pct,
        "non_serious_cases": non_serious_cases,
        "non_serious_percent": non_serious_pct,
        "criteria": criteria_metrics,
        "criteria_table": criteria_table,
    }

    contributing_cases = cases_df[cases_df["is_serious"]]["safety_report_id"].astype(str).tolist() if "is_serious" in cases_df.columns else []
    return metrics, contributing_cases
