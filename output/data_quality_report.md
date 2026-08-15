## Data Quality and Integrity Assessment

- **Total Raw Rows Ingested:** 1,068
- **Unique Safety Report IDs:** 1,024
- **Duplicate/Updated Case Instances:** 41
- **Reaction/Outcome List Alignment Mismatches:** 6
- **Total Findings:** Critical (0), Warnings (47), Info (0)

### Findings Breakdown by Category
| Issue Type | Count |
| :--- | :--- |
| `UPDATED_CASE_ROW` | 41 |
| `LIST_LENGTH_MISMATCH` | 6 |

### Positional List Mismatch Details
The following cases contain comma-separated reaction lists whose lengths differ from their associated outcome lists (likely due to embedded commas in MedDRA terms):
- **Case `25459724` (Row 316):** PTs: 17 vs Outcomes: 16
- **Case `25282743` (Row 362):** PTs: 4 vs Outcomes: 3
- **Case `25187835` (Row 510):** PTs: 7 vs Outcomes: 6
- **Case `25517207` (Row 701):** PTs: 19 vs Outcomes: 18
- **Case `26115793` (Row 786):** PTs: 7 vs Outcomes: 6
- **Case `26144528` (Row 822):** PTs: 4 vs Outcomes: 3
