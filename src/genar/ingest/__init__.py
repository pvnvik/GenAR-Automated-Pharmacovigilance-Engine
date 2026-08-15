"""Data ingestion, validation, quality assessment, and canonicalization module."""

from genar.ingest.canonicalizer import (
    CanonicalizationResult,
    build_canonical_cases,
    build_exploded_reactions,
    persist_processed_artifacts,
    resolve_age_group,
    run_canonicalization,
)
from genar.ingest.loader import (
    calculate_file_checksum,
    create_dataset_metadata,
    load_raw_dataframe,
    to_raw_case_records,
)
from genar.ingest.quality import (
    build_data_quality_report,
    format_dq_summary_markdown,
)
from genar.ingest.validator import (
    parse_date_value,
    validate_case_ids,
    validate_dataset,
    validate_dates,
    validate_demographics,
    validate_reaction_alignment,
    validate_schema,
)

__all__ = [
    "calculate_file_checksum",
    "load_raw_dataframe",
    "to_raw_case_records",
    "create_dataset_metadata",
    "parse_date_value",
    "validate_schema",
    "validate_case_ids",
    "validate_dates",
    "validate_reaction_alignment",
    "validate_demographics",
    "validate_dataset",
    "build_data_quality_report",
    "format_dq_summary_markdown",
    "resolve_age_group",
    "build_canonical_cases",
    "build_exploded_reactions",
    "persist_processed_artifacts",
    "run_canonicalization",
    "CanonicalizationResult",
]
