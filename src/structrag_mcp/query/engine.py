"""
Query Engine

Handles natural language to SQL translation, execution, and answer generation.
Includes query classification, safety validation, and result formatting.

Implements S-RAG paper Section 3.3:
- Text-to-SQL translation with column statistics
- Hybrid inference mode for queries requiring document context
"""

import logging
import time
from typing import List, Dict, Any, Optional, Literal
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

# Inference modes per S-RAG paper Section 3.3
InferenceMode = Literal["structured", "hybrid"]


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
        
        # Step 7: Log query for audit (store doc IDs for provenance)
        source_doc_ids = [doc.get("doc_id") for doc in source_docs if doc.get("doc_id")]
        self.db.log_query(
            query_id=query_id,
            question=natural_language_query,
            sql=sql_result.sql,
            result=results,
            source_docs=source_doc_ids,
            execution_time_ms=execution_time_ms,
            error=None
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
        
        Per S-RAG paper Section 3.3: "To enhance the quality of the generated 
        query and avoid ambiguity, the LLM receives as input the query q, 
        the schema S and statistics for every column in the DB."
        
        Args:
            natural_language_query: User's question
            query_metadata: Optional pre-classified metadata
        
        Returns:
            SQLQueryResult with generated SQL
        """
        # Get available tables and schemas
        tables = self.db.list_tables()
        table_schemas = {}
        column_statistics = {}
        
        # Filter to entity tables (exclude system tables)
        entity_tables = [t for t in tables if t not in 
                        ['documents', 'chunks', 'query_provenance', 'schema_registry']]
        
        for table in entity_tables:
            schema = self.db.get_table_schema(table)
            if schema:
                # Convert to list of dicts format expected by prompt builder
                table_schemas[table] = [
                    {"name": col_name, "type": col_type}
                    for col_name, col_type in schema.items()
                ]
                
                # Get column statistics (S-RAG paper Section 3.3)
                try:
                    stats_str = self.db.format_statistics_for_prompt(table)
                    column_statistics[table] = stats_str
                except Exception as e:
                    logger.warning(f"Could not compute statistics for {table}: {e}")
        
        prompt = build_query_translation_prompt(
            natural_language_query=natural_language_query,
            available_tables=entity_tables,
            table_schemas=table_schemas,
            column_statistics=column_statistics if column_statistics else None
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
        
        # Dangerous keywords that modify data (match whole words)
        import re
        dangerous_keywords = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
            "TRUNCATE", "CREATE", "GRANT", "REVOKE"
        ]
        pattern = r"\b(" + "|".join(dangerous_keywords) + r")\b"
        if re.search(pattern, sql_upper):
            logger.error("Unsafe SQL detected: contains data-modifying keyword")
            return False
        
        # Must start with SELECT or WITH (CTE)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            logger.error(f"SQL must start with SELECT/WITH, got: {sql_upper[:20]}")
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
        SELECT DISTINCT d.doc_id, d.filename, d.source_type
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
                    "file_type": doc.get("source_type", "unknown")
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
    
    # ========================================================================
    # HYBRID INFERENCE MODE (S-RAG Paper Section 3.3)
    # ========================================================================
    
    def query_hybrid(
        self,
        natural_language_query: str,
        max_documents: int = 10,
        format: str = "markdown"
    ) -> QueryExecutionResult:
        """
        Execute query in hybrid mode (S-RAG + classic RAG).
        
        Per S-RAG paper Section 3.3: "When the predicted schema fails to 
        capture certain attributes, particularly rare ones, the answer to 
        a free-text query cannot be derived directly from the SQL table. 
        In such cases, we view our system as an effective mechanism for 
        narrowing a large corpus to a smaller set of documents from which 
        the answer can be inferred."
        
        HYBRID-S-RAG operates in two steps:
        1. Translate query to SQL that returns document IDs (filtering)
        2. Apply classic RAG on the filtered document subset
        
        Args:
            natural_language_query: User's question
            max_documents: Maximum documents to retrieve for RAG
            format: Output format
        
        Returns:
            QueryExecutionResult with answer from hybrid approach
        """
        start_time = time.time()
        query_id = self.provenance.generate_query_id(natural_language_query)
        
        logger.info(f"Hybrid query [{query_id}]: {natural_language_query}")
        
        # Step 1: Generate filtering SQL that returns document IDs
        filter_sql = self._generate_filter_sql(natural_language_query)
        
        if not filter_sql:
            logger.warning("Could not generate filter SQL, falling back to full corpus")
            doc_ids = self._get_all_document_ids()[:max_documents]
        else:
            try:
                # Execute filter to get document subset
                filter_results = self.db.execute_query(filter_sql)
                doc_ids = self._extract_doc_ids_from_results(filter_results)
                logger.info(f"Filter SQL returned {len(doc_ids)} documents")
            except Exception as e:
                logger.warning(f"Filter SQL failed: {e}, using all documents")
                doc_ids = self._get_all_document_ids()[:max_documents]
        
        # Limit documents
        doc_ids = doc_ids[:max_documents]
        
        if not doc_ids:
            return QueryExecutionResult(
                query_id=query_id,
                original_query=natural_language_query,
                sql_executed=filter_sql or "N/A",
                results=[],
                result_count=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                answer="No relevant documents found for your query.",
                source_documents=[],
                confidence=0.0
            )
        
        # Step 2: Get document texts for RAG
        document_texts = self._get_document_texts(doc_ids)
        
        # Step 3: Generate answer using document context
        answer = self._generate_rag_answer(
            question=natural_language_query,
            documents=document_texts
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Get source document metadata
        source_docs = self._get_document_metadata(doc_ids)
        
        result = QueryExecutionResult(
            query_id=query_id,
            original_query=natural_language_query,
            sql_executed=filter_sql or "HYBRID_RAG",
            results=[{"answer": answer}],
            result_count=len(doc_ids),
            execution_time_ms=execution_time_ms,
            answer=answer,
            source_documents=source_docs,
            confidence=0.8  # Hybrid mode confidence
        )
        
        logger.info(f"Hybrid query complete: {len(doc_ids)} docs, {execution_time_ms:.0f}ms")
        
        return result
    
    def _generate_filter_sql(self, query: str) -> Optional[str]:
        """Generate SQL that filters and returns document IDs"""
        
        prompt = f"""You are a SQL expert. Generate a DuckDB SQL query that filters documents 
based on the user's question and returns document IDs.

**User Question**: {query}

**Instructions**:
1. Generate SQL that SELECTs doc_id from the relevant entity table
2. Apply WHERE clauses based on the query's filtering criteria
3. The goal is to narrow down to a subset of relevant documents
4. Return ONLY doc_id column

**Output Format** (valid JSON):
{{
  "sql": "SELECT DISTINCT doc_id FROM ... WHERE ...",
  "explanation": "Brief explanation"
}}

Return ONLY the JSON, no additional text."""
        
        try:
            response = complete_with_fallback(
                system_prompt=SYSTEM_PROMPT_QUERY_TRANSLATION,
                user_prompt=prompt,
                json_mode=True
            )
            
            if response.error:
                return None
            
            clean_content = _strip_markdown_json(response.content)
            sql_data = json.loads(clean_content)
            return sql_data.get("sql")
            
        except Exception as e:
            logger.error(f"Failed to generate filter SQL: {e}")
            return None
    
    def _extract_doc_ids_from_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract document IDs from query results"""
        doc_ids = []
        for row in results:
            if isinstance(row, dict):
                doc_id = row.get("doc_id") or row.get("document_id") or row.get("id")
                if doc_id:
                    doc_ids.append(str(doc_id))
        return doc_ids
    
    def _get_all_document_ids(self) -> List[str]:
        """Get all document IDs from corpus"""
        try:
            results = self.db.execute_query("SELECT DISTINCT doc_id FROM documents LIMIT 100")
            return [row["doc_id"] for row in results]
        except:
            return []
    
    def _get_document_texts(self, doc_ids: List[str]) -> List[Dict[str, str]]:
        """Get document texts for RAG context"""
        documents = []
        
        for doc_id in doc_ids:
            try:
                # Get chunks for this document
                results = self.db.execute_query(
                    "SELECT text FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
                    params=[doc_id]
                )
                
                if results:
                    full_text = "\n\n".join([r["text"] for r in results if r.get("text")])
                    documents.append({
                        "doc_id": doc_id,
                        "text": full_text[:5000]  # Limit text length
                    })
            except Exception as e:
                logger.warning(f"Failed to get text for {doc_id}: {e}")
        
        return documents
    
    def _get_document_metadata(self, doc_ids: List[str]) -> List[Dict[str, str]]:
        """Get document metadata for provenance"""
        if not doc_ids:
            return []
        
        placeholders = ", ".join(["?"] * len(doc_ids))
        try:
            results = self.db.execute_query(
                f"SELECT doc_id, filename, source_type FROM documents WHERE doc_id IN ({placeholders})",
                params=doc_ids
            )
            return [
                {
                    "doc_id": r["doc_id"],
                    "filename": r.get("filename", "Unknown"),
                    "file_type": r.get("source_type", "unknown")
                }
                for r in results
            ]
        except:
            return []
    
    def _generate_rag_answer(
        self,
        question: str,
        documents: List[Dict[str, str]]
    ) -> str:
        """Generate answer using RAG with document context"""
        
        # Build context from documents
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"[Document {i}]\n{doc['text']}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        prompt = f"""Answer the user's question based ONLY on the provided documents.

**Question**: {question}

**Documents**:
{context[:15000]}

**Instructions**:
1. Answer based only on information in the documents
2. If the answer cannot be found, say so
3. Cite document numbers when possible (e.g., [1], [2])
4. Be concise and direct

Answer:"""
        
        response = complete_with_fallback(
            system_prompt=SYSTEM_PROMPT_ANSWER_GENERATION,
            user_prompt=prompt,
            json_mode=False
        )
        
        if response.error:
            return f"Error generating answer: {response.error}"
        
        return response.content.strip()
