# Phase 7: Multi-Mode Section Generation & LLM Dispatching

## 1. Overview & Objective
Phase 7 implements the **Section Generation Engine** for the **GenAR** system.

In compliance with the project architecture:
> **"Deterministic template and table renderers are executed first; LLM generation is utilized for narrative sections strictly bounded by approved evidence packets, regulatory system prompts, and non-invention rules."**

Phase 7 delivers:
1. `src/genar/generation/templates.py`: Deterministic string interpolation for template sections (`executive_summary`, `regulatory_actions`).
2. `src/genar/generation/tables.py`: Deterministic GitHub Flavored Markdown table formatter with column alignment, integer formatting, and percent formatting.
3. `src/genar/generation/llm.py`: Regulatory prompt builder and pluggable `LLMGenerator` featuring an offline deterministic synthesizer for 100% test reproducibility and zero hallucination.
4. `src/genar/generation/dispatcher.py`: `SectionGenerator` dispatching across all 4 modes (`template`, `table`, `llm`, `table_and_llm`).
5. CLI command `generate-drafts` assembling complete Markdown reports.

All goals for Phase 7 have been completed and verified with **55/55 passing unit and regression tests**.

---

## 2. Directory Layout & Implemented Files

```
pvn-vikrant-genar-challenge/
├── configs/
│   ├── dataset/
│   │   └── bisoprolol.yaml
│   └── pader.yaml
├── output/
│   ├── analysis_results.json
│   ├── evidence_packets.json
│   └── draft_pader_report.md       # Complete assembled 8-section draft report
├── prompts/
│   └── system_prompts.txt          # Regulatory safety writer system prompt & templates
├── src/
│   └── genar/
│       ├── cli.py                  # Added `generate-drafts` command
│       ├── models/
│       │   ├── section.py          # GenerationMode, SectionDraft, SectionFeedback
│       │   └── ...
│       └── generation/
│           ├── __init__.py         # Generation module exports
│           ├── templates.py        # Template renderer
│           ├── tables.py           # Markdown table renderer
│           ├── llm.py              # LLM prompt builder & synthesizer
│           └── dispatcher.py       # SectionGenerator multi-mode dispatcher
├── tasks/
│   ├── phase1.md
│   ├── phase2.md
│   ├── phase3.md
│   ├── phase4.md
│   ├── phase5.md
│   ├── phase6.md
│   └── phase7.md                   # Phase 7 documentation & test guide
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_config.py
    ├── test_ingest.py
    ├── test_canonicalizer.py
    ├── test_analyses.py
    ├── test_evidence.py
    └── test_generation.py          # Multi-mode section generation tests
```

---

## 3. Section Generation Summary

| Order | Section ID | Mode | Evidence Items | Key Output Features |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `executive_summary` | `template` | 5 | Deterministic summary: **1,024** canonical cases, **1,023** serious (99.9%), **1** non-serious (0.1%), **1,023** 15-day alerts, **68** fatalities. |
| 2 | `fifteen_day_alerts` | `table_and_llm` | 1 | Table of top alert reactions (Acute kidney injury 80, Drug ineffective 53, Hypotension 46) + regulatory narrative. |
| 3 | `serious_cases_breakdown` | `table_and_llm` | 1 | Criteria table (Hospitalization: 482, Death: 68, Life-threatening: 105, Disabling: 44, Congenital: 7, Other: 905) + clinical interpretation. |
| 4 | `demographics` | `table` | 1 | Full 18-row demographic distribution table (Sex, Age Buckets, Summary Stats, Top Countries). |
| 5 | `reactions_and_outcomes` | `table_and_llm` | 2 | 10-row matrix of top MedDRA PTs across outcomes (Recovered, Recovering, Not Recovered, Fatal, Unknown, Sequelae) + narrative commentary. |
| 6 | `trend_analysis` | `table_and_llm` | 1 | 13-month monthly time series table + Z-score statistical anomaly candidate note (Dec 2024 initial reporting month). |
| 7 | `narrative_summary` | `llm` | 6 | Evidence-grounded synthesis covering cumulative volume, serious proportions, top events, and negative finding confirmation. |
| 8 | `regulatory_actions` | `template` | 0 | Standard negative finding template adhering to FDA 21 CFR 314.80. |

---

## 4. Phase 7 Checklist & Definition of Done

- [x] Deterministic template renderer (`templates.py`) implemented with safe metric interpolation.
- [x] Deterministic markdown table renderer (`tables.py`) implemented with header mapping and percent formatting.
- [x] LLM prompt builder and generator (`llm.py`) implemented with strict regulatory system prompt and non-invention rules.
- [x] Offline deterministic fallback generator ensuring 100% test reproducibility without requiring live external API keys.
- [x] Dispatcher (`dispatcher.py`) routing section generation dynamically based on `section_cfg.generation_mode`.
- [x] CLI `generate-drafts` command added to produce assembled Markdown reports.
- [x] Comprehensive test suite in `tests/test_generation.py` passing with 100% success rate.
- [x] All 55 test cases passing cleanly across the repository.

---

## 5. How to Run and Test Phase 7

### 1. Run Complete Test Suite
```powershell
python -m pytest -v
```

**Expected Output**:
```
tests/test_analyses.py::test_registry_registration_and_discovery PASSED  [  1%]
...
tests/test_generation.py::test_render_template_section PASSED            [ 58%]
tests/test_generation.py::test_render_markdown_table PASSED              [ 60%]
tests/test_generation.py::test_render_table_section PASSED               [ 61%]
tests/test_generation.py::test_build_llm_prompt PASSED                   [ 63%]
tests/test_generation.py::test_llm_generator_deterministic_fallback PASSED [ 65%]
tests/test_generation.py::test_section_generator_dispatch_modes PASSED   [ 67%]
tests/test_generation.py::test_generate_all_sections_coverage PASSED     [ 69%]
tests/test_generation.py::test_cli_generate_drafts_command PASSED        [ 70%]
...
============================= 55 passed in 28.46s =============================
```

### 2. Generate Section Drafts via CLI
```powershell
python -m genar generate-drafts
```

**Terminal Output**:
```
+-----------------------------------------------------------------------------+
| GenAR Multi-Mode Section Generator (v0.1.0)                                 |
+-----------------------------------------------------------------------------+
[OK] Loaded report: Periodic Adverse Drug Experience Report (PADER) & dataset: Bisoprolol
Generating section drafts in configured order...
                           Generated Section Drafts                            
+-----------------------------------------------------------------------------+
| Order | Section Title      | Mode          | Content Length | Evidence Used |
|-------+--------------------+---------------+----------------+---------------|
| 1     | 1. Executive       | template      | 405 chars      | 5             |
| 2     | 2. 15-Day Alerts   | table_and_llm | 782 chars      | 1             |
| 3     | 3. Serious Events  | table_and_llm | 803 chars      | 1             |
| 4     | 4. Demographics    | table         | 790 chars      | 1             |
| 5     | 5. Reactions/Outc. | table_and_llm | 1,003 chars    | 2             |
| 6     | 6. Interval Trends | table_and_llm | 909 chars      | 1             |
| 7     | 7. Narrative       | llm           | 1,058 chars    | 6             |
| 8     | 8. Safety Actions  | template      | 258 chars      | 0             |
+-----------------------------------------------------------------------------+
```

### 3. Assemble Complete Draft Report to Markdown
```powershell
python -m genar generate-drafts -o output/draft_pader_report.md
```

---

## 6. Next Steps: Phase 8 & Phase 9 Scope (Review, Audit Trail & Export)
With multi-mode section generation complete, the system proceeds to:
- **Phase 8 (Review & Traceability)**: Implement Section Review Workflow, Feedback tracking, and Section-level Evidence Claim Validation.
- **Phase 9 (Assembly & Export)**: Implement Report Document Assembly, Full Provenance Audit Trail Export, and Multi-Format Document Exporter (Markdown & HTML).
