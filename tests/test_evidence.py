"""Unit and regression tests for EvidenceStore, provenance tracking, and section EvidencePackets."""

import json
from pathlib import Path
import pytest
from click.testing import CliRunner

from genar.analyses.registry import AnalysisRegistry
from genar.cli import cli
from genar.config import load_dataset_config, load_report_config
from genar.evidence import (
    EvidenceStore,
    build_all_packets,
    build_evidence_packet,
)
from genar.ingest.canonicalizer import run_canonicalization
from genar.ingest.loader import load_raw_dataframe
from genar.models.evidence import EvidencePacket


@pytest.fixture(scope="module")
def populated_store(sample_dataset_config_path: Path):
    """Fixture providing populated EvidenceStore with all 7 analyses."""
    config = load_dataset_config(sample_dataset_config_path)
    raw_df = load_raw_dataframe(config.raw_data_path)
    cases_df, reactions_df, _ = run_canonicalization(raw_df, config)
    
    results = AnalysisRegistry.run_all(cases_df, reactions_df, config)
    store = EvidenceStore()
    store.add_many(results)
    return store, config


def test_evidence_store_crud_and_persistence(populated_store, tmp_path: Path):
    """Verify EvidenceStore indexing, persistence, and roundtrip loading."""
    store, _ = populated_store
    assert len(store.list_analyses()) >= 7
    assert store.get("total_case_volume") is not None
    assert store.get("non_existent") is None

    # Test JSON persistence
    dump_file = tmp_path / "store.json"
    store.save_to_json(dump_file)
    assert dump_file.exists()

    reloaded_store = EvidenceStore.load_from_json(dump_file)
    assert len(reloaded_store.list_analyses()) == len(store.list_analyses())
    assert reloaded_store.get("total_case_volume").metrics["total_cases"] == 1024


def test_evidence_provenance_generation(populated_store):
    """Verify EvidenceProvenance correctly extracts calculation metadata and sample case IDs."""
    store, _ = populated_store
    prov = store.get_provenance("total_case_volume")

    assert prov is not None
    assert prov.analysis_id == "total_case_volume"
    assert prov.category == "volume"
    assert prov.contributing_cases_count == 1024
    assert len(prov.sample_case_ids) == 5
    assert prov.method_name.endswith("compute_volume_summary")


def test_build_evidence_packet_executive_summary(populated_store, sample_report_config_path: Path):
    """Verify executive summary packet receives strictly declared volume/seriousness evidence."""
    store, dataset_cfg = populated_store
    report_cfg = load_report_config(sample_report_config_path)
    exec_cfg = next(s for s in report_cfg.sections if s.id == "executive_summary")

    packet = build_evidence_packet(exec_cfg, store, dataset_cfg)
    assert isinstance(packet, EvidencePacket)
    assert packet.section_id == "executive_summary"
    assert "total_case_volume" in packet.items
    assert "serious_case_count" in packet.items
    assert "non_serious_case_count" in packet.items
    assert "fifteen_day_alert_count" in packet.items
    
    # Verify summary metrics for template interpolation
    assert packet.summary_metrics["total_cases"] == 1024
    assert packet.summary_metrics["serious_cases"] == 1023
    assert packet.summary_metrics["fatalities_count"] == 68
    assert packet.summary_metrics["product_name"] == "Bisoprolol"

    # Verify unneeded demographic and trend evidence is excluded
    assert "demographics_summary" not in packet.items
    assert "interval_trends" not in packet.items


def test_build_evidence_packet_demographics(populated_store, sample_report_config_path: Path):
    """Verify demographics packet receives demographic distributions and table representation."""
    store, dataset_cfg = populated_store
    report_cfg = load_report_config(sample_report_config_path)
    demo_cfg = next(s for s in report_cfg.sections if s.id == "demographics")

    packet = build_evidence_packet(demo_cfg, store, dataset_cfg)
    assert packet.section_id == "demographics"
    assert "demographics_summary" in packet.items
    assert packet.table_data is not None
    assert len(packet.table_data) > 0

    # Ensure volume/trend items are excluded
    assert "total_case_volume" not in packet.items
    assert "interval_trends" not in packet.items


def test_build_evidence_packet_reactions_and_outcomes(populated_store, sample_report_config_path: Path):
    """Verify reactions and outcomes packet receives reaction rankings and outcome matrices."""
    store, dataset_cfg = populated_store
    report_cfg = load_report_config(sample_report_config_path)
    rxn_cfg = next(s for s in report_cfg.sections if s.id == "reactions_and_outcomes")

    packet = build_evidence_packet(rxn_cfg, store, dataset_cfg)
    assert packet.section_id == "reactions_and_outcomes"
    assert "top_adverse_reactions" in packet.items
    assert "reaction_outcomes_summary" in packet.items
    assert packet.table_data is not None

    # Verify demographics is excluded
    assert "demographics_summary" not in packet.items


def test_build_evidence_packet_trend_analysis(populated_store, sample_report_config_path: Path):
    """Verify trend analysis packet receives monthly series, non-invention rules, and anomalies."""
    store, dataset_cfg = populated_store
    report_cfg = load_report_config(sample_report_config_path)
    trend_cfg = next(s for s in report_cfg.sections if s.id == "trend_analysis")

    packet = build_evidence_packet(trend_cfg, store, dataset_cfg)
    assert packet.section_id == "trend_analysis"
    assert "interval_trends" in packet.items
    assert len(packet.non_invention_notes) > 0
    assert packet.table_data is not None


def test_build_all_packets_coverage(populated_store, sample_report_config_path: Path):
    """Verify all sections in report configuration receive isolated packets."""
    store, dataset_cfg = populated_store
    report_cfg = load_report_config(sample_report_config_path)

    packets = build_all_packets(report_cfg, store, dataset_cfg)
    assert len(packets) == len(report_cfg.sections)
    for section_cfg in report_cfg.sections:
        assert section_cfg.id in packets
        pkt = packets[section_cfg.id]
        assert pkt.dataset_name == dataset_cfg.dataset_name
        assert pkt.section_title == section_cfg.title


def test_cli_build_packets_command(tmp_path: Path):
    """Verify CLI build-packets command executes and outputs JSON artifact."""
    runner = CliRunner()
    out_file = tmp_path / "packets.json"
    result = runner.invoke(cli, ["build-packets", "-o", str(out_file)])

    assert result.exit_code == 0
    assert "Assembled Section Evidence Packets" in result.output
    assert out_file.exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "executive_summary" in data
    assert data["executive_summary"]["summary_metrics"]["total_cases"] == 1024
    assert len(data) == 8
