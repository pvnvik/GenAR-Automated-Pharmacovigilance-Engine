# Phase 6: Report Configuration & Multi-Mode Definition

## 1. Overview & Objective
Phase 6 implements the **Declarative Report Configuration Layer** for the **GenAR** system.

In compliance with regulatory requirements:
> **"The system must be configurable across report types (surviving PADER -> PSUR/PBRER/DSUR/CSR) and section generation modes (template, table, llm, table_and_llm) without hardcoded section names or brittle if-else chains."**

In Phase 6, report definitions in `configs/pader.yaml` are loaded into structured Pydantic models (`ReportConfig`, `SectionConfig`) specifying section order, generation mode, required evidence keys, table column headers, prompt templates, and explicit non-invention rules.

All goals for Phase 6 have been completed and verified with **55/55 passing unit and regression tests**.

---

## 2. Report Configuration Specification (`configs/pader.yaml`)

```yaml
report_type: "PADER"
title: "Periodic Adverse Drug Experience Report (PADER)"
version: "1.0"
regulatory_framework: "FDA 21 CFR 314.80"

sections:
  - id: "executive_summary"
    title: "1. Executive Summary & Overview"
    order: 1
    generation_mode: "template"
    required_evidence:
      - "total_case_volume"
      - "reporting_period"
      - "serious_case_count"
      - "non_serious_case_count"
      - "fifteen_day_alert_count"
    template: |
      ## 1. Executive Summary & Overview
      This Periodic Adverse Drug Experience Report (PADER) covers the reporting period from {reporting_period_start} to {reporting_period_end} for {product_name} ({active_substance}).
      During this interval, a total of **{total_cases}** canonical adverse event cases were evaluated.
      - **Serious Cases:** {serious_cases} ({serious_percent}%)
      - **Non-Serious Cases:** {non_serious_cases} ({non_serious_percent}%)
      - **15-Day Alert Reports:** {fifteen_day_alerts}
      - **Fatalities Reported:** {fatalities_count}

  - id: "fifteen_day_alerts"
    title: "2. 15-Day Alert Reports"
    order: 2
    generation_mode: "table_and_llm"
    required_evidence:
      - "fifteen_day_alerts_breakdown"
      - "fifteen_day_top_reactions"
    non_invention_rules:
      - "Only report cases explicitly matching 15-day alert criteria."
      - "Do not extrapolate unverified causality."

  - id: "serious_cases_breakdown"
    title: "3. Analysis of Serious Adverse Events"
    order: 3
    generation_mode: "table_and_llm"
    required_evidence:
      - "seriousness_criteria_counts"
      - "seriousness_percentage_breakdown"
    table_columns:
      - "Seriousness Criteria"
      - "Case Count"
      - "Percentage (%)"
    non_invention_rules:
      - "Sum of criteria may exceed total serious cases because individual cases may meet multiple criteria."
      - "Do not invent additional seriousness categories."

  - id: "demographics"
    title: "4. Demographic Distribution"
    order: 4
    generation_mode: "table"
    required_evidence:
      - "sex_distribution"
      - "age_group_distribution"
      - "country_distribution"
    table_columns:
      - "Demographic Category"
      - "Sub-category"
      - "Cases"
      - "Percentage (%)"

  - id: "reactions_and_outcomes"
    title: "5. Adverse Reactions and Outcomes"
    order: 5
    generation_mode: "table_and_llm"
    required_evidence:
      - "top_adverse_reactions"
      - "reaction_outcomes_summary"
      - "serious_vs_nonserious_reactions"
    table_columns:
      - "Preferred Term (PT)"
      - "Total Events"
      - "Recovered"
      - "Recovering"
      - "Not Recovered"
      - "Fatal"
      - "Unknown"
      - "Sequelae"

  - id: "trend_analysis"
    title: "6. Interval Trend Analysis"
    order: 6
    generation_mode: "table_and_llm"
    required_evidence:
      - "monthly_case_counts"
      - "flagged_trend_anomalies"
    non_invention_rules:
      - "Only discuss trends flagged as statistically notable by Python analysis."
      - "Do not claim new safety signals unless explicitly confirmed in evidence."

  - id: "narrative_summary"
    title: "7. Narrative Summary & Clinical Evaluation"
    order: 7
    generation_mode: "llm"
    required_evidence:
      - "narrative_synthesis_packet"
    prompt_template: "narrative_summary_prompt"
    non_invention_rules:
      - "Use strictly neutral regulatory phrasing."
      - "Never state that a reaction was caused by the drug; describe reported associations."
      - "Do not invent background clinical studies or unsupplied clinical histories."

  - id: "regulatory_actions"
    title: "8. Actions Taken for Safety Reasons"
    order: 8
    generation_mode: "template"
    required_evidence:
      - "safety_actions_status"
    template: |
      ## 8. Actions Taken for Safety Reasons
      During the reporting period, no regulatory actions or label changes were initiated based solely on the spontaneous adverse experience reports analyzed in this interval. All safety data continue to be actively monitored.
```

---

## 3. Supported Generation Modes

| Mode | Handler | Description | Used in Sections |
| :--- | :--- | :--- | :--- |
| `template` | `render_template_section` | Pure deterministic string template interpolation using exact figures from the evidence packet. | `executive_summary`, `regulatory_actions` |
| `table` | `render_table_section` | Deterministic GitHub Flavored Markdown table generation with column alignment and percent formatting. | `demographics` |
| `llm` | `llm_generator.generate` | Context-bounded LLM narrative generation guided by regulatory system prompt and non-invention rules. | `narrative_summary` |
| `table_and_llm` | `render_table_section` + `llm_generator.generate` | Formatted markdown table followed by evidence-grounded clinical interpretation narrative. | `fifteen_day_alerts`, `serious_cases_breakdown`, `reactions_and_outcomes`, `trend_analysis` |

---

## 4. Phase 6 Checklist & Definition of Done

- [x] Declarative report schema loaded and validated into typed `ReportConfig` and `SectionConfig` models.
- [x] All 8 PADER sections defined with distinct generation modes, evidence bindings, and anti-hallucination rules.
- [x] Extensible architecture ready to support future report types (PSUR, PBRER, DSUR, CSR) by adding new YAML configs without Python code changes.
- [x] Unit and schema validation tests passing in `tests/test_config.py`.

---

## 5. How to Run and Test Phase 6

Validate report configuration via CLI:
```powershell
python -m genar validate-config -r configs/pader.yaml
```

Run test suite:
```powershell
python -m pytest tests/test_config.py -v
```
