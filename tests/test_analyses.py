"""Unit and regression tests for deterministic analysis modules and analysis registry."""

import json
from pathlib import Path
import pandas as pd
import pytest
from click.testing import CliRunner

from genar.analyses import (
    AnalysisRegistry,
    compute_15_day_alerts,
    compute_demographics_breakdown,
    compute_interval_trends,
    compute_outcomes_analysis,
    compute_reactions_analysis,
    compute_seriousness_breakdown,
    compute_volume_summary,
)
from genar.cli import cli
from genar.config import load_dataset_config
from genar.ingest.canonicalizer import run_canonicalization
from genar.ingest.loader import load_raw_dataframe
from genar.models.analysis import AnalysisCategory, AnalysisResult


@pytest.fixture(scope="module")
def processed_data(sample_dataset_config_path: Path):
    """Fixture providing canonical case and reaction dataframes."""
    config = load_dataset_config(sample_dataset_config_path)
    raw_df = load_raw_dataframe(config.raw_data_path)
    cases_df, reactions_df, _ = run_canonicalization(raw_df, config)
    return cases_df, reactions_df, config


def test_registry_registration_and_discovery():
    """Verify all 7 standard analysis modules are registered in the AnalysisRegistry."""
    analyses = AnalysisRegistry.list_analyses()
    names = [a["name"] for a in analyses]
    assert "total_case_volume" in names
    assert "seriousness_breakdown" in names
    assert "demographics_breakdown" in names
    assert "reactions_analysis" in names
    assert "outcomes_analysis" in names
    assert "fifteen_day_alerts" in names
    assert "interval_trends" in names


def test_volume_analysis_exact_values(processed_data):
    """Verify total case volume and date range calculations."""
    cases_df, reactions_df, config = processed_data
    result = AnalysisRegistry.run_analysis("total_case_volume", cases_df, reactions_df, config)

    assert isinstance(result, AnalysisResult)
    assert result.metrics["total_cases"] == 1024
    assert result.metrics["total_reactions"] == 3429
    assert result.metrics["mean_reactions_per_case"] == 3.35
    assert result.metrics["reporting_period_start"] == "2024-12-27"
    assert result.metrics["reporting_period_end"] == "2025-12-26"
    assert len(result.contributing_case_ids) == 1024


def test_seriousness_analysis_exact_values(processed_data):
    """Verify exact counts and proportions for seriousness and individual criteria."""
    cases_df, reactions_df, config = processed_data
    result = AnalysisRegistry.run_analysis("seriousness_breakdown", cases_df, reactions_df, config)

    assert result.metrics["total_cases"] == 1024
    assert result.metrics["serious_cases"] == 1023
    assert result.metrics["non_serious_cases"] == 1
    assert result.metrics["serious_percent"] == 99.9

    criteria = result.metrics["criteria"]
    assert criteria["death_count"] == 68
    assert criteria["life_threatening_count"] == 105
    assert criteria["hospitalization_count"] == 482
    assert criteria["disabling_count"] == 44
    assert criteria["congenital_anomaly_count"] == 7
    assert criteria["other_medically_important_count"] == 905


def test_demographics_analysis_exact_values(processed_data):
    """Verify exact demographic distribution figures."""
    cases_df, reactions_df, config = processed_data
    result = AnalysisRegistry.run_analysis("demographics_breakdown", cases_df, reactions_df, config)

    sex_dist = result.metrics["sex_distribution"]
    assert sex_dist["FEMALE"] == 503
    assert sex_dist["MALE"] == 493
    assert sex_dist["UNKNOWN"] == 28

    age_dist = result.metrics["age_group_distribution"]
    assert age_dist["Pediatric (<18)"] == 16
    assert age_dist["Adult (18-64)"] == 249
    assert age_dist["Elderly (65+)"] == 676
    assert age_dist["UNKNOWN"] == 83

    country_dist = result.metrics["country_distribution"]
    assert country_dist["EU"] == 345
    assert country_dist["UNITED KINGDOM"] == 281
    assert country_dist["FRANCE"] == 185


def test_reactions_analysis_exact_values(processed_data):
    """Verify MedDRA PT frequencies, ranking, and case counts."""
    cases_df, reactions_df, config = processed_data
    result = AnalysisRegistry.run_analysis("reactions_analysis", cases_df, reactions_df, config, top_n=10)

    assert result.metrics["total_reactions"] == 3429
    assert result.metrics["unique_preferred_terms"] == 1122

    top_rxns = result.metrics["top_reactions_overall"]
    assert top_rxns[0]["preferred_term"] == "Acute kidney injury"
    assert top_rxns[0]["event_count"] == 80
    assert top_rxns[1]["preferred_term"] == "Drug ineffective"
    assert top_rxns[1]["event_count"] == 54
    assert top_rxns[2]["preferred_term"] == "Hypotension"
    assert top_rxns[2]["event_count"] == 46


def test_outcomes_analysis_exact_values(processed_data):
    """Verify outcome distribution in positionally aligned reactions."""
    cases_df, reactions_df, config = processed_data
    result = AnalysisRegistry.run_analysis("outcomes_analysis", cases_df, reactions_df, config)

    assert result.metrics["total_aligned_reactions"] == 3371
    assert result.metrics["total_unaligned_reactions"] == 58

    outcomes = result.metrics["outcome_distribution"]
    assert outcomes["recovered/resolved"] == 1257
    assert outcomes["unknown"] == 1028
    assert outcomes["not recovered/not resolved/ongoing"] == 512
    assert outcomes["recovering/resolving"] == 406
    assert outcomes["fatal"] == 134
    assert outcomes["recovered/resolved with sequelae"] == 34


def test_15_day_alerts_analysis_exact_values(processed_data):
    """Verify 15-day expedited alerts counts."""
    cases_df, reactions_df, config = processed_data
    result = AnalysisRegistry.run_analysis("fifteen_day_alerts", cases_df, reactions_df, config)

    assert result.metrics["fifteen_day_alerts_count"] == 1023
    assert result.metrics["fifteen_day_alerts_percent"] == 99.9
    assert "Acute kidney injury" in result.metrics["top_reactions_in_alerts"]


def test_interval_trends_analysis_exact_values(processed_data):
    """Verify monthly case aggregations and statistical candidate anomaly detection."""
    cases_df, reactions_df, config = processed_data
    result = AnalysisRegistry.run_analysis("interval_trends", cases_df, reactions_df, config)

    assert result.metrics["total_months"] == 13
    assert result.metrics["mean_monthly_volume"] > 0
    monthly_counts = result.metrics["monthly_counts"]
    assert monthly_counts["2024-12"] == 21
    assert monthly_counts["2025-07"] == 109


def test_run_all_analyses(processed_data):
    """Verify AnalysisRegistry.run_all executes every registered calculator with provenance."""
    cases_df, reactions_df, config = processed_data
    results = AnalysisRegistry.run_all(cases_df, reactions_df, config)

    assert len(results) >= 7
    for aid, res in results.items():
        assert isinstance(res, AnalysisResult)
        assert res.execution_time_ms is not None
        assert res.method_name is not None
        assert res.dataset_id == config.dataset_name


def test_cli_run_analysis_command(tmp_path: Path):
    """Verify CLI run-analysis command executes and outputs JSON artifact."""
    runner = CliRunner()
    json_out = tmp_path / "analysis_results.json"
    result = runner.invoke(cli, ["run-analysis", "-o", str(json_out)])

    assert result.exit_code == 0
    assert "Executed Deterministic Analyses" in result.output
    assert "total_case_volume" in result.output
    assert json_out.exists()

    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert "seriousness_breakdown" in data
    assert data["seriousness_breakdown"]["metrics"]["serious_cases"] == 1023
