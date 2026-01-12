"""
DuckDB Storage Manager for StructRAG MCP
Handles all database operations including schema creation and querying
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
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """).fetchall()
        return [row[0] for row in result]
    
    def get_document_count(self) -> int:
        """Get total document count"""
        result = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        return result[0] if result else 0
    
    def get_chunk_count(self) -> int:
        """Get total chunk count"""
        result = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
        return result[0] if result else 0
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")
