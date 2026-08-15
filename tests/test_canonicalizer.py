"""Unit and regression tests for case deduplication, canonicalization, and reaction explosion."""

from pathlib import Path
import pandas as pd
import pytest
from click.testing import CliRunner

from genar.cli import cli
from genar.config import DatasetConfig, load_dataset_config
from genar.ingest.canonicalizer import (
    build_canonical_cases,
    build_exploded_reactions,
    persist_processed_artifacts,
    resolve_age_group,
    run_canonicalization,
)
from genar.ingest.loader import load_raw_dataframe
from genar.models.dataset import CanonicalCase, ReactionRecord


def test_resolve_age_group(sample_dataset_config_path: Path):
    """Verify age group resolution according to configured age buckets."""
    config = load_dataset_config(sample_dataset_config_path)
    assert resolve_age_group(12.0, config) == "Pediatric (<18)"
    assert resolve_age_group(17.99, config) == "Pediatric (<18)"
    assert resolve_age_group(18.0, config) == "Adult (18-64)"
    assert resolve_age_group(45.5, config) == "Adult (18-64)"
    assert resolve_age_group(64.99, config) == "Adult (18-64)"
    assert resolve_age_group(65.0, config) == "Elderly (65+)"
    assert resolve_age_group(88.0, config) == "Elderly (65+)"
    assert resolve_age_group(None, config) == "UNKNOWN"


def test_build_canonical_cases_synthetic():
    """Verify deduplication picks highest version and aggregates source rows."""
    config = DatasetConfig(
        dataset_name="test_dataset",
        product_name="TestDrug",
        active_substance="TestSubstance",
        manufacturer="TestMfg",
        raw_data_path="test.csv",
        reporting_period_start="2024-01-01",
        reporting_period_end="2024-12-31",
    )
    raw_df = pd.DataFrame({
        "safetyreportid": [1001, 1001, 1002],
        "safetyreportversion": [1, 2, 1],
        "receivedate": [20240101, 20240105, 20240201],
        "receiptdate": [20240101, 20240105, 20240201],
        "serious": ["serious", "serious", "not serious"],
        "seriousnessdeath": ["no", "yes", "no"],
        "seriousnesshospitalization": ["yes", "yes", "no"],
        "patient_patientsex": ["female", "female", "male"],
        "patient_patientonsetage": [45.0, 45.0, 70.0],
        "primarysourcecountry": ["US", "US", "UK"],
        "patient_reaction_reactionmeddrapt": ["Nausea, Vomiting", "Nausea, Vomiting, Fatigue", "Headache"],
        "patient_reaction_reactionoutcome": ["recovered, recovered", "recovered, recovered, unknown", "recovered"],
    })

    cases_df, case_models = build_canonical_cases(raw_df, config)
    assert len(cases_df) == 2
    assert len(case_models) == 2

    # Case 1001 must have version 2 data (is_death = True, 3 reactions)
    case_1001 = next(c for c in case_models if c.safety_report_id == "1001")
    assert case_1001.is_death is True
    assert case_1001.reactions_count == 3
    assert case_1001.version_count == 2
    assert case_1001.has_dq_warnings is True
    assert case_1001.source_row_indices == [0, 1]

    # Case 1002 must have version 1 data (not serious)
    case_1002 = next(c for c in case_models if c.safety_report_id == "1002")
    assert case_1002.is_serious is False
    assert case_1002.version_count == 1


def test_build_exploded_reactions_synthetic():
    """Verify explosion of positionally aligned reaction lists and outcome pairing."""
    config = DatasetConfig(
        dataset_name="test_dataset",
        product_name="TestDrug",
        active_substance="TestSubstance",
        manufacturer="TestMfg",
        raw_data_path="test.csv",
        reporting_period_start="2024-01-01",
        reporting_period_end="2024-12-31",
    )
    raw_df = pd.DataFrame({
        "safetyreportid": [101, 102],
        "safetyreportversion": [1, 1],
        "receivedate": [20240101, 20240201],
        "receiptdate": [20240101, 20240201],
        "serious": ["serious", "serious"],
        "patient_patientsex": ["female", "male"],
        "patient_patientonsetage": [30.0, 75.0],
        "primarysourcecountry": ["US", "DE"],
        "patient_reaction_reactionmeddrapt": ["Nausea, Rash", "Headache, Dizziness, Malaise"],
        "patient_reaction_reactionoutcome": ["recovered, resolved", "recovered, unknown"],  # 102 is unaligned (3 vs 2)
    })

    cases_df, _ = build_canonical_cases(raw_df, config)
    reactions_df, reaction_models = build_exploded_reactions(cases_df, config)

    assert len(reactions_df) == 5
    assert len(reaction_models) == 5

    # Check case 101 reactions (aligned)
    r_101 = [r for r in reaction_models if r.safety_report_id == "101"]
    assert len(r_101) == 2
    assert r_101[0].reaction_pt == "Nausea"
    assert r_101[0].reaction_outcome == "recovered"
    assert r_101[0].is_positionally_aligned is True

    # Check case 102 reactions (unaligned)
    r_102 = [r for r in reaction_models if r.safety_report_id == "102"]
    assert len(r_102) == 3
    assert r_102[2].reaction_pt == "Malaise"
    assert r_102[2].reaction_outcome == "UNKNOWN"
    assert r_102[2].is_positionally_aligned is False


def test_canonicalization_real_dataset(sample_dataset_config_path: Path):
    """Verify complete canonicalization execution and exact statistics on Bisoprolol sample."""
    config = load_dataset_config(sample_dataset_config_path)
    raw_df = load_raw_dataframe(config.raw_data_path)
    cases_df, reactions_df, result = run_canonicalization(raw_df, config)

    # 1. Row & case counts
    assert result.total_raw_rows == 1068
    assert result.total_canonical_cases == 1024
    assert result.total_exploded_reactions == 3429
    assert result.aligned_reactions_count == 3371
    assert result.unaligned_reactions_count == 58

    # 2. Exact Seriousness Counts
    assert int(cases_df["is_serious"].sum()) == 1023
    assert int(cases_df["is_death"].sum()) == 68
    assert int(cases_df["is_life_threatening"].sum()) == 105
    assert int(cases_df["is_hospitalization"].sum()) == 482
    assert int(cases_df["is_disabling"].sum()) == 44
    assert int(cases_df["is_congenital_anomaly"].sum()) == 7
    assert int(cases_df["is_other_medically_important"].sum()) == 905
    assert int(cases_df["is_15_day_alert"].sum()) == 1023

    # 3. Exact Demographics
    sex_counts = cases_df["patient_sex"].value_counts().to_dict()
    assert sex_counts["FEMALE"] == 503
    assert sex_counts["MALE"] == 493
    assert sex_counts["UNKNOWN"] == 28

    age_counts = cases_df["patient_age_group"].value_counts().to_dict()
    assert age_counts["Pediatric (<18)"] == 16
    assert age_counts["Adult (18-64)"] == 249
    assert age_counts["Elderly (65+)"] == 676
    assert age_counts["UNKNOWN"] == 83


def test_persist_processed_artifacts(sample_dataset_config_path: Path, tmp_path: Path):
    """Verify persistence of processed CSV artifacts to disk."""
    config = load_dataset_config(sample_dataset_config_path)
    raw_df = load_raw_dataframe(config.raw_data_path).head(50)
    cases_df, reactions_df, result = run_canonicalization(raw_df, config, output_dir=tmp_path)

    cases_file = tmp_path / "canonical_cases.csv"
    reactions_file = tmp_path / "exploded_reactions.csv"

    assert cases_file.exists()
    assert reactions_file.exists()

    reloaded_cases = pd.read_csv(cases_file)
    reloaded_reactions = pd.read_csv(reactions_file)

    assert len(reloaded_cases) == len(cases_df)
    assert len(reloaded_reactions) == len(reactions_df)


def test_cli_canonicalize_command(tmp_path: Path):
    """Verify CLI canonicalize command executes and produces artifacts."""
    runner = CliRunner()
    out_dir = tmp_path / "processed_test"
    result = runner.invoke(cli, ["canonicalize", "-o", str(out_dir)])

    assert result.exit_code == 0
    assert "Canonicalization Summary" in result.output
    assert "Canonical Cases (1 per case ID)" in result.output
    assert "Exploded Reactions (1 per event)" in result.output
    assert (out_dir / "canonical_cases.csv").exists()
    assert (out_dir / "exploded_reactions.csv").exists()
