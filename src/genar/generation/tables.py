"""Deterministic markdown table renderer for tabular report sections."""

from typing import Any, Dict, List, Optional
from genar.config import SectionConfig
from genar.models.evidence import EvidencePacket


def render_markdown_table(
    headers: List[str],
    rows: List[Dict[str, Any]],
    alignments: Optional[List[str]] = None
) -> str:
    """Format row dictionaries into a clean GitHub Flavored Markdown table."""
    if not rows:
        return "*No data records available for this table.*"

    # Determine columns from headers or keys of first row
    first_row = rows[0]
    keys = list(first_row.keys()) if not headers else list(first_row.keys())[:len(headers)]
    display_headers = headers if headers and len(headers) == len(keys) else [k.replace("_", " ").title() for k in keys]

    # Format header line
    header_line = "| " + " | ".join(display_headers) + " |"
    sep_line = "| " + " | ".join([":---" if not alignments else (alignments[i] if i < len(alignments) else ":---") for i in range(len(display_headers))]) + " |"

    # Format data rows
    row_lines = []
    for r in rows:
        formatted_cells = []
        for k in keys:
            val = r.get(k, "")
            if isinstance(val, float):
                formatted_cells.append(f"{val:.2f}%" if "percent" in k.lower() else f"{val:.2f}")
            elif isinstance(val, int):
                formatted_cells.append(f"{val:,}")
            elif val is None:
                formatted_cells.append("-")
            else:
                formatted_cells.append(str(val))
        row_lines.append("| " + " | ".join(formatted_cells) + " |")

    return "\n".join([header_line, sep_line] + row_lines)


def render_table_section(section_cfg: SectionConfig, packet: EvidencePacket) -> str:
    """Render a structured report section containing section title and formatted markdown table."""
    title = f"## {section_cfg.title}"
    
    if not packet.table_data:
        return f"{title}\n\n*No tabular data available in evidence packet.*"

    headers = section_cfg.table_columns or []
    table_md = render_markdown_table(headers, packet.table_data)

    return f"{title}\n\n{table_md}"
