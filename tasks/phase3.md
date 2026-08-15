# Phase 3: Canonicalization (Case-Level and Reaction-Level Views)

## 1. Overview & Objective
Phase 3 implements the **Canonicalization Engine** for the **GenAR** system.

In raw safety reporting datasets, single CSV/XLSX rows cannot be naively assumed to represent single cases or single reactions due to multi-version updates and comma-delimited reaction lists. Phase 3 resolves these ambiguities deterministically, creating two trusted, reproducible analytical views:
1. **Case-Level View (`canonical_cases.csv`)**: One record per unique safety report ID (1,024 cases), applying the configured deduplication policy (`LATEST_VERSION`), standardizing dates, evaluating case-level seriousness criteria, and assigning configured age buckets.
2. **Exploded Reaction-Level View (`exploded_reactions.csv`)**: One record per reaction occurrence (3,429 reactions), preserving positional outcome alignment while explicitly flagging length mismatches.

All primary goals for Phase 3 have been completed and verified with **29/29 passing unit and regression tests**.

---

## 2. Directory Layout & Implemented Files

```
pvn-vikrant-genar-challenge/
├── configs/
│   ├── dataset/
│   │   └── bisoprolol.yaml         # Age buckets, column mappings, deduplication rules
│   └── pader.yaml                  # PADER report configuration
├── data/
│   ├── raw/
│   │   └── Bisoprolol_icsr_sample_1068rows.xlsx  # 1,068 raw rows
│   └── processed/
│       ├── canonical_cases.csv     # 1,024 canonical case records
│       └── exploded_reactions.csv  # 3,429 exploded reaction records
├── output/
│   └── data_quality_report.md      # Reviewer-facing DQ audit report
├── src/
│   └── genar/
│       ├── cli.py                  # CLI with `canonicalize` command
│       ├── config.py               # Config models & loaders
│       ├── models/                 # Domain & Pydantic models
│       │   ├── dataset.py          # CanonicalCase, ReactionRecord, DatasetMetadata
│       │   └── ...
│       └── ingest/
│           ├── __init__.py         # Ingestion & Canonicalization exports
│           ├── loader.py           # Raw data loader & SHA-256 checksum calculator
│           ├── validator.py        # Schema, duplicate case, date & reaction validators
│           ├── quality.py          # Data quality report aggregator
│           └── canonicalizer.py    # Deduplication, case & reaction builders, artifact persister
├── tasks/
│   ├── phase1.md                   # Phase 1 scaffold summary
│   ├── phase2.md                   # Phase 2 ingestion & validation summary
│   └── phase3.md                   # Phase 3 canonicalization summary & test guide
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_config.py
    ├── test_ingest.py
    ├── test_models.py
    └── test_canonicalizer.py       # Canonicalization & exact-value regression tests
```

---

## 3. Canonicalization Architecture & Separation of Semantics

### A. Case-Level Semantics (`build_canonical_cases`)
- **Deduplication Policy**: Groups by `safetyreportid`, sorts by `safetyreportversion` ascending, and retains the latest version.
- **Traceability**: Records `source_row_indices`, `version_count`, and sets `has_dq_warnings = True` for updated records.
- **Case-Level Seriousness**: Evaluates overall seriousness and individual criteria (`death`, `life_threatening`, `hospitalization`, `disabling`, `congenital_anomaly`, `other_medically_important`).
- **Demographics & Bucketing**: Resolves patient age against configured ranges (`Pediatric (<18)`, `Adult (18-64)`, `Elderly (65+)`, `UNKNOWN`) and standardizes sex (`FEMALE`, `MALE`, `UNKNOWN`).

### B. Reaction-Level Semantics (`build_exploded_reactions`)
- **Explosion**: Splits comma-separated `reactions_pt` lists into individual records.
- **Positional Alignment**: Pairs each reaction with its corresponding positional outcome in `reactions_outcome`.
- **Mismatch Protection**: If PT count ≠ Outcome count (e.g. embedded commas in terms like *"Hallucination, visual"*), sets `is_positionally_aligned = False` and assigns `"UNKNOWN"` for unaligned outcomes to prevent false attribution.
- **Context Inheritance**: Inherits canonical case seriousness, received date, sex, age group, and country.

---

## 4. Exact Deterministic Ground Truth (`Bisoprolol_icsr_sample_1068rows.xlsx`)

Executing the canonicalization pipeline against the real dataset yields the following exact deterministic metrics:

| Category | Metric | Value |
| :--- | :--- | :--- |
| **Volumes** | Total Raw Rows | `1,068` |
| | Unique Canonical Cases | `1,024` |
| | Multi-Version Duplicate Instances | `41` (44 excess rows) |
| | Total Exploded Reactions | `3,429` |
| | - Positionally Aligned Reactions | `3,371` |
| | - Unaligned Reactions (Flagged) | `58` |
| **Seriousness** | Serious Cases | `1,023` (99.9%) |
| | Non-Serious Cases | `1` (0.1%) |
| | 15-Day Alert Cases | `1,023` |
| | Death Criteria Met | `68` |
| | Life-Threatening Criteria Met | `105` |
| | Hospitalization Criteria Met | `482` |
| | Disabling Criteria Met | `44` |
| | Congenital Anomaly Criteria Met | `7` |
| | Other Medically Important Criteria Met | `905` |
| **Demographics** | Female Cases | `503` (49.12%) |
| | Male Cases | `493` (48.14%) |
| | Unknown Sex Cases | `28` (2.73%) |
| | Pediatric (<18) Cases | `16` (1.56%) |
| | Adult (18-64) Cases | `249` (24.32%) |
| | Elderly (65+) Cases | `676` (66.02%) |
| | Unknown Age Cases | `83` (8.11%) |

---

## 5. Phase 3 Checklist & Definition of Done

- [x] `src/genar/ingest/canonicalizer.py` implemented with deduplication, case-view builder, and reaction-view builder.
- [x] Positional list alignment validated and protected against invalid token splits.
- [x] Processed artifacts (`canonical_cases.csv`, `exploded_reactions.csv`) automatically persisted to `data/processed/`.
- [x] `canonicalize` command added to `src/genar/cli.py` with Rich table summaries.
- [x] Comprehensive test suite in `tests/test_canonicalizer.py` asserting exact expected values on real fixtures.
- [x] All 29 test cases passing cleanly with zero warnings.

---

## 6. How to Run and Test Phase 3

### 1. Run Complete Test Suite
```powershell
python -m pytest -v
```

**Expected Output**:
```
tests/test_canonicalizer.py::test_resolve_age_group PASSED               [  3%]
tests/test_canonicalizer.py::test_build_canonical_cases_synthetic PASSED [  6%]
tests/test_canonicalizer.py::test_build_exploded_reactions_synthetic PASSED [ 10%]
tests/test_canonicalizer.py::test_canonicalization_real_dataset PASSED   [ 13%]
tests/test_canonicalizer.py::test_persist_processed_artifacts PASSED     [ 17%]
tests/test_canonicalizer.py::test_cli_canonicalize_command PASSED        [ 20%]
tests/test_cli.py::test_cli_help PASSED                                  [ 24%]
tests/test_cli.py::test_cli_validate_config PASSED                       [ 27%]
tests/test_cli.py::test_cli_inspect_data PASSED                          [ 31%]
tests/test_config.py::test_load_pader_report_config PASSED               [ 34%]
tests/test_config.py::test_load_bisoprolol_dataset_config PASSED         [ 37%]
tests/test_config.py::test_missing_config_raises_error PASSED            [ 41%]
tests/test_config.py::test_invalid_report_config PASSED                  [ 44%]
tests/test_ingest.py::test_load_real_bisoprolol_dataset PASSED           [ 48%]
tests/test_ingest.py::test_calculate_file_checksum PASSED                [ 51%]
tests/test_ingest.py::test_create_dataset_metadata PASSED                [ 55%]
tests/test_ingest.py::test_to_raw_case_records PASSED                    [ 58%]
tests/test_ingest.py::test_parse_date_value PASSED                       [ 62%]
tests/test_ingest.py::test_validate_schema_missing_column PASSED         [ 65%]
tests/test_ingest.py::test_validate_case_ids_duplicates PASSED           [ 68%]
tests/test_ingest.py::test_validate_reaction_alignment_mismatch PASSED   [ 72%]
tests/test_ingest.py::test_validate_dataset_full_real_sample PASSED      [ 75%]
tests/test_ingest.py::test_format_dq_summary_markdown PASSED             [ 79%]
tests/test_ingest.py::test_cli_validate_data_command PASSED              [ 82%]
tests/test_models.py::test_canonical_case_model PASSED                   [ 86%]
tests/test_models.py::test_dq_issue_and_report_models PASSED             [ 89%]
tests/test_models.py::test_analysis_result_provenance PASSED             [ 93%]
tests/test_models.py::test_evidence_packet_structure PASSED              [ 96%]
tests/test_models.py::test_report_document_and_review_models PASSED      [100%]

============================= 29 passed in 13.01s =============================
```

### 2. Execute Canonicalization via CLI
```powershell
python -m genar canonicalize
```

**Terminal Output**:
```
+-----------------------------------------------------------------------------+
| GenAR Dataset Canonicalizer (v0.1.0)                                        |
+-----------------------------------------------------------------------------+
[OK] Loaded dataset config for Bisoprolol
Loading raw dataset from data\raw\Bisoprolol_icsr_sample_1068rows.xlsx...
Executing canonicalization (deduplication + reaction explosion)...
                           Canonicalization Summary                            
+-----------------------------------------------------------------------------+
| Analytical View                  | Count | Artifact File Path               |
|----------------------------------+-------+----------------------------------|
| Canonical Cases (1 per case ID)  | 1,024 | data\processed\canonical_cases.csv|
| Exploded Reactions (1 per event) | 3,429 | data\processed\exploded_reactions.csv|
|   - Positionally Aligned         | 3,371 | -                                |
|   - Unaligned Reactions (Flagged)| 58    | -                                |
+-----------------------------------------------------------------------------+
Canonicalization complete and artifacts successfully persisted!
```

---

## 7. Next Steps: Phase 4 Scope (Deterministic Analysis Registry)
With canonical case and reaction datasets established, the project moves to **Phase 4 (Deterministic Analysis Registry)**:
- Implement `src/genar/analyses/registry.py` to register and invoke analytical calculators by name.
- Implement pure calculation modules:
  - `analyses/volume.py`: Case totals and reporting periods.
  - `analyses/seriousness.py`: Serious/non-serious splits and criteria breakdown.
  - `analyses/demographics.py`: Sex, age bucket, and country distributions.
  - `analyses/reactions.py`: Frequency ranking of top adverse reactions.
  - `analyses/outcomes.py`: Reaction-outcome cross-tabulations.
  - `analyses/alerts.py`: 15-day expedited alert metrics.
  - `analyses/trends.py`: Monthly time-series aggregations and statistical candidate-trend detection.
