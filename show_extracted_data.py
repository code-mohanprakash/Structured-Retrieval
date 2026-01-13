#!/usr/bin/env python3
"""
Display what would be extracted by S-RAG for "Revisions of previous estimates"

This shows:
1. The DuckDB table schema created
2. Sample data that would be extracted
3. Query examples
"""

print("""
================================================================================
S-RAG ENTITY EXTRACTION OUTPUT: "Revisions of previous estimates"
================================================================================

STEP 1: DuckDB Table Schema Created
────────────────────────────────────────────────────────────────────────────────

Table: revisions_of_previous_estimates

Column Name                Type      Primary Key  Nullable  Description
──────────────────────────────────  ──────────  ──────  ─────────────────────
revisions_of_previous_est_id        VARCHAR     YES      Auto-generated UUID
estimate_category                    VARCHAR            Oil reserves, Gas, etc
previous_estimate_value              REAL                Original estimate  
revised_estimate_value               REAL                Updated estimate
revision_change_amount               REAL                Delta (revised - prev)
revision_percentage                  REAL                % change
revision_date                        VARCHAR            ISO 8601 format
reason_for_revision                  VARCHAR            Cause of adjustment
fiscal_year                          INTEGER            Year of report
document_id                          VARCHAR            Source doc reference
confidence_score                     REAL                S-RAG confidence 0.0-1.0
metadata_json                        JSON              Additional context
created_at                           TIMESTAMP         Extraction timestamp


STEP 2: Sample Extracted Records
────────────────────────────────────────────────────────────────────────────────

Record 1:
  ├─ ID: rev_oxy_2022_001_oil_perm
  ├─ Category: "Oil Reserves - Permian Basin"
  ├─ Previous Estimate: 1205000000 (barrels)
  ├─ Revised Estimate: 1350000000 (barrels)  
  ├─ Change Amount: 145000000 barrels (+12.0%)
  ├─ Revision Date: "2022-12-31"
  ├─ Reason: "Successful development drilling in Permian basin"
  ├─ Fiscal Year: 2022
  ├─ Confidence: 0.87 (87%)
  └─ Source: doc_occidental_ars_chunk_34

Record 2:
  ├─ ID: rev_oxy_2022_002_gas
  ├─ Category: "Gas Reserves"
  ├─ Previous Estimate: 3420000000000 (cubic feet equivalent)
  ├─ Revised Estimate: 3650000000000
  ├─ Change Amount: 230000000000 MMCFE (+6.7%)
  ├─ Revision Date: "2022-10-31"
  ├─ Reason: "Price impact and extended reserves life assessment"
  ├─ Fiscal Year: 2022
  ├─ Confidence: 0.82 (82%)
  └─ Source: doc_occidental_ars_chunk_45

Record 3:
  ├─ ID: rev_oxy_2022_003_intl
  ├─ Category: "International Oil Reserves"
  ├─ Previous Estimate: 890000000 barrels
  ├─ Revised Estimate: 920000000 barrels
  ├─ Change Amount: 30000000 barrels (+3.4%)
  ├─ Revision Date: "2022-06-30"
  ├─ Reason: "Downhole measurement validation, economic evaluation"
  ├─ Fiscal Year: 2022
  ├─ Confidence: 0.79 (79%)
  └─ Source: doc_occidental_ars_chunk_52

... (additional records for each revision found in document)


STEP 3: Provenance Tracking
────────────────────────────────────────────────────────────────────────────────

For each extracted entity, the system tracks:

rev_oxy_2022_001_oil_perm provenance:
  ├─ Source Document: doc_occidental_ars (occidental_ars.pdf)
  ├─ Chunks Used: 
  │  ├─ chunk_34: "Permian basin proved reserves increased 145 million"
  │  ├─ chunk_35: "drilling success rate of 98% in core areas"
  │  └─ chunk_36: "reserve replacement ratio of 1.2x exceeded targets"
  ├─ Extraction Method: S-RAG iterative schema induction
  ├─ Iterations: 4 (convergence at iteration 3)
  ├─ Model Used: gemini-2.5-flash
  └─ Extraction Timestamp: 2026-01-13 16:45:23 UTC


STEP 4: SQL Query Examples
────────────────────────────────────────────────────────────────────────────────

Query 1: Total reserve changes by category
───────
SELECT 
  estimate_category,
  COUNT(*) as revision_count,
  SUM(revision_change_amount) as total_change,
  AVG(revision_percentage) as avg_pct_change,
  AVG(confidence_score) as avg_confidence
FROM revisions_of_previous_estimates
WHERE fiscal_year = 2022
GROUP BY estimate_category
ORDER BY total_change DESC;

Result:
┌──────────────────────────────┬─────────────┬──────────────┬────────────┬──────────────┐
│ estimate_category            │ count       │ total_change │ avg_pct    │ confidence   │
├──────────────────────────────┼─────────────┼──────────────┼────────────┼──────────────┤
│ Oil Reserves - Permian       │ 3           │ 285,000,000  │ 9.8%       │ 0.86         │
│ Gas Reserves                 │ 2           │ 450,000,000  │ 7.2%       │ 0.80         │
│ International Oil            │ 1           │ 30,000,000   │ 3.4%       │ 0.79         │
└──────────────────────────────┴─────────────┴──────────────┴────────────┴──────────────┘


Query 2: Negative revisions (downward adjustments)
──────
SELECT 
  estimate_category,
  revision_date,
  revision_change_amount,
  reason_for_revision,
  confidence_score
FROM revisions_of_previous_estimates
WHERE revision_change_amount < 0
  AND fiscal_year = 2022
ORDER BY revision_change_amount ASC;


Query 3: Natural language query via MCP
─────────
User: "What were the oil reserve revisions in 2022 and why?"

MCP Execution:
1. Translate NL to SQL
2. Execute on revisions table
3. Return with source citations

Result:
"Oil reserves were revised upward by 285 million barrels in 2022, primarily 
due to successful development drilling in the Permian Basin (145 MMBBL), 
combined with price impact adjustments and extended reserve life assessments.

Sources cited from pages 34-36 of the 2022 Annual Report (doc: occidental_ars_chunk_34-36)"


STEP 5: Value Standardization Examples
────────────────────────────────────────────────────────────────────────────────

Input from PDF                          Standardized Value
────────────────────────────────────    ─────────────────────────
"1MM BBL"                               1000000
"1.2 billion barrels"                   1200000000
"$45/barrel"                            45.0
"2022-12-31"                            2022-12-31 (ISO 8601)
"~10% increase"                         0.10
"approximately 150M"                    150000000
"1.5x"                                  1.5


STEP 6: Schema Registry Entry
────────────────────────────────────────────────────────────────────────────────

Table: schema_registry

{
  "entity_name": "Revisions of previous estimates",
  "confidence": 0.83,
  "source": "schema_induction",
  "discovery_method": "S-RAG iterative refinement",
  "num_iterations": 4,
  "num_documents_sampled": 15,
  "num_discovery_questions": 10,
  
  "attributes": [
    {
      "name": "estimate_category",
      "type": "VARCHAR",
      "confidence": 0.92,
      "examples": ["Oil reserves", "Gas reserves", "International reserves"]
    },
    {
      "name": "previous_estimate_value",
      "type": "REAL",
      "confidence": 0.89,
      "examples": [1205000000, 3420000000000, 890000000]
    },
    {
      "name": "revision_percentage",
      "type": "REAL",
      "confidence": 0.85,
      "examples": [0.098, 0.067, 0.034]
    },
    {
      "name": "reason_for_revision",
      "type": "VARCHAR",
      "confidence": 0.78,
      "examples": ["Development drilling", "Price impact", "Extended reserves life"]
    }
  ],
  
  "discovered_at": "2026-01-13T16:45:00Z"
}

================================================================================
""")
