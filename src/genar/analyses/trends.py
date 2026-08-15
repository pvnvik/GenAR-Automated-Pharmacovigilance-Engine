"""Deterministic time-series trends and statistical candidate anomaly detection."""

from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from genar.analyses.registry import register_analysis
from genar.config import DatasetConfig
from genar.models.analysis import AnalysisCategory


@register_analysis(
    name="interval_trends",
    category=AnalysisCategory.TRENDS,
    description="Computes monthly case counts, month-over-month deltas, and flags statistical trend anomalies.",
    version="1.0",
)
def compute_interval_trends(
    cases_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    config: DatasetConfig,
    z_score_threshold: float = 1.5,
    **kwargs
) -> Tuple[Dict[str, Any], List[str]]:
    """Compute monthly aggregations and identify statistical candidate anomalies."""
    if "received_date" not in cases_df.columns:
        return {}, []

    dates = pd.to_datetime(cases_df["received_date"]).dropna()
    if dates.empty:
        return {}, []

    # 1. Monthly case counts
    month_series = dates.dt.to_period("M").astype(str)
    monthly_counts = month_series.value_counts().sort_index()

    counts_list = monthly_counts.tolist()
    months_list = monthly_counts.index.tolist()

    # 2. Summary stats across months
    mean_monthly = float(np.mean(counts_list)) if counts_list else 0.0
    std_monthly = float(np.std(counts_list)) if len(counts_list) > 1 else 0.0

    # 3. Build monthly table and detect candidate anomalies
    monthly_table = []
    candidate_anomalies = []

    for i, (month_str, count) in enumerate(monthly_counts.items()):
        # MoM change
        prev_count = counts_list[i - 1] if i > 0 else None
        mom_change_pct = round(((count - prev_count) / prev_count) * 100, 2) if prev_count and prev_count > 0 else None

        # Statistical Z-score
        z_score = round(float((count - mean_monthly) / std_monthly), 2) if std_monthly > 0 else 0.0
        is_spike = bool(z_score >= z_score_threshold)
        is_dip = bool(z_score <= -z_score_threshold)

        if is_spike or is_dip:
            anomaly_type = "VOLUME_SPIKE" if is_spike else "VOLUME_DIP"
            candidate_anomalies.append({
                "month": month_str,
                "count": int(count),
                "z_score": z_score,
                "type": anomaly_type,
                "description": f"{anomaly_type} detected in {month_str}: {count} cases (mean: {mean_monthly:.1f}, Z-score: {z_score:+0.2f}).",
            })

        monthly_table.append({
            "month": month_str,
            "count": int(count),
            "mom_change_pct": mom_change_pct,
            "z_score": z_score,
            "is_anomaly_candidate": is_spike or is_dip,
        })

    metrics = {
        "total_months": len(monthly_counts),
        "mean_monthly_volume": round(mean_monthly, 2),
        "std_monthly_volume": round(std_monthly, 2),
        "monthly_counts": monthly_counts.to_dict(),
        "monthly_table": monthly_table,
        "candidate_anomalies": candidate_anomalies,
        "z_score_threshold": z_score_threshold,
    }

    contributing_cases = cases_df["safety_report_id"].astype(str).tolist()
    return metrics, contributing_cases
