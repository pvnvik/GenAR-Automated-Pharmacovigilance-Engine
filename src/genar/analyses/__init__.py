"""Deterministic analysis registry and specialized statistical calculators."""

from genar.analyses.alerts import compute_15_day_alerts
from genar.analyses.demographics import compute_demographics_breakdown
from genar.analyses.outcomes import compute_outcomes_analysis
from genar.analyses.reactions import compute_reactions_analysis
from genar.analyses.registry import AnalysisRegistry, register_analysis
from genar.analyses.seriousness import compute_seriousness_breakdown
from genar.analyses.trends import compute_interval_trends
from genar.analyses.volume import compute_volume_summary

__all__ = [
    "AnalysisRegistry",
    "register_analysis",
    "compute_volume_summary",
    "compute_seriousness_breakdown",
    "compute_demographics_breakdown",
    "compute_reactions_analysis",
    "compute_outcomes_analysis",
    "compute_15_day_alerts",
    "compute_interval_trends",
]
