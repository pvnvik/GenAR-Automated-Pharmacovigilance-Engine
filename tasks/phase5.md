# Phase 5: Evidence Management, Provenance Tracking & Section Evidence Packets

## 1. Overview & Objective
Phase 5 implements the **Evidence Management & Context Engineering Layer** for the **GenAR** system.

In regulatory report generation, sending the raw dataset or entire analysis store to an LLM introduces risks of number distortion, false causality claims, and ungrounded statements. Phase 5 enforces **strict context isolation**:
1. **`EvidenceStore` (`src/genar/evidence/store.py`)**: Indexes deterministic `AnalysisResult` objects and manufactures traceable `EvidenceItem` instances stamped with `EvidenceProvenance` (capturing `analysis_id`, `version`, `category`, `method_name`, `calculated_at`, contributing case counts, and sample case IDs).
2. **`packet_builder.py` (`src/genar/evidence/packet_builder.py`)**: Assembles section-specific `EvidencePacket` objects strictly filtered to include **only** the approved facts declared in each section's `required_evidence` configuration in `configs/pader.yaml`.

All goals for Phase 5 have been completed and verified with **47/47 passing unit and regression tests**.

---

## 2. Directory Layout & Implemented Files

```
pvn-vikrant-genar-challenge/
├── configs/
│   ├── dataset/
│   │   └── bisoprolol.yaml         # Dataset mapping & age buckets
│   └── pader.yaml                  # Report definition & required evidence keys
├── data/
│   ├── raw/
│   │   └── Bisoprolol_icsr_sample_1068rows.xlsx
│   └── processed/
│       ├── canonical_cases.csv
│       └── exploded_reactions.csv
├── output/
│   ├── analysis_results.json       # Deterministic analysis outputs
│   └── evidence_packets.json       # Section-scoped isolated evidence packets
├── src/
│   └── genar/
│       ├── cli.py                  # CLI with `build-packets` command
│       ├── config.py
│       ├── models/
│       │   ├── evidence.py         # EvidenceItem, EvidenceProvenance, EvidencePacket
│       │   └── ...
│       ├── ingest/
│       ├── analyses/
│       └── evidence/
│           ├── __init__.py         # Evidence module exports
│           ├── store.py            # EvidenceStore indexing & provenance extraction
│           └── packet_builder.py   # Context-isolated section packet builder
├── tasks/
│   ├── phase1.md
│   ├── phase2.md
│   ├── phase3.md
│   ├── phase4.md
│   └── phase5.md                   # Phase 5 documentation & test guide
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_config.py
    ├── test_ingest.py
    ├── test_canonicalizer.py
    ├── test_analyses.py
    └── test_evidence.py            # EvidenceStore, provenance, and packet isolation tests
```

---

## 3. Section-Scoped Evidence Packet Isolation

Each section receives an isolated `EvidencePacket` containing only its declared facts:

| Section ID | Section Title | Declared Evidence Items | Structured Table Representation | Non-Invention Rules |
| :--- | :--- | :--- | :--- | :--- |
| `executive_summary` | 1. Executive Summary & Overview | `total_case_volume`, `reporting_period`, `serious_case_count`, `non_serious_case_count`, `fifteen_day_alert_count` | *N/A (Template metrics: total 1024, serious 1023, deaths 68)* | Template mode |
| `fifteen_day_alerts` | 2. 15-Day Alert Reports | `fifteen_day_alerts_breakdown` | Top reactions in alert cases (10 rows) | 2 rules (no unverified causality) |
| `serious_cases_breakdown` | 3. Analysis of Serious Adverse Events | `seriousness_criteria_counts` | Seriousness criteria table (6 rows: Hospitalization, Life-threatening, Death, Disabling, Congenital, Other) | 2 rules (no invented criteria) |
| `demographics` | 4. Demographic Distribution | `demographics_summary` | Sex, Age Buckets, Age Stats, and Top Countries (18 rows) | Table mode |
| `reactions_and_outcomes` | 5. Adverse Reactions and Outcomes | `top_adverse_reactions`, `reaction_outcomes_summary` | Reaction-outcome matrix table (10 rows) | Table & LLM mode |
| `trend_analysis` | 6. Interval Trend Analysis | `interval_trends` | Monthly time series table with Z-scores (13 months) | 2 rules (statistically flagged anomalies only) |
| `narrative_summary` | 7. Narrative Summary & Clinical Evaluation | `total_case_volume`, `reporting_period`, `serious_case_count`, `fifteen_day_alert_count`, `top_adverse_reactions`, `reaction_outcomes_summary` | Synthesis packet | 3 rules (strictly neutral regulatory phrasing) |
| `regulatory_actions` | 8. Actions Taken for Safety Reasons | *N/A (Standard negative finding template)* | *N/A* | Template mode |

---

## 4. Evidence Traceability Chain

Every claim in an `EvidencePacket` traces directly back to source data:

$$\text{EvidenceItem} \xrightarrow{\text{provenance}} \text{AnalysisResult} \xrightarrow{\text{contributing\_case\_ids}} \text{CanonicalCase} \xrightarrow{\text{source\_row\_indices}} \text{Raw ICSR Row}$$

Example from `executive_summary` packet:
- **Evidence ID**: `ev_total_case_volume`
- **Value**: `1,024`
- **Analysis ID**: `total_case_volume`
- **Method**: `genar.analyses.volume.compute_volume_summary`
- **Contributing Cases Count**: `1,024`
- **Sample Case IDs**: `['24780403', '24780599', '24780680', '24784771', '24784845']`

---

## 5. Phase 5 Checklist & Definition of Done

- [x] `src/genar/evidence/store.py` implemented with CRUD operations, provenance stamping, and JSON persistence.
- [x] `src/genar/evidence/packet_builder.py` implemented to construct isolated `EvidencePacket` instances strictly mapped to `configs/pader.yaml`.
- [x] Packet isolation verified: no unrequested evidence (e.g., trend anomalies in demographics, demographic tables in executive summary) enters any packet.
- [x] CLI `build-packets` command added with Rich summary table and optional JSON export.
- [x] Comprehensive test suite in `tests/test_evidence.py` verifying packet coverage and provenance fidelity.
- [x] All 47 test cases passing cleanly across the repository.

---

## 6. How to Run and Test Phase 5

### 1. Run Complete Test Suite
```powershell
python -m pytest -v
```

**Expected Output**:
```
tests/test_analyses.py::test_registry_registration_and_discovery PASSED  [  2%]
tests/test_analyses.py::test_volume_analysis_exact_values PASSED         [  4%]
tests/test_analyses.py::test_seriousness_analysis_exact_values PASSED    [  6%]
tests/test_analyses.py::test_demographics_analysis_exact_values PASSED   [  8%]
tests/test_analyses.py::test_reactions_analysis_exact_values PASSED      [ 10%]
tests/test_analyses.py::test_outcomes_analysis_exact_values PASSED       [ 12%]
tests/test_analyses.py::test_15_day_alerts_analysis_exact_values PASSED  [ 14%]
tests/test_analyses.py::test_interval_trends_analysis_exact_values PASSED [ 17%]
tests/test_analyses.py::test_run_all_analyses PASSED                     [ 19%]
tests/test_analyses.py::test_cli_run_analysis_command PASSED             [ 21%]
tests/test_canonicalizer.py::test_resolve_age_group PASSED               [ 23%]
tests/test_canonicalizer.py::test_build_canonical_cases_synthetic PASSED [ 25%]
tests/test_canonicalizer.py::test_build_exploded_reactions_synthetic PASSED [ 27%]
tests/test_canonicalizer.py::test_canonicalization_real_dataset PASSED   [ 29%]
tests/test_canonicalizer.py::test_persist_processed_artifacts PASSED     [ 31%]
tests/test_canonicalizer.py::test_cli_canonicalize_command PASSED        [ 34%]
tests/test_cli.py::test_cli_help PASSED                                  [ 36%]
tests/test_cli.py::test_cli_validate_config PASSED                       [ 38%]
tests/test_cli.py::test_cli_inspect_data PASSED                          [ 40%]
tests/test_config.py::test_load_pader_report_config PASSED               [ 42%]
tests/test_config.py::test_load_bisoprolol_dataset_config PASSED         [ 44%]
tests/test_config.py::test_missing_config_raises_error PASSED            [ 46%]
tests/test_config.py::test_invalid_report_config PASSED                  [ 48%]
tests/test_evidence.py::test_evidence_store_crud_and_persistence PASSED  [ 51%]
tests/test_evidence.py::test_evidence_provenance_generation PASSED       [ 53%]
tests/test_evidence.py::test_build_evidence_packet_executive_summary PASSED [ 55%]
tests/test_evidence.py::test_build_evidence_packet_demographics PASSED   [ 57%]
tests/test_evidence.py::test_build_evidence_packet_reactions_and_outcomes PASSED [ 59%]
tests/test_evidence.py::test_build_evidence_packet_trend_analysis PASSED [ 61%]
tests/test_evidence.py::test_build_all_packets_coverage PASSED           [ 63%]
tests/test_evidence.py::test_cli_build_packets_command PASSED            [ 65%]
tests/test_ingest.py::test_load_real_bisoprolol_dataset PASSED           [ 68%]
tests/test_ingest.py::test_calculate_file_checksum PASSED                [ 70%]
tests/test_ingest.py::test_create_dataset_metadata PASSED                [ 72%]
tests/test_ingest.py::test_to_raw_case_records PASSED                    [ 74%]
tests/test_ingest.py::test_parse_date_value PASSED                       [ 76%]
tests/test_ingest.py::test_validate_schema_missing_column PASSED         [ 78%]
tests/test_ingest.py::test_validate_case_ids_duplicates PASSED           [ 80%]
tests/test_ingest.py::test_validate_reaction_alignment_mismatch PASSED   [ 82%]
tests/test_ingest.py::test_validate_dataset_full_real_sample PASSED      [ 85%]
tests/test_ingest.py::test_format_dq_summary_markdown PASSED             [ 87%]
tests/test_ingest.py::test_cli_validate_data_command PASSED              [ 89%]
tests/test_models.py::test_canonical_case_model PASSED                   [ 91%]
tests/test_models.py::test_dq_issue_and_report_models PASSED             [ 93%]
tests/test_models.py::test_analysis_result_provenance PASSED             [ 95%]
tests/test_models.py::test_evidence_packet_structure PASSED              [ 97%]
tests/test_models.py::test_report_document_and_review_models PASSED      [100%]

============================= 47 passed in 23.09s =============================
```

### 2. Assemble Section Evidence Packets via CLI
```powershell
python -m genar build-packets
```

**Terminal Output**:
```
+-----------------------------------------------------------------------------+
| GenAR Evidence Packet Builder (v0.1.0)                                      |
+-----------------------------------------------------------------------------+
[OK] Loaded report: Periodic Adverse Drug Experience Report (PADER) & dataset: Bisoprolol
Building isolated evidence packets for 8 sections...
                      Assembled Section Evidence Packets                       
+-----------------------------------------------------------------------------+
| Section ID              | Section Title       | Evidence Items | Table Rows | Non-Invention Rules |
|-------------------------+---------------------+----------------+------------+---------------------|
| executive_summary       | 1. Executive Summary| 5              | -          | -                   |
| fifteen_day_alerts      | 2. 15-Day Alerts    | 1              | 10         | 2                   |
| serious_cases_breakdown | 3. Serious Events   | 1              | 6          | 2                   |
| demographics            | 4. Demographics     | 1              | 18         | -                   |
| reactions_and_outcomes  | 5. Reactions/Outcomes| 2             | 10         | -                   |
| trend_analysis          | 6. Interval Trends  | 1              | 13         | 2                   |
| narrative_summary       | 7. Narrative Summary| 6              | -          | 3                   |
| regulatory_actions      | 8. Safety Actions   | 0              | -          | -                   |
+-----------------------------------------------------------------------------+
```

### 3. Export Evidence Packets to JSON
```powershell
python -m genar build-packets -o output/evidence_packets.json
```

---

## 7. Next Steps: Phase 6 & Phase 7 Scope (Report Configuration & Section Generation)
With evidence packets assembled and context isolation guaranteed, the project proceeds to:
- **Phase 6 (Report Configuration)**: Formalizing multi-mode section rendering dispatching (`template`, `table`, `llm`, `table_and_llm`).
- **Phase 7 (Section Generation)**:
  - Implement deterministic template renderers (Executive Summary, Safety Actions).
  - Implement Markdown table formatters (Demographics, Serious Criteria, Reactions & Outcomes).
  - Implement LLM generation client with section prompt engineering and strict non-invention constraints.
