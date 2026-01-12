"""
StructRAG MCP Server

FastMCP server exposing 6 tools for structured RAG:
1. ingest_corpus - Ingest documents into the system
2. build_structure - Induce schema from documents
3. explain_schema - Describe discovered schema
4. query_structured - Query data with natural language
5. query_hybrid - Hybrid structured + semantic search (future)
6. audit - View query provenance and system stats
"""

import logging
import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from mcp.server.fastmcp import FastMCP

from .ingestion import PDFParser, CSVParser, TextParser, SemanticChunker, MetadataExtractor
from .storage import DuckDBManager, ProvenanceTracker
from .structure import SchemaInductor, EntityExtractor
from .query import QueryEngine
from .structure.models import IngestionSummary, AuditSummary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("StructRAG")

# Global state (initialized on first tool call)
_db_manager: Optional[DuckDBManager] = None
_provenance: Optional[ProvenanceTracker] = None
_schema_inductor: Optional[SchemaInductor] = None
_entity_extractor: Optional[EntityExtractor] = None
_query_engine: Optional[QueryEngine] = None


def get_db_manager() -> DuckDBManager:
    """Get or create DuckDB manager instance"""
    global _db_manager
    if _db_manager is None:
        db_path = os.getenv("DUCKDB_PATH", "./data/structrag.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _db_manager = DuckDBManager(db_path)
        logger.info(f"Initialized DuckDB at {db_path}")
    return _db_manager


def get_provenance() -> ProvenanceTracker:
    """Get or create provenance tracker"""
    global _provenance
    if _provenance is None:
        _provenance = ProvenanceTracker(get_db_manager())
    return _provenance


def get_schema_inductor() -> SchemaInductor:
    """Get or create schema inductor"""
    global _schema_inductor
    if _schema_inductor is None:
        _schema_inductor = SchemaInductor(get_db_manager())
    return _schema_inductor


def get_entity_extractor() -> EntityExtractor:
    """Get or create entity extractor"""
    global _entity_extractor
    if _entity_extractor is None:
        _entity_extractor = EntityExtractor(get_db_manager(), get_provenance())
    return _entity_extractor


def get_query_engine() -> QueryEngine:
    """Get or create query engine"""
    global _query_engine
    if _query_engine is None:
        _query_engine = QueryEngine(get_db_manager(), get_provenance())
    return _query_engine


@mcp.tool()
def ingest_corpus(input_path: str) -> str:
    """
    Ingest documents from a directory or file into StructRAG.
    
    Supports: PDF, CSV, TSV, TXT, Markdown, JSON
    
    Args:
        input_path: Path to file or directory containing documents
    
    Returns:
        Ingestion summary with statistics
    """
    logger.info(f"Starting ingestion from: {input_path}")
    
    path = Path(input_path)
    if not path.exists():
        return f"Error: Path does not exist: {input_path}"
    
    # Initialize components
    db = get_db_manager()
    provenance = get_provenance()
    chunker = SemanticChunker()
    
    # Collect files
    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob("*"))
        files = [f for f in files if f.is_file()]
    
    logger.info(f"Found {len(files)} files to process")
    
    # Track statistics
    total_files = len(files)
    files_processed = 0
    files_failed = 0
    total_chunks = 0
    total_tokens = 0
    parsers_used = {}
    errors = []
    
    import time
    start_time = time.time()
    
    for file_path in files:
        try:
            # Select parser based on extension
            ext = file_path.suffix.lower()
            
            if ext == ".pdf":
                parser = PDFParser()
                parser_name = "PDF"
            elif ext in [".csv", ".tsv"]:
                parser = CSVParser()
                parser_name = "CSV"
            elif ext in [".txt", ".md", ".markdown", ".json"]:
                parser = TextParser()
                parser_name = "Text"
            else:
                logger.warning(f"Unsupported file type: {ext}, skipping {file_path.name}")
                continue
            
            # Parse document
            parsed = parser.parse(str(file_path))
            
            # Extract metadata
            metadata_extractor = MetadataExtractor()
            file_metadata = metadata_extractor.extract_file_metadata(str(file_path))
            metadata = {**parsed.get("metadata", {}), **file_metadata}
            
            # Generate document ID
            doc_id = provenance.generate_doc_id(file_path.name, str(file_path))
            
            # Insert document
            db.insert_document(
                doc_id=doc_id,
                filename=file_path.name,
                file_path=str(file_path),
                file_type=ext,
                metadata=metadata
            )
            
            # Chunk text
            chunks = chunker.chunk(parsed["text"], metadata)
            
            # Insert chunks
            for chunk in chunks:
                chunk_id = provenance.generate_chunk_id(doc_id, chunk["chunk_index"])
                db.insert_chunks([{
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "token_count": chunk["token_count"],
                    "metadata": chunk.get("metadata", {})
                }])
                total_tokens += chunk["token_count"]
            
            total_chunks += len(chunks)
            files_processed += 1
            parsers_used[parser_name] = parsers_used.get(parser_name, 0) + 1
            
            logger.info(f"✓ Processed {file_path.name}: {len(chunks)} chunks, {total_tokens} tokens")
        
        except Exception as e:
            logger.error(f"✗ Failed to process {file_path.name}: {str(e)}")
            files_failed += 1
            errors.append(f"{file_path.name}: {str(e)}")
    
    processing_time = time.time() - start_time
    
    summary = IngestionSummary(
        corpus_path=input_path,
        total_files=total_files,
        files_processed=files_processed,
        files_failed=files_failed,
        total_chunks=total_chunks,
        total_tokens=total_tokens,
        parsers_used=parsers_used,
        processing_time_seconds=processing_time,
        errors=errors[:10]  # Limit to 10 errors
    )
    
    result = f"""# Ingestion Complete

**Source**: {input_path}
**Files**: {files_processed}/{total_files} processed ({files_failed} failed)
**Chunks**: {total_chunks:,}
**Tokens**: {total_tokens:,}
**Time**: {processing_time:.1f}s

**Parsers Used**:
"""
    for parser, count in parsers_used.items():
        result += f"- {parser}: {count} files\n"
    
    if errors:
        result += f"\n**Errors** ({len(errors)}):\n"
        for err in errors[:5]:
            result += f"- {err}\n"
    
    return result


@mcp.tool()
def build_structure(entity_hints: List[str], max_samples: int = 10) -> str:
    """
    Induce structured schema from documents using LLM analysis.
    
    Args:
        entity_hints: Entity types to discover (e.g., ["Deal", "Company", "Person"])
        max_samples: Number of documents to analyze (default: 10)
    
    Returns:
        Discovered schema with entity definitions
    """
    logger.info(f"Building structure for entities: {entity_hints}")
    
    try:
        inductor = get_schema_inductor()
        
        # Induce schema
        result = inductor.induce_schema(
            entity_hints=entity_hints,
            max_samples=max_samples,
            min_confidence=0.7
        )
        
        # Create tables in DuckDB
        inductor.create_tables_from_schema(result)
        
        # Extract entities from corpus
        extractor = get_entity_extractor()
        
        for entity_schema in result.entities:
            logger.info(f"Extracting {entity_schema.name} entities from corpus...")
            
            extraction_results = extractor.extract_from_corpus(
                entity_schema=entity_schema,
                batch_size=10,
                min_confidence=0.7
            )
            
            # Flatten all entities
            all_entities = []
            for ext_result in extraction_results:
                all_entities.extend(ext_result.entities)
            
            # Store in database
            if all_entities:
                extractor.store_entities(entity_schema, all_entities)
        
        # Format response
        response = f"""# Schema Induction Complete

**Entities Discovered**: {len(result.entities)}
**Documents Analyzed**: {result.total_documents_analyzed}
**Model**: {result.llm_model}
**Tokens Used**: {result.llm_tokens_used:,}

## Entity Schemas

"""
        
        for entity in result.entities:
            response += f"### {entity.name}\n\n"
            response += f"**Table**: `{entity.table_name}`\n\n"
            response += "**Attributes**:\n"
            for attr in entity.attributes:
                pk_marker = " 🔑" if attr.is_primary_key else ""
                response += f"- `{attr.name}` ({attr.type}) - confidence: {attr.confidence:.2f}{pk_marker}\n"
            
            if entity.relationships:
                response += "\n**Relationships**:\n"
                for rel in entity.relationships:
                    response += f"- {rel.relationship_type} → {rel.to_entity} (FK: {rel.foreign_key})\n"
            
            response += "\n"
        
        return response
    
    except Exception as e:
        logger.error(f"Schema induction failed: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@mcp.tool()
def explain_schema() -> str:
    """
    Explain the current database schema and available entities.
    
    Returns:
        Human-readable schema documentation
    """
    logger.info("Explaining schema")
    
    try:
        db = get_db_manager()
        inductor = get_schema_inductor()
        
        # Get all schemas from registry
        schemas = inductor.list_all_schemas()
        
        if not schemas:
            return "No schema defined yet. Use `build_structure` to induce schema from documents."
        
        response = f"""# Database Schema

**Total Entities**: {len(schemas)}

"""
        
        for schema in schemas:
            # Get row count from table
            try:
                count_result = db.execute_query(f"SELECT COUNT(*) as count FROM {schema.table_name}")
                row_count = count_result[0]["count"] if count_result else 0
            except:
                row_count = 0
            
            response += f"## {schema.name}\n\n"
            response += f"**Table**: `{schema.table_name}` ({row_count:,} rows)\n\n"
            
            response += "**Columns**:\n\n"
            response += "| Column | Type | Nullable | Notes |\n"
            response += "|--------|------|----------|-------|\n"
            
            for attr in schema.attributes:
                nullable = "Yes" if attr.is_nullable else "No"
                notes = "Primary Key" if attr.is_primary_key else f"Confidence: {attr.confidence:.0%}"
                response += f"| `{attr.name}` | {attr.type} | {nullable} | {notes} |\n"
            
            if schema.relationships:
                response += "\n**Relationships**:\n"
                for rel in schema.relationships:
                    response += f"- {rel.relationship_type} → `{rel.to_entity}` via `{rel.foreign_key}`\n"
            
            response += "\n---\n\n"
        
        # Add system tables info
        response += "## System Tables\n\n"
        response += "- `documents` - Ingested document metadata\n"
        response += "- `chunks` - Document chunks for RAG\n"
        response += "- `query_provenance` - Query audit trail\n"
        response += "- `schema_registry` - Schema definitions\n"
        
        return response
    
    except Exception as e:
        logger.error(f"Schema explanation failed: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@mcp.tool()
def query_structured(nl_query: str, format: str = "markdown") -> str:
    """
    Query the structured data using natural language.
    
    Args:
        nl_query: Natural language question (e.g., "How many deals closed last month?")
        format: Output format - "markdown" (default), "json", or "table"
    
    Returns:
        Query results with natural language answer and source citations
    """
    logger.info(f"Executing structured query: {nl_query}")
    
    try:
        engine = get_query_engine()
        
        # Execute query
        result = engine.query(nl_query, format=format)
        
        # Format based on requested format
        if format == "json":
            return result.model_dump_json(indent=2)
        elif format == "table":
            # Simple table format
            if not result.results:
                return "No results found."
            
            columns = list(result.results[0].keys())
            output = " | ".join(columns) + "\n"
            output += "-" * (len(output) - 1) + "\n"
            for row in result.results[:50]:
                output += " | ".join([str(row.get(col, "")) for col in columns]) + "\n"
            return output
        else:
            # Markdown format (default)
            return result.to_markdown()
    
    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        return f"Error executing query: {str(e)}"


@mcp.tool()
def audit(query_id: Optional[str] = None) -> str:
    """
    View query provenance and system audit information.
    
    Args:
        query_id: Optional specific query ID to audit. If None, returns system summary.
    
    Returns:
        Audit information with data lineage
    """
    logger.info(f"Audit request: {query_id or 'system summary'}")
    
    try:
        provenance = get_provenance()
        db = get_db_manager()
        
        if query_id:
            # Audit specific query
            sources = provenance.trace_query_sources(query_id)
            
            if not sources:
                return f"Query ID not found: {query_id}"
            
            response = f"# Query Audit: {query_id}\n\n"
            response += f"**Sources**: {len(sources)} documents\n\n"
            
            for source in sources[:10]:
                response += f"- **{source.get('filename', 'Unknown')}** (ID: {source.get('doc_id', 'N/A')})\n"
                response += f"  - Chunks: {source.get('chunks_used', 'N/A')}\n"
            
            return response
        
        else:
            # System-wide audit summary
            summary = provenance.get_audit_summary()
            
            response = f"""# System Audit Summary

## Storage Statistics
- **Documents**: {summary.get('total_documents', 0):,}
- **Chunks**: {summary.get('total_chunks', 0):,}
- **Queries Executed**: {summary.get('total_queries', 0):,}

## Entity Tables
"""
            
            for table in summary.get('entity_tables', []):
                try:
                    count_result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                    count = count_result[0]["count"] if count_result else 0
                    response += f"- `{table}`: {count:,} rows\n"
                except:
                    response += f"- `{table}`: Error reading count\n"
            
            response += "\n## Recent Activity\n"
            
            recent_queries = db.execute_query("""
                SELECT query_text, query_type, result_count, created_at
                FROM query_provenance
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            if recent_queries:
                response += "\n| Query | Type | Results | Time |\n"
                response += "|-------|------|---------|------|\n"
                for q in recent_queries:
                    query_text = q.get('query_text', '')[:50]
                    response += f"| {query_text} | {q.get('query_type', 'N/A')} | {q.get('result_count', 0)} | {q.get('created_at', 'N/A')} |\n"
            else:
                response += "*No queries executed yet*\n"
            
            return response
    
    except Exception as e:
        logger.error(f"Audit failed: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


# Note: query_hybrid will be implemented in future with ChromaDB integration
# For MVP, we focus on structured queries only

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
