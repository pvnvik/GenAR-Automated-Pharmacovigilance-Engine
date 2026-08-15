"""Deterministic analysis of adverse reaction preferred terms (PTs)."""

from typing import Any, Dict, List, Tuple
import pandas as pd

from genar.analyses.registry import register_analysis
from genar.config import DatasetConfig
from genar.models.analysis import AnalysisCategory


@register_analysis(
    name="reactions_analysis",
    category=AnalysisCategory.REACTIONS,
    description="Analyzes top adverse reactions overall, in serious cases, and across distinct cases.",
    version="1.0",
)
def compute_reactions_analysis(
    cases_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    config: DatasetConfig,
    top_n: int = 15,
    **kwargs
) -> Tuple[Dict[str, Any], List[str]]:
    """Rank and compute frequencies of reported reaction preferred terms (PTs)."""
    total_reactions = len(reactions_df)
    total_cases = len(cases_df)
    unique_pts = int(reactions_df["reaction_pt"].nunique()) if "reaction_pt" in reactions_df.columns else 0

    # 1. Overall top reactions by event frequency
    pt_counts = reactions_df["reaction_pt"].value_counts()
    top_overall = []
    
    for rank, (pt, count) in enumerate(pt_counts.head(top_n).items(), start=1):
        # Case frequency (number of distinct cases reporting this PT)
        cases_with_pt = reactions_df[reactions_df["reaction_pt"] == pt]["safety_report_id"].nunique()
        pct_rxn = round((count / total_reactions) * 100, 2) if total_reactions > 0 else 0.0
        pct_case = round((cases_with_pt / total_cases) * 100, 2) if total_cases > 0 else 0.0

        top_overall.append({
            "rank": rank,
            "preferred_term": pt,
            "event_count": int(count),
            "event_percent": pct_rxn,
            "distinct_cases_count": int(cases_with_pt),
            "case_percent": pct_case,
        })

    # 2. Top reactions in serious cases
    serious_rxns = reactions_df[reactions_df["is_case_serious"]] if "is_case_serious" in reactions_df.columns else reactions_df
    top_serious_counts = serious_rxns["reaction_pt"].value_counts().head(top_n).to_dict()

    metrics = {
        "total_reactions": total_reactions,
        "unique_preferred_terms": unique_pts,
        "top_reactions_overall": top_overall,
        "top_serious_reactions": top_serious_counts,
        "top_n_requested": top_n,
    }

    contributing_cases = cases_df["safety_report_id"].astype(str).tolist()
    return metrics, contributing_cases
