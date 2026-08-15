"""Deterministic template renderer for template-based report sections."""

import re
from typing import Any, Dict
from genar.config import SectionConfig
from genar.models.evidence import EvidencePacket


def render_template_section(section_cfg: SectionConfig, packet: EvidencePacket) -> str:
    """Interpolate approved evidence packet metrics into configured markdown template."""
    if not section_cfg.template:
        return f"## {section_cfg.title}\n\n*No template defined for section.*"

    # Merge summary metrics and items
    params: Dict[str, Any] = dict(packet.summary_metrics)
    for k, item in packet.items.items():
        params[k] = item.formatted_value
        params[item.metric_key] = item.value

    # Default fallback formatting
    template_str = section_cfg.template

    # Replace placeholders safely (e.g. {total_cases})
    def replacer(match):
        key = match.group(1).strip()
        val = params.get(key)
        if val is not None:
            if isinstance(val, float):
                return f"{val:,.2f}".rstrip("0").rstrip(".")
            elif isinstance(val, int):
                return f"{val:,}"
            return str(val)
        return f"[{key.upper()}_UNAVAILABLE]"

    rendered = re.sub(r"\{([^{}]+)\}", replacer, template_str)
    return rendered.strip()
