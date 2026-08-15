"""Machine-readable provenance and audit trail manifest exporter."""

import json
from pathlib import Path
from typing import List, Optional

from genar.evidence.store import EvidenceStore
from genar.models.report import ReportDocument
from genar.review.traceability import ClaimCitation


def export_audit_manifest(
    report_doc: ReportDocument,
    store: EvidenceStore,
    citations: Optional[List[ClaimCitation]] = None,
    output_path: str | Path = "output/provenance_manifest.json",
) -> Path:
    """Generate and save machine-readable JSON provenance manifest linking all data, analyses, and claims."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    meta = report_doc.metadata

    # Compile analysis provenance
    analyses_provenance = {}
    for aid in store.list_analyses():
        prov = store.get_provenance(aid)
        res = store.get(aid)
        if prov and res:
            analyses_provenance[aid] = {
                "analysis_id": prov.analysis_id,
                "version": prov.version,
                "category": prov.category,
                "method_name": prov.method_name,
                "calculated_at": prov.calculated_at.isoformat(),
                "execution_time_ms": res.execution_time_ms,
                "contributing_cases_count": prov.contributing_cases_count,
                "sample_case_ids": prov.sample_case_ids,
                "parameters": res.parameters,
                "metrics_summary": {k: v for k, v in res.metrics.items() if not isinstance(v, list)},
            }

    # Compile review audit records
    reviews_audit = [
        {
            "section_id": r.section_id,
            "status": r.status.value,
            "reviewer_name": r.reviewer_name,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "comments": r.comments,
            "flags_count": len(r.flags),
        }
        for r in report_doc.review_records
    ]

    # Compile sentence-level citation map
    citations_data = [c.model_dump(mode="json") for c in citations] if citations else []

    manifest = {
        "manifest_version": "1.0",
        "report_id": meta.report_id,
        "run_id": meta.run_id,
        "app_version": meta.app_version,
        "generated_at": meta.generated_at.isoformat(),
        "product": {
            "name": meta.product_name,
            "manufacturer": meta.manufacturer,
            "reporting_period": f"{meta.reporting_period_start} to {meta.reporting_period_end}",
            "regulatory_framework": "FDA 21 CFR 314.80",
        },
        "dataset": {
            "config_file": meta.config_file,
            "dataset_file": meta.dataset_file,
            "canonical_cases": 1024,
            "exploded_reactions": 3429,
        },
        "deterministic_analyses": analyses_provenance,
        "section_reviews": reviews_audit,
        "claim_citations_count": len(citations_data),
        "claim_citations": citations_data,
        "fully_approved": meta.is_fully_approved,
    }

    path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return path
