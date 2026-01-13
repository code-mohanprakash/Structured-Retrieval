"""
Schema Induction Prompts for S-RAG

Implements the iterative schema refinement from S-RAG paper (arXiv:2511.08505v1).
Per Section 3.2.1: Schema prediction uses an iterative algorithm with 4 iterations,
12 documents, and 10 questions to refine the schema.
"""

from typing import List, Dict, Any, Optional


# ============================================================================
# S-RAG PAPER PROMPTS (Appendix B)
# ============================================================================

SCHEMA_PROMPT_FIRST_ITERATION = """Task: Extract a single JSON schema from the provided documents.

I'll provide you with a set of documents. Your task is to analyze these documents and identify recurring concepts. Then, build a single JSON schema that exhaustively captures *all* these concepts across all documents.

Focus specifically on identifying patterns that appear consistently across multiple documents.

Present your response as a complete JSON schema with the following structure:

```json
{{
  "title": "YourSchemaName",
  "type": "object",
  "properties": {{
    "fieldName": {{
      "type": "string",
      "description": "Detailed description of the field, at least two sentences.",
      "examples": ["example1", "example2"]
    }}
  }},
  "required": ["fieldName"]
}}
```

When building the schema:
- Avoid object-type fields with additional nested properties when possible.
- Avoid list. Instead use boolean attribute for each of the potential value.
- Make sure to capture all recurring concepts
- Relevant concepts may include locations, dates, numbers, strings, etc.
- Relevant concepts should not be lengthy strings (e.g. a "description" field is not a good choice), you should rather decompose into separate fields if possible.

**Documents**:
{documents_text}

Return ONLY the JSON schema, no additional text."""


SCHEMA_PROMPT_REFINEMENT = """Task: Refine an existing JSON schema based on set of questions and documents analysis.

I'll provide you with an existing JSON schema, set of questions, and a set of documents. The JSON schemas of different documents will be converted into an SQL table, that will be used as knowledge source to answer questions that are similar to the provided questions.

Your task is to analyze what attributes from the documents can provide answers to questions similar to the provided questions, and refine the existing schema.

Make sure that the attribute value can be extracted (and not inferred) from each of the documents.

**Existing Schema**:
```json
{existing_schema}
```

**Sample Questions** (the schema should be able to answer these types of questions):
{questions_text}

**Documents**:
{documents_text}

When evaluating the existing schema:
- Make sure that every property can be extracted from each of the documents
- Modify properties where the name, type, or definition could be improved
- Add new properties for concepts that can help answer the questions. E.g.: if a question is about "the most common location", you should add a property for "location" if it doesn't exist. Make sure that the property value can be extracted from each of the documents.
- Add new properties for recurring concepts not captured in the existing schema
- Add new properties for trivial concepts that are missing in the existing schema. E.g: If the schema represents a house for sale, it must include the seller's name.
- Use appropriate JSON Schema types (string, number, integer, boolean, array, etc.)
- Provide descriptions and examples for each property
- Avoid nested object properties
- Fields should not be lengthy strings (e.g. a "description" field is not a good choice), you should rather decompose into separate fields if possible.
- Avoid assigning values to the attributes in the schema. You should only provide the schema itself, without any values.

For each property decision, provide a clear rationale based on related question or patterns observed in the documents. Your goal is to create a refined schema that better captures the recurring patterns that can be used to answer the questions while minimizing unnecessary changes to the existing structure.

Provide the final refined JSON schema implementation:

```json
{{
  "title": "RefinedSchemaName",
  "type": "object",
  "properties": {{
    "propertyName": {{
      "type": "string",
      "description": "Detailed description of the property, at least two sentences.",
      "examples": ["example1", "example2"]
    }}
  }},
  "required": ["propertyName"]
}}
```

Return ONLY the JSON schema, no additional text."""


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


def build_iterative_schema_first_prompt(
    sample_documents: List[str],
    max_samples: int = 12
) -> str:
    """
    Build prompt for first iteration of schema induction (S-RAG paper Section 3.2.1)
    
    Per paper: Uses 12 documents in zero-shot prompting for initial schema.
    
    Args:
        sample_documents: Sample document texts for analysis
        max_samples: Maximum documents (default 12 per paper)
    
    Returns:
        Formatted prompt string
    """
    documents_text = "\n\n".join([
        f"--- Document {i+1} ---\n{doc[:2000]}"  # Truncate to 2000 chars per doc
        for i, doc in enumerate(sample_documents[:max_samples])
    ])
    
    return SCHEMA_PROMPT_FIRST_ITERATION.format(documents_text=documents_text)


def build_iterative_schema_refinement_prompt(
    existing_schema: Dict[str, Any],
    sample_questions: List[str],
    sample_documents: List[str],
    max_samples: int = 12
) -> str:
    """
    Build prompt for schema refinement iteration (S-RAG paper Section 3.2.1)
    
    Per paper: Refines schema using documents + 10 sample questions to ensure
    the schema can answer queries that will be asked at inference time.
    
    Args:
        existing_schema: Current schema from previous iteration
        sample_questions: Representative questions (default 10 per paper)
        sample_documents: Sample document texts
        max_samples: Maximum documents
    
    Returns:
        Formatted prompt string
    """
    import json
    
    documents_text = "\n\n".join([
        f"--- Document {i+1} ---\n{doc[:2000]}"
        for i, doc in enumerate(sample_documents[:max_samples])
    ])
    
    questions_text = "\n".join([
        f"{i+1}. {q}" 
        for i, q in enumerate(sample_questions[:10])
    ])
    
    existing_schema_json = json.dumps(existing_schema, indent=2)
    
    return SCHEMA_PROMPT_REFINEMENT.format(
        existing_schema=existing_schema_json,
        questions_text=questions_text,
        documents_text=documents_text
    )


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
    table_schemas: Dict[str, List[Dict[str, Any]]],
    column_statistics: Optional[Dict[str, str]] = None
) -> str:
    """
    Build prompt for translating natural language to SQL.
    
    Per S-RAG paper Section 3.3: "To enhance the quality of the generated 
    query and avoid ambiguity, the LLM receives as input the query q, 
    the schema S and statistics for every column in the DB."
    
    Args:
        natural_language_query: User's question in natural language
        available_tables: List of table names in database
        table_schemas: Dict mapping table name to list of column definitions
        column_statistics: Optional dict mapping table names to formatted statistics strings
    
    Returns:
        Formatted prompt string
    """
    
    schema_text = ""
    for table_name in available_tables:
        columns = table_schemas.get(table_name, [])
        column_list = ", ".join([f"{col['name']} {col['type']}" for col in columns])
        schema_text += f"\nCREATE TABLE {table_name} ({column_list});\n"
    
    # Include column statistics if provided (S-RAG paper Section 3.3)
    stats_text = ""
    if column_statistics:
        stats_text = "\n\n**Column Statistics** (use these to understand data ranges and values):\n"
        for table_name, stats_str in column_statistics.items():
            stats_text += f"\n{stats_str}\n"
    
    prompt = f"""You are a SQL expert. Translate the natural language query into DuckDB SQL.

**Available Database Schema**:
{schema_text}
{stats_text}

**Natural Language Query**: {natural_language_query}

**Instructions**:
1. Generate valid DuckDB SQL that answers the query
2. Use proper JOIN clauses if query spans multiple tables
3. Include appropriate WHERE, GROUP BY, ORDER BY, LIMIT clauses
4. For aggregations (count, sum, avg), include descriptive column aliases
5. Ensure query is safe (no DROP, DELETE, INSERT, UPDATE, ALTER)
6. Return results in a readable format
7. Use the column statistics to map semantic query terms to correct column values
   (e.g., if statistics show values like "New York", "Los Angeles", use exact matches)

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


# ============================================================================
# EVALUATION PROMPTS (S-RAG Paper Section 5.5 and Appendix E)
# ============================================================================

EVAL_PROMPT_ANSWER_COMPARISON = """<instructions>
You are given a query, a gold answer, and a judged answer.
Decide if the judged answer is a correct answer for the query, based on the gold answer.
Do not use any external or prior knowledge. Only use the gold answer.
Answer Yes if the judged answer is a correct answer for the query, and No otherwise.

<query>
{query}
</query>

<gold_answer>
{gold_answer}
</gold_answer>

<judged_answer>
{judged_answer}
</judged_answer>
</instructions>"""


def build_answer_comparison_prompt(
    query: str,
    gold_answer: str,
    judged_answer: str
) -> str:
    """
    Build prompt for LLM-as-judge Answer Comparison metric.
    
    Per S-RAG paper Section 5.5: "Answer Comparison, where the LLM is 
    instructed to provide a binary judgment on whether the generated 
    answer is correct given the query and the expected answer."
    
    Args:
        query: The original question
        gold_answer: The expected correct answer
        judged_answer: The system-generated answer to evaluate
    
    Returns:
        Formatted evaluation prompt
    """
    return EVAL_PROMPT_ANSWER_COMPARISON.format(
        query=query,
        gold_answer=gold_answer,
        judged_answer=judged_answer
    )


def build_answer_recall_prompt(
    gold_answer: str,
    judged_answer: str
) -> str:
    """
    Build prompt for LLM-as-judge Answer Recall metric.
    
    Per S-RAG paper Section 5.5: "Answer Recall, where an LLM-based 
    system decomposes the expected answer into individual claims and 
    computes the percentage of those claims that are covered in the 
    generated answer."
    
    Args:
        gold_answer: The expected correct answer
        judged_answer: The system-generated answer to evaluate
    
    Returns:
        Formatted evaluation prompt
    """
    return f"""Evaluate the coverage of claims in the judged answer compared to the gold answer.

**Gold Answer (Expected)**:
{gold_answer}

**Judged Answer (Generated)**:
{judged_answer}

**Task**:
1. Decompose the gold answer into individual claims/facts
2. For each claim, determine if it is covered in the judged answer
3. Calculate the percentage of claims covered

**Output Format** (valid JSON):
{{
  "claims": [
    {{"claim": "claim text", "covered": true}},
    {{"claim": "claim text", "covered": false}}
  ],
  "total_claims": 5,
  "covered_claims": 3,
  "recall_score": 0.6
}}

Return ONLY the JSON, no additional text."""
