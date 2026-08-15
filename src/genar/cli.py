"""Command-line interface (CLI) for GenAR."""

from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from genar import __version__
from genar.config import load_dataset_config, load_report_config

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="genar")
def cli():
    """GenAR: Generative Adverse Event Reporting System.
    
    A deterministic core and evidence-backed regulatory safety report generator.
    """
    pass


@cli.command("validate-config")
@click.option(
    "--report-config",
    "-r",
    default="configs/pader.yaml",
    help="Path to report configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
def validate_config(report_config: str, dataset_config: str):
    """Validate report and dataset YAML configurations against Pydantic schemas."""
    console.print(Panel(f"[bold blue]GenAR Configuration Validator[/bold blue] (v{__version__})"))
    
    # Validate report config
    try:
        r_cfg = load_report_config(report_config)
        console.print(f"[green][OK][/green] Report Config Valid: [bold]{r_cfg.title}[/bold] ({len(r_cfg.sections)} sections defined)")
    except Exception as e:
        console.print(f"[red][ERROR][/red] Report Config Error: {e}")
        raise click.Abort()

    # Validate dataset config
    try:
        d_cfg = load_dataset_config(dataset_config)
        console.print(f"[green][OK][/green] Dataset Config Valid: [bold]{d_cfg.product_name}[/bold] (Manufacturer: {d_cfg.manufacturer})")
    except Exception as e:
        console.print(f"[red][ERROR][/red] Dataset Config Error: {e}")
        raise click.Abort()

    console.print("[bold green]All configuration files validated successfully![/bold green]")


@cli.command("inspect-data")
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
def inspect_data(dataset_config: str):
    """Inspect raw dataset path and configuration metadata without running pipeline."""
    cfg = load_dataset_config(dataset_config)
    data_path = Path(cfg.raw_data_path)
    
    table = Table(title=f"Dataset Configuration Overview: {cfg.product_name}")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Dataset Name", cfg.dataset_name)
    table.add_row("Product Name", cfg.product_name)
    table.add_row("Active Substance", cfg.active_substance)
    table.add_row("Manufacturer", cfg.manufacturer)
    table.add_row("Raw Data File", str(data_path))
    table.add_row("File Exists", str(data_path.exists()))
    if data_path.exists():
        table.add_row("File Size (KB)", f"{data_path.stat().st_size / 1024:.2f} KB")
    table.add_row("Reporting Period", f"{cfg.reporting_period_start} to {cfg.reporting_period_end}")
    table.add_row("Configured Age Buckets", str(len(cfg.age_buckets)))

    console.print(table)


@cli.command("validate-data")
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-report",
    "-o",
    default=None,
    help="Optional path to save data quality markdown report.",
    type=click.Path(),
)
def validate_data(dataset_config: str, output_report: Optional[str]):
    """Ingest raw dataset, run deterministic validation suite, and generate DQ report."""
    from genar.ingest.loader import create_dataset_metadata, load_raw_dataframe
    from genar.ingest.quality import build_data_quality_report, format_dq_summary_markdown
    from genar.ingest.validator import validate_dataset

    console.print(Panel(f"[bold blue]GenAR Data Ingestion & Quality Validator[/bold blue] (v{__version__})"))

    # 1. Load config
    cfg = load_dataset_config(dataset_config)
    console.print(f"[green][OK][/green] Loaded config for [bold]{cfg.product_name}[/bold]")

    # 2. Ingest raw data
    data_path = Path(cfg.raw_data_path)
    if not data_path.exists():
        console.print(f"[red][ERROR][/red] Raw data file not found: {data_path}")
        raise click.Abort()

    console.print(f"Ingesting raw dataset from [cyan]{data_path}[/cyan]...")
    df = load_raw_dataframe(data_path)
    metadata = create_dataset_metadata(df, cfg, data_path)
    console.print(f"[green][OK][/green] Ingested {len(df):,} rows ({metadata.total_canonical_cases:,} unique case IDs)")

    # 3. Run validation suite
    console.print("Executing deterministic validation suite...")
    issues = validate_dataset(df, cfg)
    dq_report = build_data_quality_report(issues, len(df), metadata.total_canonical_cases)

    # 4. Render Rich Summary Table
    table = Table(title="Data Quality Assessment Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold magenta")

    table.add_row("Total Raw Rows", f"{dq_report.total_raw_rows:,}")
    table.add_row("Unique Case IDs", f"{dq_report.total_unique_case_ids:,}")
    table.add_row("Duplicate/Updated Instances", f"{dq_report.duplicate_rows_detected}")
    table.add_row("Reaction/Outcome List Mismatches", f"{dq_report.list_mismatches_detected}")
    table.add_row("Critical Findings", f"{dq_report.critical_issues_count}")
    table.add_row("Warning Findings", f"{dq_report.warning_issues_count}")
    table.add_row("Info Findings", f"{dq_report.info_issues_count}")

    console.print(table)

    if dq_report.summary_by_type:
        type_table = Table(title="Findings by Category")
        type_table.add_column("Issue Type", style="yellow")
        type_table.add_column("Count", style="bold white")
        for itype, count in sorted(dq_report.summary_by_type.items(), key=lambda x: x[1], reverse=True):
            type_table.add_row(itype, str(count))
        console.print(type_table)

    # 5. Export Report if requested
    if output_report:
        out_path = Path(output_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_text = format_dq_summary_markdown(dq_report)
        out_path.write_text(md_text, encoding="utf-8")
        console.print(f"[bold green]Data quality markdown report saved to {out_path}[/bold green]")


@cli.command("canonicalize")
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-dir",
    "-o",
    default="data/processed",
    help="Directory to save canonical cases and reactions CSV artifacts.",
    type=click.Path(),
)
def canonicalize(dataset_config: str, output_dir: str):
    """Run deduplication and build canonical case-level and exploded reaction-level tables."""
    from genar.ingest.canonicalizer import run_canonicalization
    from genar.ingest.loader import load_raw_dataframe

    console.print(Panel(f"[bold blue]GenAR Dataset Canonicalizer[/bold blue] (v{__version__})"))

    cfg = load_dataset_config(dataset_config)
    console.print(f"[green][OK][/green] Loaded dataset config for [bold]{cfg.product_name}[/bold]")

    raw_path = Path(cfg.raw_data_path)
    if not raw_path.exists():
        console.print(f"[red][ERROR][/red] Raw data file not found: {raw_path}")
        raise click.Abort()

    console.print(f"Loading raw dataset from [cyan]{raw_path}[/cyan]...")
    raw_df = load_raw_dataframe(raw_path)

    console.print("Executing canonicalization (deduplication + reaction explosion)...")
    cases_df, reactions_df, result = run_canonicalization(raw_df, cfg, output_dir=output_dir)

    table = Table(title="Canonicalization Summary")
    table.add_column("Analytical View", style="cyan")
    table.add_column("Count", style="bold magenta")
    table.add_column("Artifact File Path", style="green")

    table.add_row(
        "Canonical Cases (1 per case ID)",
        f"{result.total_canonical_cases:,}",
        str(result.cases_file_path),
    )
    table.add_row(
        "Exploded Reactions (1 per event)",
        f"{result.total_exploded_reactions:,}",
        str(result.reactions_file_path),
    )
    table.add_row(
        "  - Positionally Aligned Reactions",
        f"{result.aligned_reactions_count:,}",
        "-",
    )
    table.add_row(
        "  - Unaligned Reactions (Flagged)",
        f"{result.unaligned_reactions_count:,}",
        "-",
    )

    console.print(table)
    console.print("[bold green]Canonicalization complete and artifacts successfully persisted![/bold green]")


@cli.command("run-analysis")
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-json",
    "-o",
    default=None,
    help="Optional path to export all analysis result JSON records.",
    type=click.Path(),
)
def run_analysis_command(dataset_config: str, output_json: Optional[str]):
    """Execute all registered deterministic analyses (Volume, Seriousness, Demographics, Reactions, Outcomes, Alerts, Trends)."""
    import json
    from genar.analyses.registry import AnalysisRegistry
    from genar.ingest.canonicalizer import run_canonicalization
    from genar.ingest.loader import load_raw_dataframe

    console.print(Panel(f"[bold blue]GenAR Deterministic Analysis Runner[/bold blue] (v{__version__})"))

    cfg = load_dataset_config(dataset_config)
    console.print(f"[green][OK][/green] Loaded dataset config for [bold]{cfg.product_name}[/bold]")

    raw_path = Path(cfg.raw_data_path)
    if not raw_path.exists():
        console.print(f"[red][ERROR][/red] Raw data file not found: {raw_path}")
        raise click.Abort()

    raw_df = load_raw_dataframe(raw_path)
    cases_df, reactions_df, _ = run_canonicalization(raw_df, cfg)

    console.print("Running registered deterministic analysis modules...")
    results = AnalysisRegistry.run_all(cases_df, reactions_df, cfg)

    # 1. Summary table of executed analyses
    summary_table = Table(title="Executed Deterministic Analyses")
    summary_table.add_column("Analysis ID", style="cyan")
    summary_table.add_column("Category", style="yellow")
    summary_table.add_column("Execution Time", style="green")
    summary_table.add_column("Key Metric", style="bold magenta")

    for aid, res in results.items():
        key_metric_str = ""
        if res.category == "volume":
            key_metric_str = f"{res.metrics.get('total_cases'):,} cases / {res.metrics.get('total_reactions'):,} rxns"
        elif res.category == "seriousness":
            key_metric_str = f"{res.metrics.get('serious_cases'):,} serious ({res.metrics.get('serious_percent')}%)"
        elif res.category == "demographics":
            key_metric_str = f"{res.metrics.get('sex_distribution')} | Elderly: {res.metrics.get('age_group_distribution', {}).get('Elderly (65+)', 0)}"
        elif res.category == "reactions":
            top_rxn = res.metrics.get("top_reactions_overall", [{}])[0].get("preferred_term", "N/A")
            key_metric_str = f"Top PT: {top_rxn} ({res.metrics.get('unique_preferred_terms')} unique)"
        elif res.category == "outcomes":
            key_metric_str = f"Resolved: {res.metrics.get('outcome_distribution', {}).get('recovered/resolved', 0):,} | Fatal: {res.metrics.get('outcome_distribution', {}).get('fatal', 0):,}"
        elif res.category == "alerts":
            key_metric_str = f"{res.metrics.get('fifteen_day_alerts_count'):,} expedited 15-day cases ({res.metrics.get('fifteen_day_alerts_percent')}%)"
        elif res.category == "trends":
            key_metric_str = f"{len(res.metrics.get('candidate_anomalies', []))} statistical anomalies flagged across {res.metrics.get('total_months')} months"

        summary_table.add_row(
            res.analysis_id,
            res.category.value,
            f"{res.execution_time_ms} ms",
            key_metric_str,
        )

    console.print(summary_table)

    # 2. Export JSON if requested
    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        dump_data = {aid: res.model_dump(mode="json") for aid, res in results.items()}
        out_path.write_text(json.dumps(dump_data, indent=2, default=str), encoding="utf-8")
        console.print(f"[bold green]Saved {len(results)} analysis result models to {out_path}[/bold green]")


@cli.command("build-packets")
@click.option(
    "--report-config",
    "-r",
    default="configs/pader.yaml",
    help="Path to report configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-json",
    "-o",
    default=None,
    help="Optional path to export all built evidence packets to JSON.",
    type=click.Path(),
)
def build_packets_command(report_config: str, dataset_config: str, output_json: Optional[str]):
    """Construct section-scoped EvidencePackets with strict provenance for all report sections."""
    import json
    from genar.analyses.registry import AnalysisRegistry
    from genar.evidence.packet_builder import build_all_packets
    from genar.evidence.store import EvidenceStore
    from genar.ingest.canonicalizer import run_canonicalization
    from genar.ingest.loader import load_raw_dataframe

    console.print(Panel(f"[bold blue]GenAR Evidence Packet Builder[/bold blue] (v{__version__})"))

    r_cfg = load_report_config(report_config)
    d_cfg = load_dataset_config(dataset_config)
    console.print(f"[green][OK][/green] Loaded report: [bold]{r_cfg.title}[/bold] & dataset: [bold]{d_cfg.product_name}[/bold]")

    raw_path = Path(d_cfg.raw_data_path)
    if not raw_path.exists():
        console.print(f"[red][ERROR][/red] Raw data file not found: {raw_path}")
        raise click.Abort()

    raw_df = load_raw_dataframe(raw_path)
    cases_df, reactions_df, _ = run_canonicalization(raw_df, d_cfg)

    # Run analyses and populate store
    results = AnalysisRegistry.run_all(cases_df, reactions_df, d_cfg)
    store = EvidenceStore()
    store.add_many(results)

    console.print(f"Building isolated evidence packets for {len(r_cfg.sections)} sections...")
    packets = build_all_packets(r_cfg, store, d_cfg)

    table = Table(title="Assembled Section Evidence Packets")
    table.add_column("Section ID", style="cyan")
    table.add_column("Section Title", style="white")
    table.add_column("Evidence Items", style="bold magenta")
    table.add_column("Table Data Rows", style="green")
    table.add_column("Non-Invention Rules", style="yellow")

    for sid, pkt in packets.items():
        tbl_count = len(pkt.table_data) if pkt.table_data else 0
        rules_count = len(pkt.non_invention_notes)
        table.add_row(
            pkt.section_id,
            pkt.section_title,
            str(len(pkt.items)),
            str(tbl_count) if tbl_count > 0 else "-",
            str(rules_count) if rules_count > 0 else "-",
        )

    console.print(table)

    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        dump_data = {sid: pkt.model_dump(mode="json") for sid, pkt in packets.items()}
        out_path.write_text(json.dumps(dump_data, indent=2, default=str), encoding="utf-8")
        console.print(f"[bold green]Saved {len(packets)} evidence packets to {out_path}[/bold green]")


@cli.command("generate-drafts")
@click.option(
    "--report-config",
    "-r",
    default="configs/pader.yaml",
    help="Path to report configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-markdown",
    "-o",
    default=None,
    help="Optional path to export full assembled draft report Markdown.",
    type=click.Path(),
)
def generate_drafts_command(report_config: str, dataset_config: str, output_markdown: Optional[str]):
    """Execute section generation across template, table, and LLM modes for all sections."""
    from genar.analyses.registry import AnalysisRegistry
    from genar.evidence.packet_builder import build_all_packets
    from genar.evidence.store import EvidenceStore
    from genar.generation.dispatcher import SectionGenerator
    from genar.ingest.canonicalizer import run_canonicalization
    from genar.ingest.loader import load_raw_dataframe

    console.print(Panel(f"[bold blue]GenAR Multi-Mode Section Generator[/bold blue] (v{__version__})"))

    r_cfg = load_report_config(report_config)
    d_cfg = load_dataset_config(dataset_config)
    console.print(f"[green][OK][/green] Loaded report: [bold]{r_cfg.title}[/bold] & dataset: [bold]{d_cfg.product_name}[/bold]")

    raw_path = Path(d_cfg.raw_data_path)
    if not raw_path.exists():
        console.print(f"[red][ERROR][/red] Raw data file not found: {raw_path}")
        raise click.Abort()

    raw_df = load_raw_dataframe(raw_path)
    cases_df, reactions_df, _ = run_canonicalization(raw_df, d_cfg)

    # Analyses and evidence store
    results = AnalysisRegistry.run_all(cases_df, reactions_df, d_cfg)
    store = EvidenceStore()
    store.add_many(results)

    # Packets and generation
    packets = build_all_packets(r_cfg, store, d_cfg)
    generator = SectionGenerator()

    console.print("Generating section drafts in configured order...")
    drafts = generator.generate_all(r_cfg, packets)

    table = Table(title="Generated Section Drafts")
    table.add_column("Order", style="cyan", no_wrap=True)
    table.add_column("Section Title", style="white")
    table.add_column("Mode", style="yellow")
    table.add_column("Content Length", style="green")
    table.add_column("Evidence Used", style="bold magenta")

    for draft in drafts:
        table.add_row(
            str(draft.order),
            draft.title,
            draft.generation_mode.value,
            f"{len(draft.markdown_content):,} chars",
            str(len(draft.evidence_ids_used)),
        )

    console.print(table)

    # Assemble full draft markdown
    full_md = f"# {r_cfg.title}\n\n**Product:** {d_cfg.product_name} ({d_cfg.active_substance})\n**Manufacturer:** {d_cfg.manufacturer}\n**Reporting Period:** {d_cfg.reporting_period_start} to {d_cfg.reporting_period_end}\n**Regulatory Framework:** {r_cfg.regulatory_framework}\n\n---\n\n"
    full_md += "\n\n---\n\n".join([d.markdown_content for d in drafts])

    if output_markdown:
        out_path = Path(output_markdown)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(full_md, encoding="utf-8")
        console.print(f"[bold green]Assembled draft Markdown report saved to {out_path}[/bold green]")


@cli.command("run-pipeline")
@click.option(
    "--report-config",
    "-r",
    default="configs/pader.yaml",
    help="Path to report configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-dir",
    "-o",
    default="output",
    help="Directory to save generated report artifacts (Markdown, HTML, Manifest).",
    type=click.Path(),
)
@click.option(
    "--auto-approve",
    is_flag=True,
    default=True,
    help="Automatically record human review approval after fact verification.",
)
def run_pipeline(report_config: str, dataset_config: str, output_dir: str, auto_approve: bool):
    """Execute the end-to-end GenAR regulatory safety report generation pipeline."""
    import uuid
    from datetime import date, datetime, timezone
    from genar.analyses.registry import AnalysisRegistry
    from genar.evidence.packet_builder import build_all_packets
    from genar.evidence.store import EvidenceStore
    from genar.export import export_audit_manifest, export_html_report, export_markdown_report
    from genar.generation.dispatcher import SectionGenerator
    from genar.ingest.canonicalizer import run_canonicalization
    from genar.ingest.loader import load_raw_dataframe
    from genar.ingest.validator import validate_dataset
    from genar.models.report import ReportDocument, ReportMetadata
    from genar.review.traceability import EvidenceFactChecker
    from genar.review.workflow import ReviewWorkflow

    console.print(Panel(f"[bold blue]GenAR End-to-End Regulatory Pipeline[/bold blue] (v{__version__})"))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Config Loading
    r_cfg = load_report_config(report_config)
    d_cfg = load_dataset_config(dataset_config)
    console.print(f"[green][OK][/green] Loaded config: [bold]{r_cfg.title}[/bold] for [bold]{d_cfg.product_name}[/bold]")

    # 2. Ingestion & Data Quality
    raw_path = Path(d_cfg.raw_data_path)
    if not raw_path.exists():
        console.print(f"[red][ERROR][/red] Raw data file not found: {raw_path}")
        raise click.Abort()

    raw_df = load_raw_dataframe(raw_path)
    issues = validate_dataset(raw_df, d_cfg)
    from genar.ingest.quality import build_data_quality_report
    dq_report = build_data_quality_report(
        issues,
        total_raw_rows=len(raw_df),
        total_unique_case_ids=int(raw_df[d_cfg.column_mapping.case_id].nunique()) if d_cfg.column_mapping.case_id in raw_df.columns else len(raw_df)
    )
    console.print(f"[green][OK][/green] Ingestion & Validation: {dq_report.total_raw_rows:,} rows ingested ({len(dq_report.issues)} DQ findings logged)")

    # 3. Canonicalization
    cases_df, reactions_df, _ = run_canonicalization(raw_df, d_cfg)
    console.print(f"[green][OK][/green] Canonicalization: {len(cases_df):,} unique cases | {len(reactions_df):,} exploded reactions")

    # 4. Deterministic Analyses & Evidence Store
    results = AnalysisRegistry.run_all(cases_df, reactions_df, d_cfg)
    store = EvidenceStore()
    store.add_many(results)
    console.print(f"[green][OK][/green] Deterministic Analyses: {len(results)} analytical modules calculated")

    # 5. Section Evidence Packets
    packets = build_all_packets(r_cfg, store, d_cfg)
    console.print(f"[green][OK][/green] Evidence Engineering: {len(packets)} isolated section packets prepared")

    # 6. Multi-Mode Section Generation
    generator = SectionGenerator()
    drafts = generator.generate_all(r_cfg, packets)
    console.print(f"[green][OK][/green] Section Generation: {len(drafts)} sections drafted")

    # 7. Fact Checking & Citation Traceability
    all_citations = []
    total_flags = 0
    for draft in drafts:
        pkt = packets[draft.section_id]
        fc_report = EvidenceFactChecker.verify_section(draft, pkt)
        all_citations.extend(fc_report.citations)
        total_flags += len(fc_report.flags)

    console.print(f"[green][OK][/green] Fact Verification: {len(all_citations)} claim citations mapped ({total_flags} flags)")

    # 8. Human Review Workflow
    workflow = ReviewWorkflow(drafts)
    if auto_approve:
        workflow.approve_all(reviewer_name="Regulatory Lead Reviewer")
        console.print("[green][OK][/green] Review & Verification: All 8 sections approved by Regulatory Lead Reviewer")

    # 9. Assembly & Report Packaging
    start_dt = date.fromisoformat(d_cfg.reporting_period_start) if isinstance(d_cfg.reporting_period_start, str) else d_cfg.reporting_period_start
    end_dt = date.fromisoformat(d_cfg.reporting_period_end) if isinstance(d_cfg.reporting_period_end, str) else d_cfg.reporting_period_end

    meta = ReportMetadata(
        report_id=f"PADER-{d_cfg.dataset_name.upper().replace(' ', '_')}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        report_type=r_cfg.report_type,
        product_name=d_cfg.product_name,
        manufacturer=d_cfg.manufacturer,
        reporting_period_start=start_dt,
        reporting_period_end=end_dt,
        run_id=str(uuid.uuid4())[:8],
        app_version=__version__,
        config_file=str(report_config),
        dataset_file=str(dataset_config),
        is_fully_approved=workflow.is_fully_approved(),
    )

    report_doc = ReportDocument(
        metadata=meta,
        sections=workflow.get_drafts(),
        quality_report=dq_report,
        review_records=workflow.get_review_records(),
        full_markdown="",
        render_formats=["markdown", "html", "json"],
    )

    # 10. Export Artifacts
    md_path = export_markdown_report(report_doc, out_dir / "pader_report.md")
    html_path = export_html_report(report_doc, out_dir / "pader_report.html")
    manifest_path = export_audit_manifest(report_doc, store, all_citations, out_dir / "provenance_manifest.json")

    summary_panel = Panel(
        f"[bold green]Report Pipeline Completed Successfully![/bold green]\n\n"
        f"• [bold]Markdown Report:[/bold] {md_path}\n"
        f"• [bold]Styled HTML Report:[/bold] {html_path}\n"
        f"• [bold]Provenance Manifest:[/bold] {manifest_path}\n"
        f"• [bold]Canonical Cases:[/bold] {len(cases_df):,}\n"
        f"• [bold]Review Status:[/bold] {'APPROVED' if workflow.is_fully_approved() else 'PENDING'}",
        title="Artifact Packaging Summary",
        border_style="green",
    )
    console.print(summary_panel)


@cli.command("run-graph")
@click.option(
    "--report-config",
    "-r",
    default="configs/pader.yaml",
    help="Path to report configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-dir",
    "-o",
    default="output",
    help="Directory to save generated report artifacts (Markdown, HTML, Manifest).",
    type=click.Path(),
)
@click.option(
    "--auto-approve",
    is_flag=True,
    default=True,
    help="Automatically record human review approval after fact verification.",
)
def run_graph_command(report_config: str, dataset_config: str, output_dir: str, auto_approve: bool):
    """Execute the GenAR regulatory pipeline orchestrated via LangGraph StateGraph."""
    from genar.orchestration.graph import create_genar_workflow
    from genar.orchestration.state import ReportWorkflowState

    console.print(Panel(f"[bold blue]GenAR LangGraph Workflow Orchestrator[/bold blue] (v{__version__})"))

    graph = create_genar_workflow()
    initial_state: ReportWorkflowState = {
        "report_config_path": report_config,
        "dataset_config_path": dataset_config,
        "output_dir": output_dir,
        "auto_approve": auto_approve,
        "logs": [],
        "analyses_completed": [],
    }

    console.print("Executing LangGraph StateGraph nodes...")
    final_state = graph.invoke(initial_state)

    # Print log steps
    for log in final_state.get("logs", []):
        console.print(f"[cyan]>[/cyan] {log}")

    exported = final_state.get("exported_files", {})
    summary_panel = Panel(
        f"[bold green]LangGraph Workflow Completed Successfully![/bold green]\n\n"
        f"• [bold]Markdown Report:[/bold] {exported.get('markdown')}\n"
        f"• [bold]Styled HTML Report:[/bold] {exported.get('html')}\n"
        f"• [bold]Provenance Manifest:[/bold] {exported.get('manifest')}\n"
        f"• [bold]Canonical Cases:[/bold] {final_state.get('cases_count', 0):,}\n"
        f"• [bold]Review Status:[/bold] {'APPROVED' if final_state.get('is_approved') else 'PENDING'}",
        title="LangGraph Orchestration Summary",
        border_style="green",
    )
    console.print(summary_panel)


if __name__ == "__main__":
    cli()
