"""
Schema Induction Prompts for GPT-4o

Prompt engineering for extracting structured schemas from unstructured documents.
Uses few-shot examples and guided entity hints to reduce hallucination.
"""

from typing import List, Dict, Any, Optional


def build_schema_induction_prompt(
    entity_hints: List[str],
    sample_documents: List[str],
    max_samples: int = 10
) -> str:
    """
    Build prompt for schema induction from documents
    
    Args:
        entity_hints: User-provided entity types (e.g. ["Deal", "Company", "Person"])
        sample_documents: Sample document texts for analysis
        max_samples: Maximum number of samples to include in prompt
    
    Returns:
        Formatted prompt string
    """
    
    samples_text = "\n\n".join([
        f"--- Document {i+1} ---\n{doc[:1000]}"  # Truncate to 1000 chars per doc
        for i, doc in enumerate(sample_documents[:max_samples])
    ])
    
    entity_list = ", ".join(entity_hints)
    
    prompt = f"""You are a data schema expert. Your task is to analyze sample documents and extract a structured database schema.

**Entity Types to Focus On**: {entity_list}

**Instructions**:
1. For each entity type, identify ALL relevant attributes mentioned in the documents
2. Determine the appropriate data type for each attribute (TEXT, INTEGER, REAL, DATE, BOOLEAN)
3. Identify relationships between entities (foreign keys)
4. Extract only attributes that appear in the actual documents - do not invent fields
5. Include confidence scores (0.0-1.0) based on how frequently/clearly each attribute appears

**Sample Documents**:

{samples_text}

**Output Format** (valid JSON):
{{
  "entities": [
    {{
      "name": "Deal",
      "attributes": [
        {{"name": "deal_id", "type": "TEXT", "confidence": 1.0, "is_primary_key": true}},
        {{"name": "deal_name", "type": "TEXT", "confidence": 0.95}},
        {{"name": "deal_value", "type": "REAL", "confidence": 0.9}},
        {{"name": "close_date", "type": "DATE", "confidence": 0.85}}
      ],
      "relationships": [
        {{"to_entity": "Company", "foreign_key": "company_id", "relationship_type": "many-to-one"}}
      ]
    }},
    {{
      "name": "Company",
      "attributes": [
        {{"name": "company_id", "type": "TEXT", "confidence": 1.0, "is_primary_key": true}},
        {{"name": "company_name", "type": "TEXT", "confidence": 1.0}},
        {{"name": "industry", "type": "TEXT", "confidence": 0.8}}
      ],
      "relationships": []
    }}
  ],
  "metadata": {{
    "total_documents_analyzed": {min(len(sample_documents), max_samples)},
    "extraction_notes": "Brief notes on schema decisions"
  }}
}}

Return ONLY the JSON, no additional text."""
    
    return prompt


def build_entity_extraction_prompt(
    entity_name: str,
    entity_schema: Dict[str, Any],
    document_text: str
) -> str:
    """
    Build prompt for extracting entity instances from a document
    
    Args:
        entity_name: Name of entity to extract (e.g. "Deal")
        entity_schema: Schema definition with attributes
        document_text: Full document text to analyze
    
    Returns:
        Formatted prompt string
    """
    
    attributes = entity_schema.get("attributes", [])
    attr_descriptions = "\n".join([
        f"  - {attr['name']} ({attr['type']})"
        for attr in attributes
    ])
    
    prompt = f"""Extract all {entity_name} entities from the following document.

**Entity**: {entity_name}
**Attributes**:
{attr_descriptions}

**Document**:
{document_text[:3000]}  # Truncate to 3000 chars

**Instructions**:
1. Extract ALL instances of {entity_name} mentioned in the document
2. For each instance, extract values for all listed attributes
3. Use null for missing attributes
4. Include source_chunk_id for provenance (will be filled by system)
5. Be precise - extract exact values as they appear

**Output Format** (valid JSON):
{{
  "entities": [
    {{
      "entity_type": "{entity_name}",
      "attributes": {{
        "attr1": "value1",
        "attr2": 123,
        "attr3": null
      }},
      "confidence": 0.95,
      "source_text": "Relevant excerpt from document that mentions this entity"
    }}
  ]
}}

Return ONLY the JSON array, no additional text."""
    
    return prompt


def build_query_translation_prompt(
    natural_language_query: str,
    available_tables: List[str],
    table_schemas: Dict[str, List[Dict[str, Any]]]
) -> str:
    """
    Build prompt for translating natural language to SQL
    
    Args:
        natural_language_query: User's question in natural language
        available_tables: List of table names in database
        table_schemas: Dict mapping table name to list of column definitions
    
    Returns:
        Formatted prompt string
    """
    
    schema_text = ""
    for table_name in available_tables:
        columns = table_schemas.get(table_name, [])
        column_list = ", ".join([f"{col['name']} {col['type']}" for col in columns])
        schema_text += f"\nCREATE TABLE {table_name} ({column_list});\n"
    
    prompt = f"""You are a SQL expert. Translate the natural language query into DuckDB SQL.

**Available Database Schema**:
{schema_text}

**Natural Language Query**: {natural_language_query}

**Instructions**:
1. Generate valid DuckDB SQL that answers the query
2. Use proper JOIN clauses if query spans multiple tables
3. Include appropriate WHERE, GROUP BY, ORDER BY, LIMIT clauses
4. For aggregations (count, sum, avg), include descriptive column aliases
5. Ensure query is safe (no DROP, DELETE, INSERT, UPDATE, ALTER)
6. Return results in a readable format

**Output Format** (valid JSON):
{{
  "sql": "SELECT ... FROM ... WHERE ...",
  "query_type": "aggregation|filter|join|simple",
  "explanation": "Brief explanation of what the SQL does",
  "confidence": 0.95
}}

Return ONLY the JSON, no additional text."""
    
    return prompt


def build_answer_generation_prompt(
    user_query: str,
    sql_query: str,
    sql_results: List[Dict[str, Any]],
    source_documents: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Build prompt for generating natural language answer from SQL results
    
    Args:
        user_query: Original user question
        sql_query: SQL query that was executed
        sql_results: Query results (list of dicts)
        source_documents: Optional source document metadata for citations
    
    Returns:
        Formatted prompt string
    """
    
    # Format results as markdown table
    if not sql_results:
        results_text = "No results returned."
    else:
        # Get column names from first row
        columns = list(sql_results[0].keys())
        header = "| " + " | ".join(columns) + " |"
        separator = "|" + "|".join(["---"] * len(columns)) + "|"
        rows = []
        for row in sql_results[:20]:  # Limit to 20 rows in prompt
            row_text = "| " + " | ".join([str(row.get(col, "")) for col in columns]) + " |"
            rows.append(row_text)
        results_text = "\n".join([header, separator] + rows)
        if len(sql_results) > 20:
            results_text += f"\n\n... ({len(sql_results) - 20} more rows)"
    
    sources_text = ""
    if source_documents:
        sources_text = "\n\n**Source Documents**:\n"
        for i, doc in enumerate(source_documents[:5]):
            sources_text += f"{i+1}. {doc.get('filename', 'Unknown')} (ID: {doc.get('doc_id', 'N/A')})\n"
    
    prompt = f"""Generate a clear, concise answer to the user's question based on the query results.

**User Question**: {user_query}

**SQL Query Executed**:
```sql
{sql_query}
```

**Query Results**:
{results_text}
{sources_text}

**Instructions**:
1. Answer the user's question directly in natural language
2. Highlight key numbers and insights from the results
3. If results are empty, explain what was searched and that nothing was found
4. Keep answer concise (2-4 sentences)
5. Include citations to source documents if provided (use [1], [2] notation)
6. Use markdown formatting for clarity

Return your answer as plain text (not JSON)."""
    
    return prompt


def build_query_classification_prompt(query: str) -> str:
    """
    Build prompt for classifying query intent
    
    Args:
        query: Natural language query
    
    Returns:
        Formatted prompt string
    """
    
    prompt = f"""Classify the following query into one of these categories:

**Query**: {query}

**Categories**:
1. **count** - Counting entities (e.g., "How many deals?", "Count of companies")
2. **aggregation** - Statistical operations (e.g., "Average deal value", "Total revenue", "Max/min")
3. **filter** - Finding specific entities (e.g., "Deals above $1M", "Companies in tech sector")
4. **group_by** - Grouped aggregations (e.g., "Deals by quarter", "Revenue by region")
5. **join** - Multi-entity queries (e.g., "Companies with pending deals", "Sales reps with most wins")
6. **temporal** - Time-based queries (e.g., "Deals closed last month", "Quarterly trends")
7. **ranking** - Top/bottom queries (e.g., "Top 10 deals", "Lowest performers")
8. **simple** - Direct lookups (e.g., "Show deal #123", "Company named Acme")

**Output Format** (valid JSON):
{{
  "primary_category": "aggregation",
  "secondary_categories": ["filter"],
  "requires_join": true,
  "complexity": "medium",
  "confidence": 0.9
}}

Return ONLY the JSON, no additional text."""
    
    return prompt


# System prompts for different LLM tasks
SYSTEM_PROMPT_SCHEMA_INDUCTION = """You are an expert data engineer specializing in schema extraction from unstructured documents. Your role is to analyze document samples and design optimal database schemas that capture the most important entities and their relationships. Be conservative - only extract attributes that are clearly present in the documents."""

SYSTEM_PROMPT_ENTITY_EXTRACTION = """You are a precise data extraction system. Extract entity instances from documents with high accuracy. If an attribute value is not clearly stated in the document, use null. Always preserve exact values as they appear in the source text."""

SYSTEM_PROMPT_QUERY_TRANSLATION = """You are a SQL expert specializing in DuckDB analytics queries. Translate natural language questions into efficient, safe SQL queries. Prioritize readability and correctness. Never generate queries that modify data (only SELECT statements)."""

SYSTEM_PROMPT_ANSWER_GENERATION = """You are a helpful data analyst. Generate clear, concise answers to user questions based on query results. Focus on key insights and make the data easy to understand. Always cite sources when available."""

SYSTEM_PROMPT_QUERY_CLASSIFICATION = """You are a query understanding system. Accurately classify user questions to route them to the appropriate query engine. Consider both the question structure and intent."""
