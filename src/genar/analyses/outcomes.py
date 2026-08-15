"""Deterministic analysis of reaction outcomes and outcome distributions."""

from typing import Any, Dict, List, Tuple
import pandas as pd

from genar.analyses.registry import register_analysis
from genar.config import DatasetConfig
from genar.models.analysis import AnalysisCategory


@register_analysis(
    name="outcomes_analysis",
    category=AnalysisCategory.OUTCOMES,
    description="Cross-tabulates reaction preferred terms with positionally validated clinical outcomes.",
    version="1.0",
)
def compute_outcomes_analysis(
    cases_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    config: DatasetConfig,
    **kwargs
) -> Tuple[Dict[str, Any], List[str]]:
    """Compute outcome distribution using positionally aligned reaction records."""
    # Filter to positionally valid reaction records
    aligned_df = reactions_df[reactions_df["is_positionally_aligned"]] if "is_positionally_aligned" in reactions_df.columns else reactions_df
    total_aligned = len(aligned_df)
    total_unaligned = len(reactions_df) - total_aligned

    # 1. Overall Outcome Distribution
    outcome_counts = aligned_df["reaction_outcome"].value_counts().to_dict()
    outcome_table = []
    
    for outcome, count in sorted(outcome_counts.items(), key=lambda x: x[1], reverse=True):
        pct = round((count / total_aligned) * 100, 2) if total_aligned > 0 else 0.0
        outcome_table.append({
            "outcome": outcome,
            "count": int(count),
            "percent_of_aligned": pct,
        })

    # 2. Top Reactions outcome matrix (Top 10 reactions)
    top_pts = aligned_df["reaction_pt"].value_counts().head(10).index.tolist()
    reaction_outcome_matrix = []

    for pt in top_pts:
        pt_df = aligned_df[aligned_df["reaction_pt"] == pt]
        pt_total = len(pt_df)
        pt_outcomes = pt_df["reaction_outcome"].value_counts().to_dict()
        
        reaction_outcome_matrix.append({
            "preferred_term": pt,
            "total_events": pt_total,
            "recovered_resolved": pt_outcomes.get("recovered/resolved", 0),
            "recovering": pt_outcomes.get("recovering/resolving", 0),
            "not_recovered": pt_outcomes.get("not recovered/not resolved/ongoing", 0),
            "fatal": pt_outcomes.get("fatal", 0),
            "unknown": pt_outcomes.get("unknown", 0),
            "sequelae": pt_outcomes.get("recovered/resolved with sequelae", 0),
        })

    metrics = {
        "total_aligned_reactions": total_aligned,
        "total_unaligned_reactions": total_unaligned,
        "outcome_distribution": outcome_counts,
        "outcome_table": outcome_table,
        "reaction_outcome_matrix": reaction_outcome_matrix,
    }

    contributing_cases = aligned_df["safety_report_id"].astype(str).unique().tolist()
    return metrics, contributing_cases
