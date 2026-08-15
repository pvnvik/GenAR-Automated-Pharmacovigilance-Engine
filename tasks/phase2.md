# Phase 2: Ingestion, Validation & Data Quality Reporting

## 1. Overview & Objective
Phase 2 implements the ingestion and deterministic data validation layer for the **GenAR** system. 

All primary goals for Phase 2 have been completed and verified:
- **Raw Data Ingestion (`loader.py`)**: Robust loader supporting `.xlsx`, `.xls`, `.csv`, `.tsv` without destructive schema transformations; computes SHA-256 dataset checksum for provenance tracking.
- **Deterministic Validation Suite (`validator.py`)**:
  - Schema/required field presence checks based on configurable column mappings.
  - Case identifier duplicate and version-update detection.
  - Date format parsing and verification (`102` / `YYYYMMDD`, ISO format).
  - Reaction and outcome positional list alignment validation (identifying embedded commas in MedDRA terms).
  - Demographic integrity checks (biologically plausible age bounds 0–130, sex validation).
- **Data Quality Aggregation & Reporting (`quality.py`)**:
  - Structured `DataQualityReport` model aggregating issues by category and severity (`CRITICAL`, `WARNING`, `INFO`).
  - Formatted reviewer-facing Markdown generation for audit trails and report inclusion.
- **CLI Commands**: Added `validate-data` to ingest datasets, execute validation, render Rich terminal summary tables, and export Markdown reports.
- **Test Suite**: 11 new unit and regression tests in `tests/test_ingest.py`, bringing the total test suite to **23 passing tests**.

---

## 2. Directory Layout & Implemented Files

```
pvn-vikrant-genar-challenge/
├── configs/
│   ├── dataset/
│   │   └── bisoprolol.yaml         # Column mappings, rules, age buckets
│   └── pader.yaml                  # Report definition
├── data/
│   ├── raw/
│   │   └── Bisoprolol_icsr_sample_1068rows.xlsx  # 1,068 rows, 1,024 unique case reports
│   └── processed/
├── output/
│   └── data_quality_report.md      # Reviewer-facing DQ audit report
├── src/
│   └── genar/
│       ├── cli.py                  # CLI with validate-data command
│       ├── config.py               # Config models & loaders
│       ├── models/                 # Domain & DQ models
│       │   ├── dataset.py
│       │   ├── quality.py
│       │   └── ...
│       └── ingest/
│           ├── __init__.py         # Ingestion module exports
│           ├── loader.py           # Raw data ingestion, checksum, RawCaseRecord builder
│           ├── validator.py        # Schema, duplicate case, date, list alignment validators
│           └── quality.py          # DQ aggregator & reviewer markdown renderer
├── tasks/
│   ├── phase1.md                   # Phase 1 documentation
│   └── phase2.md                   # Phase 2 documentation & test instructions
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_config.py
    ├── test_models.py
    └── test_ingest.py              # Ingestion, validation & DQ regression tests
```

---

## 3. Real Dataset Findings (`Bisoprolol_icsr_sample_1068rows.xlsx`)

Executing the deterministic validation pipeline on the sample dataset revealed key structural characteristics:

| Metric | Result | Explanation |
| :--- | :--- | :--- |
| **Total Raw Rows** | `1,068` | Full raw records ingested. |
| **Unique Safety Report IDs** | `1,024` | Distinct case report identifiers. |
| **Duplicate/Updated Case Instances** | `41` (44 excess rows) | 38 cases appear twice (v1, v2), 3 cases appear three times (v1, v3, v4). |
| **List Alignment Mismatches** | `6` | Cases with comma-separated reaction count ≠ outcome count due to embedded commas in terms (e.g. *"Hallucination, visual"*, *"Hallucinations, mixed"*). |
| **Critical Issues** | `0` | All mandatory columns and primary keys are present. |
| **Warning Issues** | `47` | 41 updated case warnings + 6 list length mismatch warnings surfaced to reviewer. |

---

## 4. Phase 2 Checklist & Definition of Done

- [x] `src/genar/ingest/loader.py` implemented for `.xlsx` and `.csv` with SHA-256 checksum calculation.
- [x] `src/genar/ingest/validator.py` implemented covering schema, duplicate IDs, dates, reactions, and demographics.
- [x] `src/genar/ingest/quality.py` implemented for building `DataQualityReport` and generating Markdown summaries.
- [x] `validate-data` command added to `src/genar/cli.py` with Rich table formatting and `--output-report` flag.
- [x] Comprehensive test suite in `tests/test_ingest.py` passing with 100% success rate.
- [x] Non-negotiable architectural rule respected: zero ambiguous data quality issues were silently modified or dropped; all findings are structured, retained, and surfaced.

---

## 5. How to Run and Test Phase 2

### 1. Run Complete Test Suite
Run the 23 unit and regression tests:
```powershell
python -m pytest -v
```

**Expected Output**:
```
tests/test_cli.py::test_cli_help PASSED                                  [  4%]
tests/test_cli.py::test_cli_validate_config PASSED                       [  8%]
tests/test_cli.py::test_cli_inspect_data PASSED                          [ 13%]
tests/test_config.py::test_load_pader_report_config PASSED               [ 17%]
tests/test_config.py::test_load_bisoprolol_dataset_config PASSED         [ 21%]
tests/test_config.py::test_missing_config_raises_error PASSED            [ 26%]
tests/test_config.py::test_invalid_report_config PASSED                  [ 30%]
tests/test_ingest.py::test_load_real_bisoprolol_dataset PASSED           [ 34%]
tests/test_ingest.py::test_calculate_file_checksum PASSED                [ 39%]
tests/test_ingest.py::test_create_dataset_metadata PASSED                [ 43%]
tests/test_ingest.py::test_to_raw_case_records PASSED                    [ 47%]
tests/test_ingest.py::test_parse_date_value PASSED                       [ 52%]
tests/test_ingest.py::test_validate_schema_missing_column PASSED         [ 56%]
tests/test_ingest.py::test_validate_case_ids_duplicates PASSED           [ 60%]
tests/test_ingest.py::test_validate_reaction_alignment_mismatch PASSED   [ 65%]
tests/test_ingest.py::test_validate_dataset_full_real_sample PASSED      [ 69%]
tests/test_ingest.py::test_format_dq_summary_markdown PASSED             [ 73%]
tests/test_ingest.py::test_cli_validate_data_command PASSED              [ 78%]
tests/test_models.py::test_canonical_case_model PASSED                   [ 82%]
tests/test_models.py::test_dq_issue_and_report_models PASSED             [ 86%]
tests/test_models.py::test_analysis_result_provenance PASSED             [ 91%]
tests/test_models.py::test_evidence_packet_structure PASSED              [ 95%]
tests/test_models.py::test_report_document_and_review_models PASSED      [100%]

============================= 23 passed in 7.11s ==============================
```

### 2. Run Data Ingestion & Quality Validation via CLI
Run dataset validation on the default configured dataset (`Bisoprolol`):
```powershell
python -m genar validate-data
```

**Terminal Output**:
```
+-----------------------------------------------------------------------------+
| GenAR Data Ingestion & Quality Validator (v0.1.0)                           |
+-----------------------------------------------------------------------------+
[OK] Loaded config for Bisoprolol
Ingesting raw dataset from data\raw\Bisoprolol_icsr_sample_1068rows.xlsx...
[OK] Ingested 1,068 rows (1,024 unique case IDs)
Executing deterministic validation suite...
      Data Quality Assessment Summary       
+------------------------------------------+
| Metric                           | Value |
|----------------------------------+-------|
| Total Raw Rows                   | 1,068 |
| Unique Case IDs                  | 1,024 |
| Duplicate/Updated Instances      | 41    |
| Reaction/Outcome List Mismatches | 6     |
| Critical Findings                | 0     |
| Warning Findings                 | 47    |
| Info Findings                    | 0     |
+------------------------------------------+
      Findings by Category      
+------------------------------+
| Issue Type           | Count |
|----------------------+-------|
| UPDATED_CASE_ROW     | 41    |
| LIST_LENGTH_MISMATCH | 6     |
+------------------------------+
```

### 3. Generate and Export DQ Markdown Report
```powershell
python -m genar validate-data -o output/data_quality_report.md
```

---

## 6. Next Steps: Phase 3 Scope (Canonicalization)
With Phase 2 complete, the system is ready for **Phase 3 (Canonicalization)**:
- Implement `src/genar/ingest/canonicalizer.py`:
  - Deduplicate multi-version rows according to configured policy (`LATEST_VERSION`).
  - Build trusted **Case-Level Table** (1 row per canonical case with standardized date, seriousness flags, demographics).
  - Build exploded **Reaction-Level Table** (1 row per reaction with positionally resolved outcomes).
  - Persist processed parquet/CSV artifacts to `data/processed/`.
