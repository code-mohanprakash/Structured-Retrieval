"""
DuckDB Storage Manager for StructRAG MCP

Handles all database operations including schema creation and querying.

Implements S-RAG paper Section 3.2.2 and Appendix D:
- Post-prediction processing to compute attribute-level statistics
- Statistics for numeric: mean, max, min, non-null count
- Statistics for string/boolean: unique values, most common values
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
import duckdb
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class DuckDBManager:
    """Manage DuckDB database for structured data storage"""
    
    def __init__(self, db_path: str = "./data/structrag.db"):
        """
        Initialize DuckDB connection
        
        Args:
            db_path: Path to DuckDB file (or :memory: for in-memory)
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._initialize_core_tables()
        logger.info(f"DuckDB initialized at {db_path}")
    
    def _initialize_core_tables(self):
        """Create core metadata tables"""
        # Documents table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id VARCHAR PRIMARY KEY,
                filename VARCHAR,
                source_type VARCHAR,
                file_size BIGINT,
                ingested_at TIMESTAMP,
                chunk_count INTEGER,
                metadata JSON
            )
        """)
        
        # Chunks table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id VARCHAR PRIMARY KEY,
                doc_id VARCHAR,
                chunk_index INTEGER,
                text TEXT,
                token_count INTEGER,
                metadata JSON,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)
        
        # Query provenance table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS query_provenance (
                query_id VARCHAR PRIMARY KEY,
                question TEXT,
                sql_executed TEXT,
                result_json JSON,
                source_docs JSON,
                executed_at TIMESTAMP,
                execution_time_ms REAL,
                error TEXT
            )
        """)
        
        # Schema registry (tracks dynamically created tables)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_registry (
                table_name VARCHAR PRIMARY KEY,
                entity_type VARCHAR,
                schema_json JSON,
                created_at TIMESTAMP,
                confidence REAL
            )
        """)
        
        self.conn.commit()
        logger.info("Core tables initialized")
    
    def insert_document(
        self, 
        doc_id: str,
        filename: str,
        file_path: str = None,
        file_type: str = None,
        source_type: str = None,
        file_size: int = 0,
        chunk_count: int = 0,
        metadata: Dict = None
    ):
        """Insert document metadata"""
        # Use file_type or source_type
        doc_type = file_type or source_type or "unknown"
        meta = metadata or {}
        
        self.conn.execute("""
            INSERT INTO documents (doc_id, filename, source_type, file_size, ingested_at, chunk_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            doc_id,
            filename,
            doc_type,
            file_size,
            datetime.now(),
            chunk_count,
            json.dumps(meta)
        ])
        self.conn.commit()
    
    def insert_chunks(self, chunks: List[Dict[str, Any]]):
        """Batch insert chunks"""
        for chunk in chunks:
            self.conn.execute("""
                INSERT INTO chunks (chunk_id, doc_id, chunk_index, text, token_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                chunk["chunk_id"],
                chunk["doc_id"],
                chunk["chunk_index"],
                chunk["text"],
                chunk["token_count"],
                json.dumps(chunk.get("metadata", {}))
            ])
        self.conn.commit()
        logger.info(f"Inserted {len(chunks)} chunks")
    
    def create_table_from_schema(self, table_name: str, schema: Dict[str, str]):
        """
        Create a table from schema definition
        
        Args:
            table_name: Name of table to create
            schema: Dict mapping column names to SQL types
        """
        # Build CREATE TABLE statement
        columns = []
        for col_name, col_type in schema.items():
            columns.append(f"{col_name} {col_type}")
        
        # Add doc_id for provenance
        if "doc_id" not in schema:
            columns.append("doc_id VARCHAR")
        
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        
        try:
            self.conn.execute(sql)
            self.conn.commit()
            
            # Register in schema registry
            self.conn.execute("""
                INSERT OR REPLACE INTO schema_registry (table_name, entity_type, schema_json, created_at, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, [
                table_name,
                table_name,  # entity_type same as table_name for now
                json.dumps(schema),
                datetime.now(),
                1.0  # Full confidence for user-created schemas
            ])
            self.conn.commit()
            
            logger.info(f"Created table: {table_name}")
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise
    
    def execute_query(
        self, 
        sql: str, 
        params: Optional[List] = None,
        timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query with timeout
        
        Args:
            sql: SQL query string
            params: Query parameters
            timeout: Timeout in seconds (not enforced by DuckDB)
            
        Returns:
            List of result dictionaries
        """
        try:
            # Note: DuckDB doesn't support statement_timeout, 
            # timeout parameter is kept for API compatibility
            
            if params:
                result = self.conn.execute(sql, params)
            else:
                result = self.conn.execute(sql)
            
            # Convert to list of dicts
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def log_query(
        self,
        query_id: str,
        question: str,
        sql: str,
        result: Any,
        source_docs: List[str],
        execution_time_ms: float,
        error: Optional[str] = None
    ):
        """Log query execution for audit trail"""
        self.conn.execute("""
            INSERT INTO query_provenance 
            (query_id, question, sql_executed, result_json, source_docs, executed_at, execution_time_ms, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            query_id,
            question,
            sql,
            json.dumps(result) if result else None,
            json.dumps(source_docs),
            datetime.now(),
            execution_time_ms,
            error
        ])
        self.conn.commit()
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """Get schema for a table"""
        result = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
        return {row[0]: row[1] for row in result}
    
    def list_tables(self) -> List[str]:
        """List all tables in database"""
        result = self.conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND table_type = 'BASE TABLE'
        """).fetchall()
        return [row[0] for row in result]

    def update_document_chunk_count(self, doc_id: str, chunk_count: int) -> None:
        """Update chunk count for a document"""
        self.conn.execute("""
            UPDATE documents
            SET chunk_count = ?
            WHERE doc_id = ?
        """, [chunk_count, doc_id])
        self.conn.commit()
    
    def get_document_count(self) -> int:
        """Get total document count"""
        result = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        return result[0] if result else 0
    
    def get_chunk_count(self) -> int:
        """Get total chunk count"""
        result = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
        return result[0] if result else 0
    
    # ========================================================================
    # COLUMN STATISTICS (S-RAG Paper Section 3.2.2 and Appendix D)
    # ========================================================================
    
    def compute_column_statistics(self, table_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Compute attribute-level statistics for a table.
        
        Per S-RAG paper Appendix D: "After applying record prediction to all 
        documents in the corpus, we compute attribute-level statistics. For 
        numeric attributes, we calculate the mean, maximum, and minimum values; 
        for string and boolean attributes, we include the set of unique values 
        predicted by the LLM. For all attributes, regardless of type, we also 
        include the number of non-zero and non-null values."
        
        These statistics are used at inference time to guide text-to-SQL.
        
        Args:
            table_name: Name of the table to analyze
        
        Returns:
            Dict mapping column names to their statistics
        """
        statistics = {}
        
        # Get column info
        schema = self.get_table_schema(table_name)
        
        for col_name, col_type in schema.items():
            col_stats = self._compute_single_column_stats(table_name, col_name, col_type)
            statistics[col_name] = col_stats
        
        logger.info(f"Computed statistics for {len(statistics)} columns in {table_name}")
        return statistics
    
    def _compute_single_column_stats(
        self, 
        table_name: str, 
        col_name: str, 
        col_type: str
    ) -> Dict[str, Any]:
        """Compute statistics for a single column"""
        stats = {
            "column_name": col_name,
            "column_type": col_type
        }
        
        try:
            # Non-null count (for all types)
            result = self.conn.execute(f"""
                SELECT 
                    COUNT(*) as total_count,
                    COUNT({col_name}) as non_null_count
                FROM {table_name}
            """).fetchone()
            
            stats["total_count"] = result[0]
            stats["non_null_count"] = result[1]
            stats["null_count"] = result[0] - result[1]
            
            # Type-specific statistics
            col_type_upper = col_type.upper()
            
            if any(t in col_type_upper for t in ['INT', 'REAL', 'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC']):
                # Numeric column statistics
                numeric_stats = self._compute_numeric_stats(table_name, col_name)
                stats.update(numeric_stats)
                
            elif 'BOOL' in col_type_upper:
                # Boolean column statistics
                bool_stats = self._compute_boolean_stats(table_name, col_name)
                stats.update(bool_stats)
                
            else:
                # String/text column statistics
                string_stats = self._compute_string_stats(table_name, col_name)
                stats.update(string_stats)
                
        except Exception as e:
            logger.warning(f"Error computing stats for {col_name}: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def _compute_numeric_stats(self, table_name: str, col_name: str) -> Dict[str, Any]:
        """Compute statistics for numeric columns"""
        result = self.conn.execute(f"""
            SELECT 
                AVG({col_name}) as mean_value,
                MAX({col_name}) as max_value,
                MIN({col_name}) as min_value,
                COUNT(CASE WHEN {col_name} != 0 THEN 1 END) as non_zero_count
            FROM {table_name}
            WHERE {col_name} IS NOT NULL
        """).fetchone()
        
        return {
            "mean": result[0],
            "max": result[1],
            "min": result[2],
            "non_zero_count": result[3]
        }
    
    def _compute_boolean_stats(self, table_name: str, col_name: str) -> Dict[str, Any]:
        """Compute statistics for boolean columns"""
        result = self.conn.execute(f"""
            SELECT 
                {col_name},
                COUNT(*) as count
            FROM {table_name}
            WHERE {col_name} IS NOT NULL
            GROUP BY {col_name}
        """).fetchall()
        
        value_counts = {str(row[0]): row[1] for row in result}
        
        return {
            "unique_values": list(value_counts.keys()),
            "value_counts": value_counts,
            "true_count": value_counts.get("true", value_counts.get("True", 0)),
            "false_count": value_counts.get("false", value_counts.get("False", 0))
        }
    
    def _compute_string_stats(self, table_name: str, col_name: str, max_unique: int = 50) -> Dict[str, Any]:
        """
        Compute statistics for string/text columns
        
        Args:
            table_name: Table name
            col_name: Column name
            max_unique: Maximum unique values to return (prevent memory issues)
        """
        # Get unique values count
        unique_count_result = self.conn.execute(f"""
            SELECT COUNT(DISTINCT {col_name}) as unique_count
            FROM {table_name}
            WHERE {col_name} IS NOT NULL
        """).fetchone()
        
        unique_count = unique_count_result[0]
        
        # Get most common values
        common_values_result = self.conn.execute(f"""
            SELECT {col_name}, COUNT(*) as count
            FROM {table_name}
            WHERE {col_name} IS NOT NULL
            GROUP BY {col_name}
            ORDER BY count DESC
            LIMIT {max_unique}
        """).fetchall()
        
        unique_values = [row[0] for row in common_values_result]
        value_counts = {row[0]: row[1] for row in common_values_result}
        
        return {
            "unique_count": unique_count,
            "unique_values": unique_values[:max_unique],
            "value_counts": value_counts,
            "most_common": unique_values[0] if unique_values else None
        }
    
    def get_all_table_statistics(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Compute statistics for all entity tables in the database.
        
        Returns:
            Dict mapping table names to their column statistics
        """
        all_stats = {}
        
        # Get entity tables from schema registry
        try:
            result = self.conn.execute("""
                SELECT table_name FROM schema_registry
            """).fetchall()
            
            entity_tables = [row[0] for row in result]
        except:
            # Fallback: get all non-system tables
            entity_tables = self.list_tables()
            entity_tables = [t for t in entity_tables if t not in 
                           ['documents', 'chunks', 'query_provenance', 'schema_registry']]
        
        for table_name in entity_tables:
            try:
                all_stats[table_name] = self.compute_column_statistics(table_name)
            except Exception as e:
                logger.warning(f"Error computing statistics for {table_name}: {e}")
        
        return all_stats
    
    def format_statistics_for_prompt(self, table_name: str) -> str:
        """
        Format column statistics as text for inclusion in LLM prompts.
        
        Per S-RAG paper Section 3.3: "These statistics guide the LLM in 
        mapping the semantic meaning of q to the appropriate lexical 
        filters or values in the formal query."
        
        Args:
            table_name: Table name
        
        Returns:
            Formatted string describing column statistics
        """
        stats = self.compute_column_statistics(table_name)
        
        lines = [f"Column Statistics for table '{table_name}':", ""]
        
        for col_name, col_stats in stats.items():
            col_type = col_stats.get("column_type", "unknown")
            non_null = col_stats.get("non_null_count", 0)
            total = col_stats.get("total_count", 0)
            
            line = f"- {col_name} ({col_type}): {non_null}/{total} non-null values"
            
            # Add type-specific info
            if "mean" in col_stats:
                mean = col_stats["mean"]
                min_val = col_stats["min"]
                max_val = col_stats["max"]
                if mean is not None:
                    line += f", range [{min_val} - {max_val}], mean {mean:.2f}"
            elif "unique_values" in col_stats:
                unique_vals = col_stats["unique_values"][:10]  # Limit for prompt
                if unique_vals:
                    line += f", values: {unique_vals}"
            
            lines.append(line)
        
        return "\n".join(lines)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")
