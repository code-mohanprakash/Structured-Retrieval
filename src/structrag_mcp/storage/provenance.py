"""
Provenance Tracker for StructRAG MCP
Tracks sources and lineage of all extracted data and query results
"""
from typing import Dict, List, Optional
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)


class ProvenanceTracker:
    """Track data provenance and source attribution"""
    
    def __init__(self, db_manager):
        """
        Initialize provenance tracker
        
        Args:
            db_manager: DuckDBManager instance
        """
        self.db = db_manager
    
    def generate_query_id(self, question: str) -> str:
        """Generate unique query ID from question"""
        timestamp = datetime.now().isoformat()
        content = f"{question}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def generate_doc_id(self, filename: str, file_path: str) -> str:
        """Generate unique document ID"""
        content = f"{filename}_{file_path}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def generate_chunk_id(self, doc_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID"""
        return f"{doc_id}_chunk_{chunk_index}"
    
    def trace_query_sources(self, query_id: str) -> Dict[str, any]:
        """
        Trace all source documents for a query result
        
        Args:
            query_id: Query ID to trace
            
        Returns:
            Dict with provenance information
        """
        # Get query record
        query = self.db.execute_query(
            "SELECT * FROM query_provenance WHERE query_id = ?",
            [query_id]
        )
        
        if not query:
            return {"error": "Query not found"}
        
        query_record = query[0]
        
        # Parse source docs
        import json
        source_doc_ids = json.loads(query_record.get("source_docs", "[]"))
        
        # Get document details
        docs = []
        for doc_id in source_doc_ids:
            doc_info = self.db.execute_query(
                "SELECT * FROM documents WHERE doc_id = ?",
                [doc_id]
            )
            if doc_info:
                docs.append(doc_info[0])
        
        return {
            "query_id": query_id,
            "question": query_record["question"],
            "sql_executed": query_record["sql_executed"],
            "executed_at": query_record["executed_at"],
            "execution_time_ms": query_record["execution_time_ms"],
            "source_documents": docs,
            "document_count": len(docs)
        }
    
    def get_document_lineage(self, doc_id: str) -> Dict[str, any]:
        """
        Get complete lineage for a document
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dict with document lineage
        """
        # Get document
        doc = self.db.execute_query(
            "SELECT * FROM documents WHERE doc_id = ?",
            [doc_id]
        )
        
        if not doc:
            return {"error": "Document not found"}
        
        doc_record = doc[0]
        
        # Get all chunks
        chunks = self.db.execute_query(
            "SELECT chunk_id, chunk_index, token_count FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
            [doc_id]
        )
        
        # Get all queries that used this document
        queries = self.db.execute_query("""
            SELECT query_id, question, executed_at 
            FROM query_provenance 
            WHERE source_docs LIKE ?
            ORDER BY executed_at DESC
            LIMIT 20
        """, [f'%{doc_id}%'])
        
        return {
            "doc_id": doc_id,
            "filename": doc_record["filename"],
            "source_type": doc_record["source_type"],
            "ingested_at": doc_record["ingested_at"],
            "chunk_count": len(chunks),
            "chunks": chunks,
            "used_in_queries": queries,
            "query_count": len(queries)
        }
    
    def get_entity_provenance(
        self, 
        table_name: str, 
        entity_id: str
    ) -> Dict[str, any]:
        """
        Trace provenance of a specific entity
        
        Args:
            table_name: Entity table name
            entity_id: Entity ID
            
        Returns:
            Dict with entity provenance
        """
        # Get entity record (assumes primary key column name matches table_name + _id)
        id_column = f"{table_name}_id"
        
        try:
            entity = self.db.execute_query(
                f"SELECT * FROM {table_name} WHERE {id_column} = ?",
                [entity_id]
            )
            
            if not entity:
                return {"error": "Entity not found"}
            
            entity_record = entity[0]
            
            # Get source document
            doc_id = entity_record.get("doc_id")
            doc_info = None
            if doc_id:
                doc_info = self.db.execute_query(
                    "SELECT filename, source_type, ingested_at FROM documents WHERE doc_id = ?",
                    [doc_id]
                )
            
            return {
                "entity_type": table_name,
                "entity_id": entity_id,
                "entity_data": entity_record,
                "source_document": doc_info[0] if doc_info else None,
                "extracted_at": entity_record.get("extracted_at", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Error getting entity provenance: {e}")
            return {"error": str(e)}
    
    def get_audit_summary(self) -> Dict[str, any]:
        """Get overall audit summary"""
        doc_count = self.db.get_document_count()
        chunk_count = self.db.get_chunk_count()
        
        # Query stats
        query_stats = self.db.execute_query("""
            SELECT 
                COUNT(*) as total_queries,
                COUNT(CASE WHEN error IS NULL THEN 1 END) as successful_queries,
                AVG(execution_time_ms) as avg_execution_time_ms
            FROM query_provenance
        """)
        
        # Recent queries
        recent = self.db.execute_query("""
            SELECT query_id, question, executed_at, error IS NOT NULL as has_error
            FROM query_provenance
            ORDER BY executed_at DESC
            LIMIT 10
        """)
        
        return {
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "query_statistics": query_stats[0] if query_stats else {},
            "recent_queries": recent
        }
