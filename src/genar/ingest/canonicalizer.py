"""Deterministic canonicalization pipeline building trusted case-level and reaction-level views."""

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from pydantic import BaseModel, Field

from genar.config import DatasetConfig
from genar.ingest.validator import parse_date_value
from genar.models.dataset import CanonicalCase, DatasetMetadata, ReactionRecord


class CanonicalizationResult(BaseModel):
    """Encapsulates output tables, models, and metadata from canonicalization."""
    metadata: DatasetMetadata
    total_raw_rows: int
    total_canonical_cases: int
    total_exploded_reactions: int
    aligned_reactions_count: int
    unaligned_reactions_count: int
    cases_file_path: Optional[str] = None
    reactions_file_path: Optional[str] = None


def resolve_age_group(age: Optional[float], config: DatasetConfig) -> str:
    """Classify numeric age into configured age buckets."""
    if age is None or pd.isna(age):
        return "UNKNOWN"

    for bucket in config.age_buckets:
        min_match = bucket.min_age <= age
        max_match = bucket.max_age is None or age <= bucket.max_age
        if min_match and max_match:
            return bucket.label

    return "UNKNOWN"


def _is_truthy(val: Any) -> bool:
    """Helper to detect boolean positive from string/number."""
    if pd.isna(val) or val is None:
        return False
    s_val = str(val).strip().lower()
    return s_val in ["yes", "1", "true", "serious", "y", "t"]


def build_canonical_cases(
    raw_df: pd.DataFrame,
    config: DatasetConfig
) -> Tuple[pd.DataFrame, List[CanonicalCase]]:
    """Deduplicate raw data and build trusted case-level view (1 row per unique case)."""
    mapping = config.column_mapping
    id_col = mapping.case_id
    version_col = mapping.version

    if id_col not in raw_df.columns:
        raise ValueError(f"Case ID column '{id_col}' not found in raw dataframe.")

    # Sort to determine latest version
    sort_cols = [id_col]
    ascending = [True]
    if version_col in raw_df.columns:
        sort_cols.append(version_col)
        ascending.append(True)
    if mapping.received_date in raw_df.columns:
        sort_cols.append(mapping.received_date)
        ascending.append(True)

    sorted_df = raw_df.sort_values(by=sort_cols, ascending=ascending)

    # Group by case ID to track all contributing raw rows
    grouped = sorted_df.groupby(id_col)
    
    canonical_rows = []
    canonical_models: List[CanonicalCase] = []

    for case_id, group in grouped:
        latest_row = group.iloc[-1]
        source_indices = group.index.tolist()
        v_count = len(group)

        # Parse dates
        rec_date = parse_date_value(latest_row.get(mapping.received_date), config.rules.date_format_code)
        receipt_date = parse_date_value(latest_row.get(mapping.receipt_date), config.rules.date_format_code)

        # Seriousness criteria
        is_death = _is_truthy(latest_row.get(mapping.serious_death))
        is_life_threatening = _is_truthy(latest_row.get(mapping.serious_lifethreatening))
        is_hospitalization = _is_truthy(latest_row.get(mapping.serious_hospitalization))
        is_disabling = _is_truthy(latest_row.get(mapping.serious_disabling))
        is_congenital = _is_truthy(latest_row.get(mapping.serious_congenital))
        is_other = _is_truthy(latest_row.get(mapping.serious_other))
        is_serious = _is_truthy(latest_row.get(mapping.serious)) or any([
            is_death, is_life_threatening, is_hospitalization, is_disabling, is_congenital, is_other
        ])
        is_15_day = _is_truthy(latest_row.get(mapping.expedited_15day))

        # Demographics
        raw_sex = str(latest_row.get(mapping.patient_sex) or "").strip().upper()
        patient_sex = raw_sex if raw_sex in ["MALE", "FEMALE"] else config.rules.unknown_sex_label

        raw_age = latest_row.get(mapping.patient_age)
        patient_age = float(raw_age) if pd.notna(raw_age) and str(raw_age).replace('.', '', 1).isdigit() else None
        patient_age_group = resolve_age_group(patient_age, config)

        raw_country = str(latest_row.get(mapping.country) or "").strip().upper()
        country = raw_country if raw_country and raw_country != "NAN" else config.rules.unknown_country_label

        # Reactions count
        pt_raw = str(latest_row.get(mapping.reactions_pt) or "")
        pts = [p.strip() for p in pt_raw.split(config.rules.list_delimiter) if p.strip() and p.strip().lower() != "nan"]
        reactions_count = len(pts)

        # Primary product
        prod_val = latest_row.get(mapping.drugs) or latest_row.get("patient_drug_medicinalproduct") or config.product_name
        primary_product = str(prod_val) if pd.notna(prod_val) else config.product_name

        c_model = CanonicalCase(
            safety_report_id=str(case_id),
            received_date=rec_date,
            receipt_date=receipt_date,
            is_serious=is_serious,
            is_death=is_death,
            is_life_threatening=is_life_threatening,
            is_hospitalization=is_hospitalization,
            is_disabling=is_disabling,
            is_congenital_anomaly=is_congenital,
            is_other_medically_important=is_other,
            is_15_day_alert=is_15_day,
            patient_sex=patient_sex,
            patient_age=patient_age,
            patient_age_group=patient_age_group,
            primary_source_country=country,
            primary_medicinal_product=primary_product,
            reactions_count=reactions_count,
            source_row_indices=source_indices,
            version_count=v_count,
            has_dq_warnings=(v_count > 1),
        )
        canonical_models.append(c_model)

        canonical_rows.append({
            "safety_report_id": str(case_id),
            "safety_report_version": int(latest_row.get(version_col, 1)) if pd.notna(latest_row.get(version_col)) else 1,
            "received_date": rec_date.isoformat() if rec_date else None,
            "receipt_date": receipt_date.isoformat() if receipt_date else None,
            "is_serious": is_serious,
            "is_death": is_death,
            "is_life_threatening": is_life_threatening,
            "is_hospitalization": is_hospitalization,
            "is_disabling": is_disabling,
            "is_congenital_anomaly": is_congenital,
            "is_other_medically_important": is_other,
            "is_15_day_alert": is_15_day,
            "patient_sex": patient_sex,
            "patient_age": patient_age,
            "patient_age_group": patient_age_group,
            "primary_source_country": country,
            "primary_medicinal_product": primary_product,
            "reactions_count": reactions_count,
            "source_row_indices": str(source_indices),
            "version_count": v_count,
            "raw_reactions_pt": pt_raw,
            "raw_reactions_outcome": str(latest_row.get(mapping.reactions_outcome) or ""),
            "primary_source_row_index": source_indices[-1],
        })

    cases_df = pd.DataFrame(canonical_rows)
    return cases_df, canonical_models


def build_exploded_reactions(
    canonical_df: pd.DataFrame,
    config: DatasetConfig
) -> Tuple[pd.DataFrame, List[ReactionRecord]]:
    """Explode positionally aligned reaction and outcome lists into 1 row per reaction."""
    delimiter = config.rules.list_delimiter
    reaction_rows = []
    reaction_models: List[ReactionRecord] = []

    for idx, row in canonical_df.iterrows():
        case_id = str(row["safety_report_id"])
        pt_raw = str(row.get("raw_reactions_pt") or "")
        out_raw = str(row.get("raw_reactions_outcome") or "")

        pts = [p.strip() for p in pt_raw.split(delimiter) if p.strip() and p.strip().lower() != "nan"]
        outcomes = [o.strip() for o in out_raw.split(delimiter) if o.strip() and o.strip().lower() != "nan"]

        is_aligned = (len(pts) == len(outcomes))
        rec_date = parse_date_value(row.get("received_date"))

        for r_idx, pt in enumerate(pts, start=1):
            reaction_id = f"{case_id}_R{r_idx}"
            
            # Positionally pair outcome if available, otherwise mark unaligned/unknown
            if r_idx - 1 < len(outcomes):
                outcome = outcomes[r_idx - 1]
            else:
                outcome = "UNKNOWN"

            r_model = ReactionRecord(
                reaction_id=reaction_id,
                safety_report_id=case_id,
                reaction_pt=pt,
                reaction_outcome=outcome,
                is_positionally_aligned=is_aligned,
                is_case_serious=bool(row["is_serious"]),
                received_date=rec_date,
                patient_sex=str(row["patient_sex"]),
                patient_age_group=str(row["patient_age_group"]),
                country=str(row["primary_source_country"]),
                source_row_index=int(row["primary_source_row_index"]),
            )
            reaction_models.append(r_model)

            reaction_rows.append({
                "reaction_id": reaction_id,
                "safety_report_id": case_id,
                "reaction_pt": pt,
                "reaction_outcome": outcome,
                "is_positionally_aligned": is_aligned,
                "is_case_serious": bool(row["is_serious"]),
                "received_date": row["received_date"],
                "patient_sex": row["patient_sex"],
                "patient_age_group": row["patient_age_group"],
                "country": row["primary_source_country"],
                "source_row_index": int(row["primary_source_row_index"]),
            })

    reactions_df = pd.DataFrame(reaction_rows)
    return reactions_df, reaction_models


def persist_processed_artifacts(
    cases_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    output_dir: str | Path = "data/processed"
) -> Tuple[Path, Path]:
    """Save canonical cases and exploded reactions to CSV artifacts."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    cases_file = out_path / "canonical_cases.csv"
    reactions_file = out_path / "exploded_reactions.csv"

    cases_df.to_csv(cases_file, index=False, encoding="utf-8")
    reactions_df.to_csv(reactions_file, index=False, encoding="utf-8")

    return cases_file, reactions_file


def run_canonicalization(
    raw_df: pd.DataFrame,
    config: DatasetConfig,
    output_dir: str | Path = "data/processed"
) -> Tuple[pd.DataFrame, pd.DataFrame, CanonicalizationResult]:
    """Execute complete canonicalization flow, persist tables, and return structured result."""
    # 1. Build canonical case view
    cases_df, case_models = build_canonical_cases(raw_df, config)

    # 2. Build exploded reaction view
    reactions_df, reaction_models = build_exploded_reactions(cases_df, config)

    # 3. Persist artifacts
    cases_path, reactions_path = persist_processed_artifacts(cases_df, reactions_df, output_dir)

    # 4. Dates for metadata
    parsed_dates = [parse_date_value(d) for d in cases_df["received_date"].dropna()]
    valid_dates = [d for d in parsed_dates if d is not None]
    period_start = min(valid_dates) if valid_dates else None
    period_end = max(valid_dates) if valid_dates else None

    # 5. Metadata
    metadata = DatasetMetadata(
        dataset_name=config.dataset_name,
        file_path=config.raw_data_path,
        total_raw_rows=len(raw_df),
        total_canonical_cases=len(cases_df),
        total_reactions=len(reactions_df),
        reporting_period_start=period_start,
        reporting_period_end=period_end,
    )

    aligned_count = int(reactions_df["is_positionally_aligned"].sum())
    unaligned_count = len(reactions_df) - aligned_count

    result = CanonicalizationResult(
        metadata=metadata,
        total_raw_rows=len(raw_df),
        total_canonical_cases=len(cases_df),
        total_exploded_reactions=len(reactions_df),
        aligned_reactions_count=aligned_count,
        unaligned_reactions_count=unaligned_count,
        cases_file_path=str(cases_path),
        reactions_file_path=str(reactions_path),
    )

    return cases_df, reactions_df, result
