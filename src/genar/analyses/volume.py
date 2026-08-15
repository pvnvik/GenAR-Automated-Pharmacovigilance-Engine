"""Deterministic volume and reporting period analysis."""

from typing import Any, Dict, List, Tuple
import pandas as pd

from genar.analyses.registry import register_analysis
from genar.config import DatasetConfig
from genar.models.analysis import AnalysisCategory


@register_analysis(
    name="total_case_volume",
    category=AnalysisCategory.VOLUME,
    description="Calculates total canonical case volume, reaction volume, and date range.",
    version="1.0",
)
def compute_volume_summary(
    cases_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    config: DatasetConfig,
    **kwargs
) -> Tuple[Dict[str, Any], List[str]]:
    """Compute case volume, reaction counts, and interval boundaries."""
    total_cases = len(cases_df)
    total_reactions = len(reactions_df)
    
    dates = pd.to_datetime(cases_df["received_date"]).dropna()
    start_date = str(dates.min().date()) if not dates.empty else config.reporting_period_start
    end_date = str(dates.max().date()) if not dates.empty else config.reporting_period_end
    
    rxn_counts = cases_df["reactions_count"] if "reactions_count" in cases_df.columns else pd.Series([1] * total_cases)
    mean_rxn = round(float(total_reactions / total_cases), 2) if total_cases > 0 else 0.0
    max_rxn = int(rxn_counts.max()) if not rxn_counts.empty else 0

    metrics = {
        "total_cases": total_cases,
        "total_reactions": total_reactions,
        "reporting_period_start": start_date,
        "reporting_period_end": end_date,
        "mean_reactions_per_case": mean_rxn,
        "max_reactions_in_single_case": max_rxn,
    }

    contributing_cases = cases_df["safety_report_id"].astype(str).tolist()
    return metrics, contributing_cases
