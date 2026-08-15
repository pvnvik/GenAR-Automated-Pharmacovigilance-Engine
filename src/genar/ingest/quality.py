"""Aggregator and reporter for Data Quality (DQ) findings."""

from collections import Counter
from typing import Dict, List
import pandas as pd

from genar.models.quality import (
    DQIssue,
    DQIssueType,
    DQSeverity,
    DataQualityReport,
)


def build_data_quality_report(
    issues: List[DQIssue],
    total_raw_rows: int,
    total_unique_case_ids: int
) -> DataQualityReport:
    """Aggregate a list of DQ findings into a structured DataQualityReport."""
    summary_by_type: Dict[str, int] = dict(Counter([i.issue_type.value for i in issues]))
    
    crit_count = sum(1 for i in issues if i.severity == DQSeverity.CRITICAL)
    warn_count = sum(1 for i in issues if i.severity == DQSeverity.WARNING)
    info_count = sum(1 for i in issues if i.severity == DQSeverity.INFO)

    dup_count = summary_by_type.get(DQIssueType.DUPLICATE_CASE_ID.value, 0) + summary_by_type.get(DQIssueType.UPDATED_CASE_ROW.value, 0)
    list_mismatch_count = summary_by_type.get(DQIssueType.LIST_LENGTH_MISMATCH.value, 0)

    return DataQualityReport(
        total_raw_rows=total_raw_rows,
        total_unique_case_ids=total_unique_case_ids,
        duplicate_rows_detected=dup_count,
        list_mismatches_detected=list_mismatch_count,
        critical_issues_count=crit_count,
        warning_issues_count=warn_count,
        info_issues_count=info_count,
        issues=issues,
        summary_by_type=summary_by_type,
    )


def format_dq_summary_markdown(report: DataQualityReport) -> str:
    """Generate clean, reviewer-facing Markdown summary of data quality findings."""
    md_lines = [
        "## Data Quality and Integrity Assessment",
        "",
        f"- **Total Raw Rows Ingested:** {report.total_raw_rows:,}",
        f"- **Unique Safety Report IDs:** {report.total_unique_case_ids:,}",
        f"- **Duplicate/Updated Case Instances:** {report.duplicate_rows_detected}",
        f"- **Reaction/Outcome List Alignment Mismatches:** {report.list_mismatches_detected}",
        f"- **Total Findings:** Critical ({report.critical_issues_count}), Warnings ({report.warning_issues_count}), Info ({report.info_issues_count})",
        "",
    ]

    if report.summary_by_type:
        md_lines.append("### Findings Breakdown by Category")
        md_lines.append("| Issue Type | Count |")
        md_lines.append("| :--- | :--- |")
        for itype, count in sorted(report.summary_by_type.items(), key=lambda x: x[1], reverse=True):
            md_lines.append(f"| `{itype}` | {count} |")
        md_lines.append("")

    if report.critical_issues_count > 0:
        md_lines.append("### Critical Quality Alerts")
        for iss in report.issues:
            if iss.severity == DQSeverity.CRITICAL:
                md_lines.append(f"- **[CRITICAL]** {iss.message}")
        md_lines.append("")

    if report.list_mismatches_detected > 0:
        md_lines.append("### Positional List Mismatch Details")
        md_lines.append("The following cases contain comma-separated reaction lists whose lengths differ from their associated outcome lists (likely due to embedded commas in MedDRA terms):")
        for iss in report.issues:
            if iss.issue_type == DQIssueType.LIST_LENGTH_MISMATCH:
                md_lines.append(f"- **Case `{iss.safety_report_id}` (Row {iss.row_index}):** {iss.raw_value}")
        md_lines.append("")

    return "\n".join(md_lines)
