# Phase 1: Project Scaffold, Domain Models, Configuration & CLI Skeleton

## 1. Overview & Objective
Phase 1 establishes the deterministic foundational engineering structure for the **GenAR** (Generative Adverse Event Reporting) system. 

All primary goals for Phase 1 have been implemented and verified:
- Clean, importable Python package structure (`genar`).
- Typed domain models and schemas using **Pydantic v2** (`src/genar/models/`).
- Declarative configuration loaders and Pydantic validation schemas for report configurations (`pader.yaml`) and dataset parameters (`bisoprolol.yaml`).
- Minimal Click + Rich CLI skeleton with documented commands (`--help`, `validate-config`, `inspect-data`, `run-pipeline`).
- Complete test suite verifying configuration loading, model serialization, and CLI operations with 100% pass rate (12/12 tests).
- Zero LLM or external agent dependencies required to run the core scaffold.

---

## 2. Directory Layout & Created Files

```
pvn-vikrant-genar-challenge/
├── pyproject.toml                  # Package setup, CLI scripts, and pytest configuration
├── requirements.txt                # Core dependencies (pydantic, pyyaml, pandas, openpyxl, click, rich, pytest)
├── configs/
│   ├── dataset/
│   │   └── bisoprolol.yaml         # Bisoprolol dataset config, column mappings, age buckets, deduplication rules
│   └── pader.yaml                  # 8-section PADER report specification and evidence mapping
├── data/
│   ├── raw/
│   │   └── Bisoprolol_icsr_sample_1068rows.xlsx  # 1,068 raw rows, 1,024 unique safety report cases
│   └── processed/                  # Target output directory for canonicalized case & reaction views
├── output/                         # Target directory for generated reports, review packets, audit trails
├── prompts/
│   └── system_prompts.txt          # Regulatory writing system prompt templates
├── src/
│   └── genar/
│       ├── __init__.py             # Package init & version stamp (0.1.0)
│       ├── __main__.py             # Direct execution entrypoint (python -m genar)
│       ├── cli.py                  # Click + Rich CLI interface implementation
│       ├── config.py               # YAML configuration loader & Pydantic validation models
│       ├── models/                 # Domain & Pydantic Data Models
│       │   ├── __init__.py         # Clean export of all domain models
│       │   ├── dataset.py          # RawCaseRecord, CanonicalCase, ReactionRecord, DatasetMetadata
│       │   ├── quality.py          # DQIssue, DQSeverity, DQIssueType, DQActionTaken, DataQualityReport
│       │   ├── analysis.py         # AnalysisResult, AnalysisCategory with full provenance tracking
│       │   ├── evidence.py         # EvidenceItem, EvidenceProvenance, EvidencePacket
│       │   ├── section.py          # SectionDraft, GenerationMode
│       │   ├── review.py           # ReviewRecord, ReviewStatus, ReviewFlag
│       │   └── report.py           # ReportMetadata, ReportDocument
│       ├── ingest/                 # (Phase 2-3) Raw data loaders, validators, canonicalizer
│       ├── analyses/               # (Phase 4) Deterministic analysis registry & calculators
│       ├── evidence/               # (Phase 5) Evidence store & packet builder
│       ├── generation/             # (Phase 6-7) Template, table, and LLM section generators
│       ├── verification/           # (Phase 8) Post-generation numeric & grounding checks
│       ├── review/                 # (Phase 9) Review state persistence & gatekeeping
│       ├── assembly/               # (Phase 10) Canonical markdown & document renderers
│       └── orchestration/          # (Phase 10/12) Deterministic execution workflow
├── tasks/
│   └── phase1.md                   # Phase 1 summary, test instructions, and verification
└── tests/
    ├── __init__.py                 # Test package init
    ├── conftest.py                 # Pytest fixtures and sys.path setup
    ├── test_config.py              # Configuration loading and schema validation tests
    ├── test_models.py              # Domain model validation and serialization tests
    └── test_cli.py                 # CLI execution and command output tests
```

---

## 3. Implemented Modules & Domain Models

### A. Configuration Models (`src/genar/config.py`)
- **`ReportConfig` & `SectionConfig`**: Validates report structure, section ordering, generation modes (`template`, `table`, `llm`, `table_and_llm`), required evidence keys, and non-invention rules.
- **`DatasetConfig`, `ColumnMappingConfig`, `AgeBucketConfig`, `DatasetRulesConfig`**: Maps dataset-specific columns, age ranges, and deduplication policies without hardcoding dataset assumptions.
- **Loaders**: `load_report_config(path)` and `load_dataset_config(path)` with automated schema validation.

### B. Core Domain Models (`src/genar/models/`)
- **`dataset.py`**:
  - `RawCaseRecord`: Raw ingested row structure.
  - `CanonicalCase`: Canonical case-level view (1 record per unique safety report ID).
  - `ReactionRecord`: Exploded reaction-level record (1 record per reaction occurrence, positionally aligned).
  - `DatasetMetadata`: Summary metadata, checksum, row/case counts.
- **`quality.py`**:
  - `DQIssue`: Discrete data-quality findings with severity levels (`INFO`, `WARNING`, `CRITICAL`) and resolution action (`FLAGGED`, `DEDUPLICATED_LATEST`, `POSITIONALLY_REJECTED`, `KEPT_AS_IS`).
  - `DataQualityReport`: Reviewer-facing audit report of all data quality issues.
- **`analysis.py`**:
  - `AnalysisResult`: Encapsulates exact deterministic computations with `analysis_id`, `version`, `category`, `parameters`, `metrics`, `contributing_case_ids`, and method metadata.
- **`evidence.py`**:
  - `EvidenceItem` & `EvidenceProvenance`: Verifiable claims with full provenance linking back to analysis ID, timestamp, and case counts.
  - `EvidencePacket`: Section-scoped bundle of approved facts passed to section generators.
- **`section.py`**:
  - `SectionDraft`: Generated section content with grounding status, order, and metadata.
- **`review.py`**:
  - `ReviewRecord`: Human reviewer gatekeeping with statuses (`DRAFT`, `QA_CHECKED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `FINAL`).
- **`report.py`**:
  - `ReportMetadata` & `ReportDocument`: Canonical container assembling approved sections and complete audit trail.

### C. CLI Skeleton (`src/genar/cli.py`)
- `genar --help`: Displays CLI description and command list.
- `genar validate-config`: Validates YAML configuration files against Pydantic models.
- `genar inspect-data`: Displays formatted dataset summary, file status, and configured age buckets.
- `genar run-pipeline`: Entrypoint for deterministic pipeline execution.

---

## 4. Phase 1 Checklist & Definition of Done

- [x] Package structure created and `genar` installed in editable mode.
- [x] `requirements.txt` and `pyproject.toml` configured.
- [x] Configuration schemas defined and validated against `configs/pader.yaml` and `configs/dataset/bisoprolol.yaml`.
- [x] Pydantic models for `Dataset`, `AnalysisResult`, `EvidencePacket`, `SectionDraft`, `ReviewRecord`, and `ReportMetadata` implemented.
- [x] CLI entry point created with documented `--help` output and rich terminal formatting.
- [x] Unit test suite implemented covering models, configurations, and CLI commands.
- [x] All 12 unit tests passing cleanly with zero warnings (`python -m pytest -v`).
- [x] Zero LLM or LangGraph dependencies required for Module 1 execution.

---

## 5. How to Run and Test Phase 1

### 1. Run Unit Test Suite
Execute the entire test suite via `pytest`:
```powershell
python -m pytest -v
```

**Expected Output**:
```
tests/test_cli.py::test_cli_help PASSED                                  [  8%]
tests/test_cli.py::test_cli_validate_config PASSED                       [ 16%]
tests/test_cli.py::test_cli_inspect_data PASSED                          [ 25%]
tests/test_config.py::test_load_pader_report_config PASSED               [ 33%]
tests/test_config.py::test_load_bisoprolol_dataset_config PASSED         [ 41%]
tests/test_config.py::test_missing_config_raises_error PASSED            [ 50%]
tests/test_config.py::test_invalid_report_config PASSED                  [ 58%]
tests/test_models.py::test_canonical_case_model PASSED                   [ 66%]
tests/test_models.py::test_dq_issue_and_report_models PASSED             [ 75%]
tests/test_models.py::test_analysis_result_provenance PASSED             [ 83%]
tests/test_models.py::test_evidence_packet_structure PASSED              [ 91%]
tests/test_models.py::test_report_document_and_review_models PASSED      [100%]

============================= 12 passed in 0.42s ==============================
```

### 2. Run CLI Help
```powershell
python -m genar --help
```

### 3. Validate Configuration Files
Validate `configs/pader.yaml` and `configs/dataset/bisoprolol.yaml`:
```powershell
python -m genar validate-config
```
**Expected Output**:
```
+-----------------------------------------------------------------------------+
| GenAR Configuration Validator (v0.1.0)                                      |
+-----------------------------------------------------------------------------+
[OK] Report Config Valid: Periodic Adverse Drug Experience Report (PADER) (8 sections defined)
[OK] Dataset Config Valid: Bisoprolol (Manufacturer: Aurobindo Pharma)
All configuration files validated successfully!
```

### 4. Inspect Dataset Metadata
Inspect raw dataset configuration and file status:
```powershell
python -m genar inspect-data
```
**Expected Output**:
```
                Dataset Configuration Overview: Bisoprolol                
+------------------------------------------------------------------------+
| Property               | Value                                         |
|------------------------+-----------------------------------------------|
| Dataset Name           | bisoprolol_sample_2024                        |
| Product Name           | Bisoprolol                                    |
| Active Substance       | Bisoprolol Fumarate                           |
| Manufacturer           | Aurobindo Pharma                              |
| Raw Data File          | data\raw\Bisoprolol_icsr_sample_1068rows.xlsx |
| File Exists            | True                                          |
| File Size (KB)         | 499.32 KB                                     |
| Reporting Period       | 2024-01-01 to 2024-12-31                      |
| Configured Age Buckets | 3                                             |
+------------------------------------------------------------------------+
```

---

## 6. Next Steps: Phase 2 Scope
With Phase 1 complete, the project is ready for **Phase 2 (Ingestion and Validation)**:
- Implement `src/genar/ingest/loader.py` to load raw CSV/XLSX into Pandas while preserving raw source values.
- Implement `src/genar/ingest/validator.py` to validate schemas, date formats, required fields, and produce structured data quality findings (`DQIssue`).
- Implement `src/genar/ingest/quality.py` to aggregate quality metrics into a reviewer-facing summary.
- Add unit tests asserting exact validation and DQ issue reporting on sample fixtures.
