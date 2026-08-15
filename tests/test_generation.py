"""Unit and regression tests for section generation, template rendering, tables, and LLM dispatching."""

from pathlib import Path
import pytest
from click.testing import CliRunner

from genar.analyses.registry import AnalysisRegistry
from genar.cli import cli
from genar.config import load_dataset_config, load_report_config
from genar.evidence import EvidenceStore, build_all_packets, build_evidence_packet
from genar.generation import (
    LLMGenerator,
    SectionGenerator,
    build_llm_prompt,
    render_markdown_table,
    render_table_section,
    render_template_section,
)
from genar.ingest.canonicalizer import run_canonicalization
from genar.ingest.loader import load_raw_dataframe
from genar.models.section import GenerationMode, SectionDraft


@pytest.fixture(scope="module")
def generation_context(sample_dataset_config_path: Path, sample_report_config_path: Path):
    """Fixture providing populated store, report config, and built evidence packets."""
    dataset_cfg = load_dataset_config(sample_dataset_config_path)
    report_cfg = load_report_config(sample_report_config_path)
    
    raw_df = load_raw_dataframe(dataset_cfg.raw_data_path)
    cases_df, reactions_df, _ = run_canonicalization(raw_df, dataset_cfg)
    
    results = AnalysisRegistry.run_all(cases_df, reactions_df, dataset_cfg)
    store = EvidenceStore()
    store.add_many(results)
    
    packets = build_all_packets(report_cfg, store, dataset_cfg)
    return report_cfg, dataset_cfg, packets


def test_render_template_section(generation_context):
    """Verify deterministic template interpolation produces exact markdown with figures."""
    report_cfg, _, packets = generation_context
    exec_cfg = next(s for s in report_cfg.sections if s.id == "executive_summary")
    packet = packets["executive_summary"]

    rendered = render_template_section(exec_cfg, packet)
    assert "## 1. Executive Summary & Overview" in rendered
    assert "1,024" in rendered
    assert "1,023" in rendered
    assert "68" in rendered
    assert "Bisoprolol" in rendered


def test_render_markdown_table():
    """Verify formatting of arbitrary dictionary rows into GitHub Flavored Markdown table."""
    headers = ["Category", "Case Count", "Percentage"]
    rows = [
        {"Category": "Elderly (65+)", "Case Count": 676, "Percentage": 66.02},
        {"Category": "Adult (18-64)", "Case Count": 249, "Percentage": 24.32},
    ]
    table_md = render_markdown_table(headers, rows)
    assert "| Category | Case Count | Percentage |" in table_md
    assert "| Elderly (65+) | 676 | 66.02% |" in table_md
    assert "| Adult (18-64) | 249 | 24.32% |" in table_md


def test_render_table_section(generation_context):
    """Verify table section renders title and formatted markdown table."""
    report_cfg, _, packets = generation_context
    demo_cfg = next(s for s in report_cfg.sections if s.id == "demographics")
    packet = packets["demographics"]

    rendered = render_table_section(demo_cfg, packet)
    assert "## 4. Demographic Distribution" in rendered
    assert "| Demographic Category | Sub-category | Cases | Percentage (%) |" in rendered
    assert "Elderly (65+)" in rendered
    assert "676" in rendered


def test_build_llm_prompt(generation_context):
    """Verify prompt formatting contains system prompt, evidence JSON, and non-invention rules."""
    report_cfg, _, packets = generation_context
    narr_cfg = next(s for s in report_cfg.sections if s.id == "narrative_summary")
    packet = packets["narrative_summary"]

    sys_prompt, user_prompt = build_llm_prompt(narr_cfg, packet)
    assert "specialized in Periodic Adverse Drug Experience Reports" in sys_prompt
    assert "Approved Evidence Packet:" in user_prompt
    assert '"total_cases": 1024' in user_prompt
    assert "Non-Invention Instructions:" in user_prompt


def test_llm_generator_deterministic_fallback(generation_context):
    """Verify offline deterministic generator synthesizes grounded narrative from approved facts."""
    report_cfg, _, packets = generation_context
    narr_cfg = next(s for s in report_cfg.sections if s.id == "narrative_summary")
    packet = packets["narrative_summary"]

    llm = LLMGenerator()
    narrative = llm.generate(narr_cfg, packet)

    assert "## 7. Narrative Summary & Clinical Evaluation" in narrative
    assert "1,024" in narrative
    assert "1,023" in narrative
    assert "Acute kidney injury" in narrative
    assert "No new unexpected safety signals" in narrative


def test_section_generator_dispatch_modes(generation_context):
    """Verify SectionGenerator correctly routes generation according to section mode."""
    report_cfg, _, packets = generation_context
    generator = SectionGenerator()

    # 1. Template section
    exec_cfg = next(s for s in report_cfg.sections if s.id == "executive_summary")
    exec_draft = generator.generate_section(exec_cfg, packets["executive_summary"])
    assert exec_draft.generation_mode == GenerationMode.TEMPLATE
    assert "1,024" in exec_draft.markdown_content

    # 2. Table section
    demo_cfg = next(s for s in report_cfg.sections if s.id == "demographics")
    demo_draft = generator.generate_section(demo_cfg, packets["demographics"])
    assert demo_draft.generation_mode == GenerationMode.TABLE
    assert "| Demographic Category |" in demo_draft.markdown_content

    # 3. LLM section
    narr_cfg = next(s for s in report_cfg.sections if s.id == "narrative_summary")
    narr_draft = generator.generate_section(narr_cfg, packets["narrative_summary"])
    assert narr_draft.generation_mode == GenerationMode.LLM
    assert "1,024" in narr_draft.markdown_content

    # 4. Table + LLM section
    rxn_cfg = next(s for s in report_cfg.sections if s.id == "reactions_and_outcomes")
    rxn_draft = generator.generate_section(rxn_cfg, packets["reactions_and_outcomes"])
    assert rxn_draft.generation_mode == GenerationMode.TABLE_AND_LLM
    assert "| Preferred Term (PT) |" in rxn_draft.markdown_content
    assert "Clinical Analysis and Interpretation" in rxn_draft.markdown_content


def test_generate_all_sections_coverage(generation_context):
    """Verify all 8 configured sections are generated in exact order."""
    report_cfg, _, packets = generation_context
    generator = SectionGenerator()

    drafts = generator.generate_all(report_cfg, packets)
    assert len(drafts) == len(report_cfg.sections)
    
    for i, draft in enumerate(drafts):
        assert draft.order == i + 1
        assert len(draft.markdown_content) > 50


def test_cli_generate_drafts_command(tmp_path: Path):
    """Verify CLI generate-drafts command executes and outputs markdown report artifact."""
    runner = CliRunner()
    out_md = tmp_path / "draft_report.md"
    result = runner.invoke(cli, ["generate-drafts", "-o", str(out_md)])

    assert result.exit_code == 0
    assert "Generated Section Drafts" in result.output
    assert out_md.exists()

    content = out_md.read_text(encoding="utf-8")
    assert "# Periodic Adverse Drug Experience Report (PADER)" in content
    assert "## 1. Executive Summary & Overview" in content
    assert "## 8. Actions Taken for Safety Reasons" in content
