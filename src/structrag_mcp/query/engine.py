"""
Query Engine

Handles natural language to SQL translation, execution, and answer generation.
Includes query classification, safety validation, and result formatting.
"""

import logging
import time
from typing import List, Dict, Any, Optional
import json

from ..llm.provider import complete_with_fallback
from ..llm.prompts import (
    build_query_classification_prompt,
    build_query_translation_prompt,
    build_answer_generation_prompt,
    SYSTEM_PROMPT_QUERY_CLASSIFICATION,
    SYSTEM_PROMPT_QUERY_TRANSLATION,
    SYSTEM_PROMPT_ANSWER_GENERATION
)
from ..storage.duckdb_manager import DuckDBManager
from ..storage.provenance import ProvenanceTracker
from ..structure.models import (
    QueryMetadata,
    SQLQueryResult,
    QueryExecutionResult
)

logger = logging.getLogger(__name__)


def _strip_markdown_json(content: str) -> str:
    """Strip markdown code blocks from LLM response (for Groq compatibility)"""
    content = content.strip()
    # Remove markdown code block markers
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    return content.strip()


class QueryEngine:
    """
    Complete query engine: classification → translation → execution → answer
    
    Usage:
        >>> engine = QueryEngine(db_manager, provenance)
        >>> result = engine.query("How many deals closed last month?")
        >>> print(result.answer)
    """
    
    def __init__(
        self,
        db_manager: DuckDBManager,
        provenance: ProvenanceTracker
    ):
        self.db = db_manager
        self.provenance = provenance
    
    def query(
        self,
        natural_language_query: str,
        format: str = "markdown"
    ) -> QueryExecutionResult:
        """
        Execute complete query pipeline
        
        Args:
            natural_language_query: User's question
            format: Output format ("markdown", "json", "table")
        
        Returns:
            QueryExecutionResult with answer and provenance
        """
        start_time = time.time()
        
        # Generate query ID
        query_id = self.provenance.generate_query_id(natural_language_query)
        
        logger.info(f"Processing query [{query_id}]: {natural_language_query}")
        
        # Step 1: Classify query
        query_metadata = self.classify_query(natural_language_query)
        
        # Step 2: Translate to SQL
        sql_result = self.translate_to_sql(
            natural_language_query,
            query_metadata
        )
        
        # Step 3: Validate SQL safety
        if not self.validate_sql_safety(sql_result.sql):
            raise ValueError(f"Unsafe SQL detected: {sql_result.sql}")
        
        # Step 4: Execute SQL
        try:
            results = self.db.execute_query(sql_result.sql)
            logger.info(f"Query executed successfully, {len(results)} results returned")
        except Exception as e:
            logger.error(f"SQL execution failed: {str(e)}, SQL: {sql_result.sql}")
            # Return empty result with error information
            return QueryExecutionResult(
                query_id=query_id,
                original_query=natural_language_query,
                sql_executed=sql_result.sql,
                results=[],
                result_count=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                answer=f"Unable to execute query: {str(e)}",
                source_documents=[],
                confidence=0.0
            )
        
        # Step 5: Get source documents for provenance
        source_docs = self._get_source_documents(results)
        
        # Step 6: Generate natural language answer
        answer = self.generate_answer(
            user_query=natural_language_query,
            sql_query=sql_result.sql,
            sql_results=results,
            source_documents=source_docs
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Step 7: Log query for audit
        self.db.log_query(
            query_id=query_id,
            query_text=natural_language_query,
            query_type=query_metadata.query_type,
            result_count=len(results)
        )
        
        result = QueryExecutionResult(
            query_id=query_id,
            original_query=natural_language_query,
            sql_executed=sql_result.sql,
            results=results,
            result_count=len(results),
            execution_time_ms=execution_time_ms,
            answer=answer,
            source_documents=source_docs,
            confidence=sql_result.confidence
        )
        
        logger.info(
            f"Query [{query_id}] complete: {len(results)} results, "
            f"{execution_time_ms:.0f}ms, confidence={sql_result.confidence:.2f}"
        )
        
        return result
    
    def classify_query(self, query: str) -> QueryMetadata:
        """
        Classify query intent and complexity
        
        Args:
            query: Natural language query
        
        Returns:
            QueryMetadata with classification
        """
        prompt = build_query_classification_prompt(query)
        
        response = complete_with_fallback(
            system_prompt=SYSTEM_PROMPT_QUERY_CLASSIFICATION,
            user_prompt=prompt,
            json_mode=True
        )
        
        if response.error:
            logger.warning(f"Query classification failed: {response.error}, using defaults")
            # Fallback to simple classification
            return QueryMetadata(
                query_id=self.provenance.generate_query_id(query),
                original_query=query,
                query_type="simple",
                complexity="medium",
                confidence=0.5
            )
        
        try:
            clean_content = _strip_markdown_json(response.content)
            classification = json.loads(clean_content)
        except json.JSONDecodeError:
            logger.error(f"Invalid classification response: {response.content}")
            return QueryMetadata(
                query_id=self.provenance.generate_query_id(query),
                original_query=query,
                query_type="simple",
                complexity="medium",
                confidence=0.5
            )
        
        return QueryMetadata(
            query_id=self.provenance.generate_query_id(query),
            original_query=query,
            query_type=classification.get("primary_category", "simple"),
            requires_join=classification.get("requires_join", False),
            complexity=classification.get("complexity", "medium"),
            confidence=classification.get("confidence", 0.8)
        )
    
    def translate_to_sql(
        self,
        natural_language_query: str,
        query_metadata: Optional[QueryMetadata] = None
    ) -> SQLQueryResult:
        """
        Translate natural language to SQL
        
        Args:
            natural_language_query: User's question
            query_metadata: Optional pre-classified metadata
        
        Returns:
            SQLQueryResult with generated SQL
        """
        # Get available tables and schemas
        tables = self.db.list_tables()
        table_schemas = {}
        
        for table in tables:
            schema = self.db.get_table_schema(table)
            if schema:
                table_schemas[table] = schema
        
        prompt = build_query_translation_prompt(
            natural_language_query=natural_language_query,
            available_tables=tables,
            table_schemas=table_schemas
        )
        
        response = complete_with_fallback(
            system_prompt=SYSTEM_PROMPT_QUERY_TRANSLATION,
            user_prompt=prompt,
            json_mode=True
        )
        
        if response.error:
            raise RuntimeError(f"SQL translation failed: {response.error}")
        
        try:
            clean_content = _strip_markdown_json(response.content)
            sql_data = json.loads(clean_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SQL response: {response.content}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        
        return SQLQueryResult(
            sql=sql_data.get("sql", ""),
            query_type=sql_data.get("query_type", "unknown"),
            explanation=sql_data.get("explanation", ""),
            confidence=sql_data.get("confidence", 0.8)
        )
    
    def validate_sql_safety(self, sql: str) -> bool:
        """
        Validate SQL is safe to execute (read-only)
        
        Args:
            sql: SQL query string
        
        Returns:
            True if safe, False otherwise
        """
        sql_upper = sql.upper().strip()
        
        # Dangerous keywords that modify data
        dangerous_keywords = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
            "TRUNCATE", "CREATE", "GRANT", "REVOKE"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                logger.error(f"Unsafe SQL detected: contains '{keyword}'")
                return False
        
        # Must start with SELECT
        if not sql_upper.startswith("SELECT"):
            logger.error(f"SQL must start with SELECT, got: {sql_upper[:20]}")
            return False
        
        return True
    
    def generate_answer(
        self,
        user_query: str,
        sql_query: str,
        sql_results: List[Dict[str, Any]],
        source_documents: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate natural language answer from SQL results
        
        Args:
            user_query: Original question
            sql_query: Executed SQL
            sql_results: Query results
            source_documents: Source document metadata
        
        Returns:
            Natural language answer string
        """
        prompt = build_answer_generation_prompt(
            user_query=user_query,
            sql_query=sql_query,
            sql_results=sql_results,
            source_documents=source_documents
        )
        
        response = complete_with_fallback(
            system_prompt=SYSTEM_PROMPT_ANSWER_GENERATION,
            user_prompt=prompt,
            json_mode=False  # Free-form text answer
        )
        
        if response.error:
            logger.error(f"Answer generation failed: {response.error}")
            # Fallback: basic answer
            if not sql_results:
                return "No results found for your query."
            else:
                return f"Found {len(sql_results)} results. See the data table for details."
        
        return response.content.strip()
    
    def _get_source_documents(
        self,
        query_results: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Trace query results back to source documents
        
        Args:
            query_results: Results from SQL query
        
        Returns:
            List of source document metadata
        """
        # Extract any chunk IDs or entity IDs from results
        source_ids = set()
        
        for row in query_results:
            # Ensure row is a dict before accessing
            if not isinstance(row, dict):
                logger.warning(f"Unexpected row type in query results: {type(row)}, value: {row}")
                continue
            
            # Look for common provenance columns
            if "source_chunk_id" in row:
                source_ids.add(row["source_chunk_id"])
            if "chunk_id" in row:
                source_ids.add(row["chunk_id"])
        
        if not source_ids:
            return []
        
        # Query documents table for source info
        placeholders = ", ".join(["?"] * len(source_ids))
        query = f"""
        SELECT DISTINCT d.doc_id, d.filename, d.file_type
        FROM documents d
        JOIN chunks c ON d.doc_id = c.doc_id
        WHERE c.chunk_id IN ({placeholders})
        LIMIT 10
        """
        
        try:
            docs = self.db.execute_query(query, params=list(source_ids))
            return [
                {
                    "doc_id": doc["doc_id"],
                    "filename": doc["filename"],
                    "file_type": doc.get("file_type", "unknown")
                }
                for doc in docs
            ]
        except Exception as e:
            logger.warning(f"Failed to retrieve source documents: {str(e)}")
            return []
    
    def explain_query(self, query: str) -> Dict[str, Any]:
        """
        Explain how a query would be processed (without executing)
        
        Args:
            query: Natural language query
        
        Returns:
            Dict with classification, SQL, and explanation
        """
        metadata = self.classify_query(query)
        sql_result = self.translate_to_sql(query, metadata)
        
        return {
            "query": query,
            "classification": {
                "type": metadata.query_type,
                "complexity": metadata.complexity,
                "requires_join": metadata.requires_join,
                "confidence": metadata.confidence
            },
            "sql": {
                "query": sql_result.sql,
                "type": sql_result.query_type,
                "explanation": sql_result.explanation,
                "is_safe": self.validate_sql_safety(sql_result.sql),
                "confidence": sql_result.confidence
            }
        }
