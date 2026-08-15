"""Deterministic demographic breakdowns (Sex, Age Buckets, Country)."""

from typing import Any, Dict, List, Tuple
import pandas as pd

from genar.analyses.registry import register_analysis
from genar.config import DatasetConfig
from genar.models.analysis import AnalysisCategory


@register_analysis(
    name="demographics_breakdown",
    category=AnalysisCategory.DEMOGRAPHICS,
    description="Computes sex, age group, age statistics, and geographic country distributions.",
    version="1.0",
)
def compute_demographics_breakdown(
    cases_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    config: DatasetConfig,
    **kwargs
) -> Tuple[Dict[str, Any], List[str]]:
    """Compute demographic distributions across canonical cases."""
    total_cases = len(cases_df)

    # 1. Sex breakdown
    sex_counts = cases_df["patient_sex"].value_counts().to_dict() if "patient_sex" in cases_df.columns else {}
    sex_table = []
    for sex, count in sorted(sex_counts.items(), key=lambda x: x[1], reverse=True):
        pct = round((count / total_cases) * 100, 2) if total_cases > 0 else 0.0
        sex_table.append({"category": "Sex", "subcategory": sex, "count": count, "percent": pct})

    # 2. Age group breakdown
    age_group_counts = cases_df["patient_age_group"].value_counts().to_dict() if "patient_age_group" in cases_df.columns else {}
    age_table = []
    for group, count in sorted(age_group_counts.items(), key=lambda x: x[1], reverse=True):
        pct = round((count / total_cases) * 100, 2) if total_cases > 0 else 0.0
        age_table.append({"category": "Age Group", "subcategory": group, "count": count, "percent": pct})

    # 3. Numeric age summary statistics
    numeric_ages = cases_df["patient_age"].dropna() if "patient_age" in cases_df.columns else pd.Series([], dtype=float)
    age_stats = {
        "mean_age": round(float(numeric_ages.mean()), 2) if not numeric_ages.empty else None,
        "median_age": round(float(numeric_ages.median()), 2) if not numeric_ages.empty else None,
        "min_age": float(numeric_ages.min()) if not numeric_ages.empty else None,
        "max_age": float(numeric_ages.max()) if not numeric_ages.empty else None,
        "std_age": round(float(numeric_ages.std()), 2) if len(numeric_ages) > 1 else None,
        "reported_age_count": int(len(numeric_ages)),
        "missing_age_count": int(total_cases - len(numeric_ages)),
    }

    # 4. Country distribution (Top 10 + Other)
    country_counts = cases_df["primary_source_country"].value_counts() if "primary_source_country" in cases_df.columns else pd.Series([], dtype=int)
    top_countries = country_counts.head(10).to_dict()
    other_count = int(country_counts.iloc[10:].sum()) if len(country_counts) > 10 else 0
    if other_count > 0:
        top_countries["OTHER_COUNTRIES"] = other_count

    country_table = []
    for ctry, count in top_countries.items():
        pct = round((count / total_cases) * 100, 2) if total_cases > 0 else 0.0
        country_table.append({"category": "Country", "subcategory": ctry, "count": count, "percent": pct})

    metrics = {
        "total_cases": total_cases,
        "sex_distribution": sex_counts,
        "age_group_distribution": age_group_counts,
        "age_statistics": age_stats,
        "country_distribution": top_countries,
        "demographics_table": sex_table + age_table + country_table,
    }

    contributing_cases = cases_df["safety_report_id"].astype(str).tolist()
    return metrics, contributing_cases
