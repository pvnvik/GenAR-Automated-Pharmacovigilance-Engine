"""Tests for configuration loading and schema validation."""

from pathlib import Path
import pytest
from pydantic import ValidationError
from genar.config import (
    DatasetConfig,
    ReportConfig,
    load_dataset_config,
    load_report_config,
)


def test_load_pader_report_config(sample_report_config_path: Path):
    """Verify default pader.yaml loads and validates cleanly."""
    config = load_report_config(sample_report_config_path)
    assert isinstance(config, ReportConfig)
    assert config.report_type == "PADER"
    assert len(config.sections) >= 5
    
    # Verify section IDs are unique and order is sequential
    section_ids = [s.id for s in config.sections]
    assert len(section_ids) == len(set(section_ids))
    assert "executive_summary" in section_ids
    assert "reactions_and_outcomes" in section_ids


def test_load_bisoprolol_dataset_config(sample_dataset_config_path: Path):
    """Verify default bisoprolol.yaml loads and validates cleanly."""
    config = load_dataset_config(sample_dataset_config_path)
    assert isinstance(config, DatasetConfig)
    assert config.product_name == "Bisoprolol"
    assert config.active_substance == "Bisoprolol Fumarate"
    assert len(config.age_buckets) == 3
    assert config.column_mapping.case_id == "safetyreportid"
    assert config.rules.deduplication_policy == "LATEST_VERSION"


def test_missing_config_raises_error(tmp_path: Path):
    """Verify FileNotFoundError is raised for non-existent configs."""
    missing_file = tmp_path / "non_existent.yaml"
    with pytest.raises(FileNotFoundError):
        load_report_config(missing_file)


def test_invalid_report_config(tmp_path: Path):
    """Verify invalid report config YAML fails Pydantic validation."""
    bad_yaml = tmp_path / "bad_report.yaml"
    bad_yaml.write_text("sections: 'not a list'", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid ReportConfig"):
        load_report_config(bad_yaml)
