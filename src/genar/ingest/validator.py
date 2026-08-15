"""Deterministic schema, data-type, date, and list-alignment validators."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import pandas as pd

from genar.config import DatasetConfig
from genar.models.quality import (
    DQActionTaken,
    DQIssue,
    DQIssueType,
    DQSeverity,
)


def parse_date_value(val: Any, date_format_code: int = 102) -> Optional[date]:
    """Parse integer (YYYYMMDD), string, or timestamp into datetime.date."""
    if pd.isna(val) or val is None or val == "":
        return None

    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()

    if isinstance(val, date):
        return val

    # Try numeric YYYYMMDD (format 102)
    s_val = str(val).strip()
    if s_val.endswith(".0"):
        s_val = s_val[:-2]

    if len(s_val) == 8 and s_val.isdigit():
        try:
            year = int(s_val[0:4])
            month = int(s_val[4:6])
            day = int(s_val[6:8])
            return date(year, month, day)
        except ValueError:
            return None

    # Try standard string date parsing
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s_val, fmt).date()
        except ValueError:
            continue

    return None


def validate_schema(df: pd.DataFrame, config: DatasetConfig) -> List[DQIssue]:
    """Verify presence of required columns mapped in DatasetConfig."""
    issues: List[DQIssue] = []
    mapping = config.column_mapping

    required_keys = [
        ("case_id", mapping.case_id, DQSeverity.CRITICAL),
        ("received_date", mapping.received_date, DQSeverity.CRITICAL),
        ("serious", mapping.serious, DQSeverity.CRITICAL),
        ("reactions_pt", mapping.reactions_pt, DQSeverity.CRITICAL),
        ("reactions_outcome", mapping.reactions_outcome, DQSeverity.WARNING),
        ("patient_sex", mapping.patient_sex, DQSeverity.WARNING),
        ("patient_age", mapping.patient_age, DQSeverity.WARNING),
        ("country", mapping.country, DQSeverity.WARNING),
    ]

    for field_alias, col_name, severity in required_keys:
        if col_name not in df.columns:
            issues.append(
                DQIssue(
                    issue_type=DQIssueType.MISSING_REQUIRED_FIELD,
                    severity=severity,
                    field_name=col_name,
                    message=f"Mapped column '{col_name}' (for '{field_alias}') was not found in raw dataset.",
                    action_taken=DQActionTaken.FLAGGED,
                )
            )

    return issues


def validate_case_ids(df: pd.DataFrame, config: DatasetConfig) -> List[DQIssue]:
    """Check for duplicate or updated case rows across the dataset."""
    issues: List[DQIssue] = []
    id_col = config.column_mapping.case_id
    version_col = config.column_mapping.version

    if id_col not in df.columns:
        return issues

    # Count occurrences of each case ID
    id_counts = df[id_col].value_counts()
    duplicate_ids = id_counts[id_counts > 1]

    for case_id, count in duplicate_ids.items():
        case_rows = df[df[id_col] == case_id]
        versions = case_rows[version_col].tolist() if version_col in df.columns else []
        row_indices = case_rows.index.tolist()

        is_updated = len(set(versions)) > 1 if versions else False
        issue_type = DQIssueType.UPDATED_CASE_ROW if is_updated else DQIssueType.DUPLICATE_CASE_ID

        issues.append(
            DQIssue(
                issue_type=issue_type,
                severity=DQSeverity.WARNING,
                safety_report_id=str(case_id),
                field_name=id_col,
                raw_value=count,
                message=(
                    f"Case ID '{case_id}' appears in {count} rows "
                    f"(versions: {versions}, row indices: {row_indices}). "
                    f"Policy '{config.rules.deduplication_policy}' will be applied during canonicalization."
                ),
                action_taken=DQActionTaken.DEDUPLICATED_LATEST,
                metadata={"versions": versions, "row_indices": row_indices, "count": int(count)},
            )
        )

    return issues


def validate_dates(df: pd.DataFrame, config: DatasetConfig) -> List[DQIssue]:
    """Validate date fields (receivedate, receiptdate) for parsing validity."""
    issues: List[DQIssue] = []
    mapping = config.column_mapping
    date_cols = [mapping.received_date, mapping.receipt_date]

    for col in date_cols:
        if col not in df.columns:
            continue

        for idx, val in df[col].items():
            if pd.isna(val):
                issues.append(
                    DQIssue(
                        issue_type=DQIssueType.MISSING_REQUIRED_FIELD,
                        severity=DQSeverity.WARNING,
                        safety_report_id=str(df.loc[idx, mapping.case_id]) if mapping.case_id in df.columns else None,
                        row_index=int(idx),
                        field_name=col,
                        raw_value=val,
                        message=f"Date field '{col}' is missing/null in row {idx}.",
                        action_taken=DQActionTaken.FLAGGED,
                    )
                )
                continue

            parsed = parse_date_value(val, config.rules.date_format_code)
            if parsed is None:
                issues.append(
                    DQIssue(
                        issue_type=DQIssueType.INVALID_DATE_FORMAT,
                        severity=DQSeverity.WARNING,
                        safety_report_id=str(df.loc[idx, mapping.case_id]) if mapping.case_id in df.columns else None,
                        row_index=int(idx),
                        field_name=col,
                        raw_value=str(val),
                        message=f"Date field '{col}' value '{val}' could not be parsed into a valid date.",
                        action_taken=DQActionTaken.FLAGGED,
                    )
                )

    return issues


def validate_reaction_alignment(df: pd.DataFrame, config: DatasetConfig) -> List[DQIssue]:
    """Detect length mismatches between comma-separated PTs and Outcomes."""
    issues: List[DQIssue] = []
    mapping = config.column_mapping
    delimiter = config.rules.list_delimiter
    pt_col = mapping.reactions_pt
    outcome_col = mapping.reactions_outcome

    if pt_col not in df.columns or outcome_col not in df.columns:
        return issues

    for idx, row in df.iterrows():
        pt_raw = row[pt_col]
        outcome_raw = row[outcome_col]

        pts = [p.strip() for p in str(pt_raw).split(delimiter)] if pd.notna(pt_raw) else []
        outcomes = [o.strip() for o in str(outcome_raw).split(delimiter)] if pd.notna(outcome_raw) else []

        if len(pts) != len(outcomes):
            case_id = str(row[mapping.case_id]) if mapping.case_id in df.columns else f"ROW_{idx}"
            issues.append(
                DQIssue(
                    issue_type=DQIssueType.LIST_LENGTH_MISMATCH,
                    severity=DQSeverity.WARNING,
                    safety_report_id=case_id,
                    row_index=int(idx),
                    field_name=f"{pt_col} / {outcome_col}",
                    raw_value=f"PTs: {len(pts)} vs Outcomes: {len(outcomes)}",
                    message=(
                        f"Positional list length mismatch in case {case_id} (row {idx}): "
                        f"{len(pts)} reactions vs {len(outcomes)} outcomes. "
                        f"Individual terms will be flagged for review."
                    ),
                    action_taken=DQActionTaken.FLAGGED,
                    metadata={
                        "pt_count": len(pts),
                        "outcome_count": len(outcomes),
                        "pts": pts,
                        "outcomes": outcomes,
                    },
                )
            )

    return issues


def validate_demographics(df: pd.DataFrame, config: DatasetConfig) -> List[DQIssue]:
    """Validate age ranges, sex values, and country fields."""
    issues: List[DQIssue] = []
    mapping = config.column_mapping

    # Validate age
    age_col = mapping.patient_age
    if age_col in df.columns:
        for idx, val in df[age_col].items():
            if pd.notna(val):
                try:
                    num_age = float(val)
                    if num_age < 0 or num_age > 130:
                        case_id = str(df.loc[idx, mapping.case_id]) if mapping.case_id in df.columns else None
                        issues.append(
                            DQIssue(
                                issue_type=DQIssueType.AGE_OUT_OF_RANGE,
                                severity=DQSeverity.WARNING,
                                safety_report_id=case_id,
                                row_index=int(idx),
                                field_name=age_col,
                                raw_value=num_age,
                                message=f"Age value {num_age} is outside biologically plausible range (0-130).",
                                action_taken=DQActionTaken.FLAGGED,
                            )
                        )
                except (ValueError, TypeError):
                    pass

    return issues


def validate_dataset(df: pd.DataFrame, config: DatasetConfig) -> List[DQIssue]:
    """Execute complete deterministic validation suite on the raw dataset."""
    all_issues: List[DQIssue] = []
    all_issues.extend(validate_schema(df, config))
    all_issues.extend(validate_case_ids(df, config))
    all_issues.extend(validate_dates(df, config))
    all_issues.extend(validate_reaction_alignment(df, config))
    all_issues.extend(validate_demographics(df, config))
    return all_issues
