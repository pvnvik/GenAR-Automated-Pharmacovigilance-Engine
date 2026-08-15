# Phase 8: Human-in-the-Loop Review, Traceability & Fact Verification

## 1. Overview & Objective
Phase 8 implements the **Human Review Workflow & Citation Traceability Layer** for the **GenAR** system.

In safety reporting, automated drafting must never bypass expert pharmacovigilance oversight:
1. **`ReviewWorkflow` (`src/genar/review/workflow.py`)**: Manages per-section and report-level human review states (`DRAFT`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `FINAL`). Records reviewer identity, timestamps, revision notes, and enables feedback-directed regeneration.
2. **`EvidenceFactChecker` (`src/genar/review/traceability.py`)**: Deterministically scans section drafts to cross-check all numerical figures against approved `EvidenceItem` values in the section packet. Generates sentence-level claim-to-evidence citations linking directly back to Python analysis modules and raw contributing cases.

All goals for Phase 8 have been completed and verified with **61/61 passing unit and integration tests**.

---

## 2. Directory Layout & Implemented Files

```
pvn-vikrant-genar-challenge/
├── src/
│   └── genar/
│       ├── models/
│       │   ├── review.py           # ReviewStatus, ReviewRecord, ReviewFlag
│       │   └── section.py          # SectionDraft, SectionFeedback
│       ├── review/
│       │   ├── __init__.py         # Review module exports
│       │   ├── workflow.py         # ReviewWorkflow state machine & feedback loop
│       │   └── traceability.py     # EvidenceFactChecker & ClaimCitation mapping
│       └── ...
├── tasks/
│   ├── phase8.md                   # Phase 8 documentation & test guide
│   └── phase9.md                   # Phase 9 documentation & test guide
└── tests/
    └── test_review_and_export.py   # Full test suite covering review & export
```

---

## 3. Review Workflow & Claim Traceability Architecture

### 1. `ReviewWorkflow`
- **State Tracking**: Initializes each generated section in `PENDING_REVIEW`.
- **Reviewer Sign-off**: Records `reviewer_name` (e.g. "Regulatory Lead Reviewer"), ISO timestamps, and specific clinical comments.
- **Revision Loop**: `regenerate_section()` accepts reviewer feedback and re-invokes the generation engine while maintaining an audit trail of previous drafts.
- **Report Finalization**: `is_fully_approved()` enforces that a report cannot be finalized until all 8 sections have explicit reviewer approvals.

### 2. Sentence-Level Traceability Chain
Every statement in the report is traced through:
$$\text{Claim / Sentence} \rightarrow \text{EvidenceItem} \rightarrow \text{AnalysisResult} \rightarrow \text{Contributing Case IDs} \rightarrow \text{Source Row Indices}$$

Example claim citation from `narrative_summary`:
```json
{
  "section_id": "narrative_summary",
  "sentence": "During the cumulative reporting interval (2024-12-27 to 2025-12-26), a total of 1,024 spontaneous adverse experience cases were received and evaluated for Bisoprolol.",
  "verified": true,
  "evidence_id": "ev_total_case_volume",
  "analysis_id": "total_case_volume",
  "method_name": "genar.analyses.volume.compute_volume_summary",
  "contributing_cases_count": 1024,
  "sample_case_ids": ["24780403", "24780599", "24780680", "24784771", "24784845"],
  "metric_value": 1024
}
```

---

## 4. Phase 8 Checklist & Definition of Done

- [x] `ReviewWorkflow` implemented with status transitions (`PENDING_REVIEW` -> `APPROVED` / `REJECTED`), reviewer stamping, and feedback-directed regeneration.
- [x] `EvidenceFactChecker` implemented with deterministic number cross-validation and sentence-level `ClaimCitation` mapping.
- [x] Full provenance maintained: every claim links back to analysis IDs and contributing case ID lists.
- [x] Unit and integration tests in `tests/test_review_and_export.py` passing with 100% success rate.

---

## 5. How to Run and Test Phase 8

Run complete test suite:
```powershell
python -m pytest tests/test_review_and_export.py -v
```
