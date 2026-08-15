"""Unit and regression tests for data ingestion, validation, and data quality reporting."""

from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from click.testing import CliRunner

from genar.cli import cli
from genar.config import ColumnMappingConfig, DatasetConfig, load_dataset_config
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
from genar.models.quality import DQIssueType, DQSeverity


def test_load_real_bisoprolol_dataset(sample_dataset_config_path: Path):
    """Verify loading real Bisoprolol sample file returns expected dimensions."""
    config = load_dataset_config(sample_dataset_config_path)
    df = load_raw_dataframe(config.raw_data_path)
    assert len(df) == 1068
    assert df["safetyreportid"].nunique() == 1024


def test_calculate_file_checksum(sample_dataset_config_path: Path):
    """Verify SHA-256 checksum calculation produces deterministic 64-char hex string."""
    config = load_dataset_config(sample_dataset_config_path)
    checksum = calculate_file_checksum(config.raw_data_path)
    assert len(checksum) == 64
    assert checksum == calculate_file_checksum(config.raw_data_path)


def test_create_dataset_metadata(sample_dataset_config_path: Path):
    """Verify DatasetMetadata generation from raw dataframe."""
    config = load_dataset_config(sample_dataset_config_path)
    df = load_raw_dataframe(config.raw_data_path)
    meta = create_dataset_metadata(df, config, config.raw_data_path)
    assert meta.dataset_name == "bisoprolol_sample_2024"
    assert meta.total_raw_rows == 1068
    assert meta.total_canonical_cases == 1024
    assert meta.checksum is not None


def test_to_raw_case_records(sample_dataset_config_path: Path):
    """Verify conversion of DataFrame rows to typed RawCaseRecord models."""
    config = load_dataset_config(sample_dataset_config_path)
    df = load_raw_dataframe(config.raw_data_path).head(10)
    records = to_raw_case_records(df, config.column_mapping)
    assert len(records) == 10
    assert records[0].safety_report_id == "24780403"
    assert records[0].patient_sex == "female"
    assert records[0].patient_age == 85.0


def test_parse_date_value():
    """Verify integer (102 format), string, and datetime parsing."""
    assert parse_date_value(20241227) == date(2024, 12, 27)
    assert parse_date_value("20241227") == date(2024, 12, 27)
    assert parse_date_value("2024-12-27") == date(2024, 12, 27)
    assert parse_date_value(pd.Timestamp("2024-12-27")) == date(2024, 12, 27)
    assert parse_date_value(None) is None
    assert parse_date_value("invalid_date") is None


def test_validate_schema_missing_column():
    """Verify missing required columns generate DQ issues with proper severity."""
    df = pd.DataFrame({"some_other_column": [1, 2, 3]})
    config = DatasetConfig(
        dataset_name="test",
        product_name="test",
        active_substance="test",
        manufacturer="test",
        raw_data_path="test.csv",
        reporting_period_start="2024-01-01",
        reporting_period_end="2024-12-31",
    )
    issues = validate_schema(df, config)
    assert len(issues) > 0
    assert any(i.severity == DQSeverity.CRITICAL for i in issues)


def test_validate_case_ids_duplicates():
    """Verify duplicate case IDs are detected and flagged."""
    df = pd.DataFrame({
        "safetyreportid": [101, 101, 102],
        "safetyreportversion": [1, 2, 1],
    })
    config = DatasetConfig(
        dataset_name="test",
        product_name="test",
        active_substance="test",
        manufacturer="test",
        raw_data_path="test.csv",
        reporting_period_start="2024-01-01",
        reporting_period_end="2024-12-31",
    )
    issues = validate_case_ids(df, config)
    assert len(issues) == 1
    assert issues[0].issue_type == DQIssueType.UPDATED_CASE_ROW
    assert issues[0].safety_report_id == "101"


def test_validate_reaction_alignment_mismatch():
    """Verify positional mismatch between PTs and outcomes is flagged."""
    df = pd.DataFrame({
        "safetyreportid": [101, 102],
        "patient_reaction_reactionmeddrapt": ["Nausea, Vomiting", "Headache, Dizziness, Fatigue"],
        "patient_reaction_reactionoutcome": ["recovered, recovered", "recovered, unknown"],  # 3 PTs vs 2 outcomes
    })
    config = DatasetConfig(
        dataset_name="test",
        product_name="test",
        active_substance="test",
        manufacturer="test",
        raw_data_path="test.csv",
        reporting_period_start="2024-01-01",
        reporting_period_end="2024-12-31",
    )
    issues = validate_reaction_alignment(df, config)
    assert len(issues) == 1
    assert issues[0].issue_type == DQIssueType.LIST_LENGTH_MISMATCH
    assert issues[0].safety_report_id == "102"


def test_validate_dataset_full_real_sample(sample_dataset_config_path: Path):
    """Verify complete validation suite execution on Bisoprolol sample dataset."""
    config = load_dataset_config(sample_dataset_config_path)
    df = load_raw_dataframe(config.raw_data_path)
    issues = validate_dataset(df, config)
    report = build_data_quality_report(issues, len(df), df["safetyreportid"].nunique())

    assert report.total_raw_rows == 1068
    assert report.total_unique_case_ids == 1024
    assert report.duplicate_rows_detected == 41  # 41 unique case IDs have multiple rows (accounting for 44 excess rows)
    assert report.list_mismatches_detected == 6
    assert report.critical_issues_count == 0


def test_format_dq_summary_markdown():
    """Verify Markdown report generation format."""
    config = DatasetConfig(
        dataset_name="test",
        product_name="test",
        active_substance="test",
        manufacturer="test",
        raw_data_path="test.csv",
        reporting_period_start="2024-01-01",
        reporting_period_end="2024-12-31",
    )
    df = pd.DataFrame({
        "safetyreportid": [101, 101],
        "safetyreportversion": [1, 2],
        "receivedate": [20240101, 20240102],
        "receiptdate": [20240101, 20240102],
        "serious": ["serious", "serious"],
        "patient_reaction_reactionmeddrapt": ["Headache, Nausea", "Headache, Nausea"],
        "patient_reaction_reactionoutcome": ["recovered", "recovered"],
    })
    issues = validate_dataset(df, config)
    report = build_data_quality_report(issues, 2, 1)
    md_text = format_dq_summary_markdown(report)
    assert "## Data Quality and Integrity Assessment" in md_text
    assert "Total Raw Rows Ingested:" in md_text


def test_cli_validate_data_command(tmp_path: Path):
    """Verify CLI validate-data command executes and exports report file."""
    runner = CliRunner()
    report_file = tmp_path / "dq_report.md"
    result = runner.invoke(cli, ["validate-data", "-o", str(report_file)])
    assert result.exit_code == 0
    assert "Data Quality Assessment Summary" in result.output
    assert "Findings by Category" in result.output
    assert report_file.exists()
    assert len(report_file.read_text(encoding="utf-8")) > 100
