"""Builds section-scoped, strictly isolated EvidencePacket objects for report generation."""

from typing import Any, Dict, List, Optional
from genar.config import DatasetConfig, ReportConfig, SectionConfig
from genar.evidence.store import EvidenceStore
from genar.models.evidence import EvidenceItem, EvidencePacket


def build_evidence_packet(
    section_cfg: SectionConfig,
    store: EvidenceStore,
    dataset_cfg: DatasetConfig,
) -> EvidencePacket:
    """Construct an EvidencePacket containing ONLY the approved facts declared for this section."""
    section_id = section_cfg.id
    items: Dict[str, EvidenceItem] = {}
    summary_metrics: Dict[str, Any] = {}
    table_data: Optional[List[Dict[str, Any]]] = None

    # Common dataset context
    vol_res = store.get("total_case_volume")
    period_str = f"{dataset_cfg.reporting_period_start} to {dataset_cfg.reporting_period_end}"
    if vol_res:
        start = vol_res.metrics.get("reporting_period_start", dataset_cfg.reporting_period_start)
        end = vol_res.metrics.get("reporting_period_end", dataset_cfg.reporting_period_end)
        period_str = f"{start} to {end}"

    # Extract required evidence items strictly based on declared keys
    req = set(section_cfg.required_evidence)

    # 1. Volume evidence
    if vol_res and ("total_case_volume" in req or "reporting_period" in req or "narrative_synthesis_packet" in req):
        if "total_case_volume" in req or "narrative_synthesis_packet" in req:
            items["total_case_volume"] = store.create_evidence_item(
                evidence_id="ev_total_case_volume",
                title="Total Case Volume",
                metric_key="total_cases",
                analysis_id="total_case_volume",
                value=vol_res.metrics.get("total_cases"),
                formatted_value=f"{vol_res.metrics.get('total_cases'):,} cases",
                description="Total unique canonical adverse event cases evaluated.",
            )
            summary_metrics["total_cases"] = vol_res.metrics.get("total_cases")
            summary_metrics["total_reactions"] = vol_res.metrics.get("total_reactions")

        if "reporting_period" in req or "narrative_synthesis_packet" in req:
            items["reporting_period"] = store.create_evidence_item(
                evidence_id="ev_reporting_period",
                title="Reporting Period Interval",
                metric_key="reporting_period",
                analysis_id="total_case_volume",
                value=period_str,
                formatted_value=period_str,
                description="Inclusive date interval of received adverse event reports.",
            )
            summary_metrics["reporting_period_start"] = vol_res.metrics.get("reporting_period_start")
            summary_metrics["reporting_period_end"] = vol_res.metrics.get("reporting_period_end")

    # 2. Seriousness evidence
    ser_res = store.get("seriousness_breakdown")
    if ser_res:
        if "serious_case_count" in req or "narrative_synthesis_packet" in req:
            items["serious_case_count"] = store.create_evidence_item(
                evidence_id="ev_serious_case_count",
                title="Serious Case Count",
                metric_key="serious_cases",
                analysis_id="seriousness_breakdown",
                value=ser_res.metrics.get("serious_cases"),
                formatted_value=f"{ser_res.metrics.get('serious_cases'):,} ({ser_res.metrics.get('serious_percent')}%)",
                description="Count and proportion of cases meeting regulatory seriousness criteria.",
            )
            summary_metrics["serious_cases"] = ser_res.metrics.get("serious_cases")
            summary_metrics["serious_percent"] = ser_res.metrics.get("serious_percent")

        if "non_serious_case_count" in req:
            items["non_serious_case_count"] = store.create_evidence_item(
                evidence_id="ev_non_serious_case_count",
                title="Non-Serious Case Count",
                metric_key="non_serious_cases",
                analysis_id="seriousness_breakdown",
                value=ser_res.metrics.get("non_serious_cases"),
                formatted_value=f"{ser_res.metrics.get('non_serious_cases'):,} ({ser_res.metrics.get('non_serious_percent')}%)",
                description="Count and proportion of non-serious cases.",
            )
            summary_metrics["non_serious_cases"] = ser_res.metrics.get("non_serious_cases")
            summary_metrics["non_serious_percent"] = ser_res.metrics.get("non_serious_percent")

        if "seriousness_criteria_counts" in req or "seriousness_percentage_breakdown" in req:
            items["seriousness_criteria_counts"] = store.create_evidence_item(
                evidence_id="ev_seriousness_criteria",
                title="Seriousness Criteria Breakdown",
                metric_key="criteria",
                analysis_id="seriousness_breakdown",
                value=ser_res.metrics.get("criteria"),
                formatted_value=f"Hospitalization: {ser_res.metrics.get('criteria', {}).get('hospitalization_count')}, Death: {ser_res.metrics.get('criteria', {}).get('death_count')}",
                description="Discrete counts across individual regulatory seriousness criteria.",
                table_representation=ser_res.metrics.get("criteria_table"),
            )
            table_data = ser_res.metrics.get("criteria_table")

        # Capture death count for executive summary interpolation
        if section_id == "executive_summary":
            summary_metrics["fatalities_count"] = ser_res.metrics.get("criteria", {}).get("death_count", 0)

    # 3. 15-Day Alert evidence
    alert_res = store.get("fifteen_day_alerts")
    if alert_res:
        if "fifteen_day_alert_count" in req or "narrative_synthesis_packet" in req:
            items["fifteen_day_alert_count"] = store.create_evidence_item(
                evidence_id="ev_fifteen_day_alerts",
                title="15-Day Expedited Alert Reports",
                metric_key="fifteen_day_alerts_count",
                analysis_id="fifteen_day_alerts",
                value=alert_res.metrics.get("fifteen_day_alerts_count"),
                formatted_value=f"{alert_res.metrics.get('fifteen_day_alerts_count'):,} cases ({alert_res.metrics.get('fifteen_day_alerts_percent')}%)",
                description="Cases meeting expedited 15-day alert reporting criteria.",
            )
            summary_metrics["fifteen_day_alerts"] = alert_res.metrics.get("fifteen_day_alerts_count")

        if "fifteen_day_alerts_breakdown" in req or "fifteen_day_top_reactions" in req:
            items["fifteen_day_alerts_breakdown"] = store.create_evidence_item(
                evidence_id="ev_fifteen_day_details",
                title="15-Day Alert Details & Top Events",
                metric_key="top_reactions_in_alerts",
                analysis_id="fifteen_day_alerts",
                value=alert_res.metrics.get("top_reactions_in_alerts"),
                formatted_value=str(alert_res.metrics.get("top_reactions_in_alerts")),
                description="Top adverse events reported among 15-day alert cases.",
            )
            top_alert_rxns = alert_res.metrics.get("top_reactions_in_alerts", {})
            table_data = [{"preferred_term": k, "alert_events_count": v} for k, v in top_alert_rxns.items()]

    # 4. Demographics evidence
    demo_res = store.get("demographics_breakdown")
    if demo_res:
        if "sex_distribution" in req or "age_group_distribution" in req or "country_distribution" in req:
            items["demographics_summary"] = store.create_evidence_item(
                evidence_id="ev_demographics",
                title="Demographic Distribution Summary",
                metric_key="sex_distribution",
                analysis_id="demographics_breakdown",
                value={
                    "sex": demo_res.metrics.get("sex_distribution"),
                    "age_groups": demo_res.metrics.get("age_group_distribution"),
                    "age_stats": demo_res.metrics.get("age_statistics"),
                    "countries": demo_res.metrics.get("country_distribution"),
                },
                formatted_value=f"Sex: {demo_res.metrics.get('sex_distribution')}, Elderly: {demo_res.metrics.get('age_group_distribution', {}).get('Elderly (65+)')}",
                description="Sex, age bucket, age summary stats, and geographic distribution.",
                table_representation=demo_res.metrics.get("demographics_table"),
            )
            table_data = demo_res.metrics.get("demographics_table")

    # 5. Reactions evidence
    rxn_res = store.get("reactions_analysis")
    if rxn_res:
        if "top_adverse_reactions" in req or "serious_vs_nonserious_reactions" in req or "narrative_synthesis_packet" in req:
            items["top_adverse_reactions"] = store.create_evidence_item(
                evidence_id="ev_top_reactions",
                title="Top Adverse Drug Reactions",
                metric_key="top_reactions_overall",
                analysis_id="reactions_analysis",
                value=rxn_res.metrics.get("top_reactions_overall"),
                formatted_value=f"{rxn_res.metrics.get('unique_preferred_terms')} unique PTs reported",
                description="Top reported MedDRA preferred terms ranked by event frequency and case count.",
                table_representation=rxn_res.metrics.get("top_reactions_overall"),
            )
            if table_data is None and "top_adverse_reactions" in req:
                table_data = rxn_res.metrics.get("top_reactions_overall")

    # 6. Outcomes evidence
    out_res = store.get("outcomes_analysis")
    if out_res:
        if "reaction_outcomes_summary" in req or "narrative_synthesis_packet" in req:
            items["reaction_outcomes_summary"] = store.create_evidence_item(
                evidence_id="ev_reaction_outcomes",
                title="Reaction Outcome Breakdown",
                metric_key="outcome_distribution",
                analysis_id="outcomes_analysis",
                value=out_res.metrics.get("outcome_distribution"),
                formatted_value=f"Resolved: {out_res.metrics.get('outcome_distribution', {}).get('recovered/resolved')}, Fatal: {out_res.metrics.get('outcome_distribution', {}).get('fatal')}",
                description="Cross-tabulation of positionally valid reactions with clinical outcomes.",
                table_representation=out_res.metrics.get("reaction_outcome_matrix"),
            )
            if "reaction_outcomes_summary" in req:
                table_data = out_res.metrics.get("reaction_outcome_matrix")

    # 7. Trend evidence
    trend_res = store.get("interval_trends")
    if trend_res:
        if "monthly_case_counts" in req or "flagged_trend_anomalies" in req:
            items["interval_trends"] = store.create_evidence_item(
                evidence_id="ev_interval_trends",
                title="Monthly Trends & Candidate Anomalies",
                metric_key="monthly_counts",
                analysis_id="interval_trends",
                value={
                    "monthly_counts": trend_res.metrics.get("monthly_counts"),
                    "candidate_anomalies": trend_res.metrics.get("candidate_anomalies"),
                },
                formatted_value=f"{trend_res.metrics.get('total_months')} months analyzed; {len(trend_res.metrics.get('candidate_anomalies', []))} statistical anomalies flagged",
                description="Monthly case volumes and candidate statistical anomalies.",
                table_representation=trend_res.metrics.get("monthly_table"),
            )
            table_data = trend_res.metrics.get("monthly_table")

    # Product and template interpolation parameters
    summary_metrics["product_name"] = dataset_cfg.product_name
    summary_metrics["active_substance"] = dataset_cfg.active_substance
    summary_metrics["manufacturer"] = dataset_cfg.manufacturer

    return EvidencePacket(
        section_id=section_id,
        section_title=section_cfg.title,
        dataset_name=dataset_cfg.dataset_name,
        reporting_period=period_str,
        items=items,
        summary_metrics=summary_metrics,
        table_data=table_data,
        non_invention_notes=section_cfg.non_invention_rules,
    )


def build_all_packets(
    report_cfg: ReportConfig,
    store: EvidenceStore,
    dataset_cfg: DatasetConfig,
) -> Dict[str, EvidencePacket]:
    """Assemble section-scoped evidence packets for all configured report sections."""
    packets: Dict[str, EvidencePacket] = {}
    for section_cfg in report_cfg.sections:
        packets[section_cfg.id] = build_evidence_packet(section_cfg, store, dataset_cfg)
    return packets
