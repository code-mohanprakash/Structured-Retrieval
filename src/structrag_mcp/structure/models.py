"""
Schema Validation using Pydantic Models

Type-safe data models for:
- Entity schemas
- Field definitions
- Schema induction results
- Query metadata
- Entity instances
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class FieldDefinition(BaseModel):
    """Definition of a single field/attribute in an entity schema
    
    Per S-RAG paper Section 3.2.1: Each attribute should include name, type,
    description, and example values to guide LLM lexicalization.
    """
    name: str = Field(..., description="Field name (snake_case)")
    type: Literal["TEXT", "INTEGER", "REAL", "DATE", "BOOLEAN", "JSON"] = Field(
        ..., description="DuckDB data type"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    is_primary_key: bool = Field(default=False, description="Whether this is the primary key")
    is_nullable: bool = Field(default=True, description="Whether this field can be null")
    description: Optional[str] = Field(None, description="Human-readable field description")
    examples: List[str] = Field(
        default_factory=list, 
        description="Example values for cross-document standardization (S-RAG paper Section 3.2.1)"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure field name is valid SQL identifier"""
        if not v or not v.replace("_", "").isalnum():
            raise ValueError(f"Invalid field name: {v}")
        if v[0].isdigit():
            raise ValueError(f"Field name cannot start with digit: {v}")
        return v.lower()


class EntityRelationship(BaseModel):
    """Relationship between two entities (foreign key)"""
    to_entity: str = Field(..., description="Target entity name")
    foreign_key: str = Field(..., description="Foreign key column name")
    relationship_type: Literal["one-to-one", "one-to-many", "many-to-one", "many-to-many"] = Field(
        ..., description="Cardinality of relationship"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence in this relationship"
    )


class EntitySchema(BaseModel):
    """Complete schema definition for an entity"""
    name: str = Field(..., description="Entity name (PascalCase)")
    attributes: List[FieldDefinition] = Field(..., description="List of entity attributes")
    relationships: List[EntityRelationship] = Field(
        default_factory=list, description="Foreign key relationships"
    )
    table_name: Optional[str] = Field(None, description="Actual DuckDB table name (auto-generated)")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure entity name is valid"""
        if not v or not v.replace("_", "").isalnum():
            raise ValueError(f"Invalid entity name: {v}")
        return v
    
    @field_validator("attributes")
    @classmethod
    def validate_primary_key(cls, v: List[FieldDefinition]) -> List[FieldDefinition]:
        """Ensure exactly one primary key exists"""
        pk_count = sum(1 for attr in v if attr.is_primary_key)
        if pk_count == 0:
            raise ValueError("Entity must have exactly one primary key")
        if pk_count > 1:
            raise ValueError(f"Entity has {pk_count} primary keys, expected 1")
        return v
    
    def to_duckdb_ddl(self) -> str:
        """
        Generate DuckDB CREATE TABLE statement
        
        Returns:
            SQL DDL string
        """
        table_name = self.table_name or self.name.lower()
        
        column_defs = []
        for attr in self.attributes:
            col_def = f"{attr.name} {attr.type}"
            if attr.is_primary_key:
                col_def += " PRIMARY KEY"
            elif not attr.is_nullable:
                col_def += " NOT NULL"
            column_defs.append(col_def)
        
        # Add foreign key constraints
        for rel in self.relationships:
            fk_def = f"FOREIGN KEY ({rel.foreign_key}) REFERENCES {rel.to_entity.lower()}(id)"
            column_defs.append(fk_def)
        
        columns_str = ",\n  ".join(column_defs)
        return f"CREATE TABLE IF NOT EXISTS {table_name} (\n  {columns_str}\n);"


class SchemaInductionResult(BaseModel):
    """Result from schema induction process"""
    entities: List[EntitySchema] = Field(..., description="Discovered entity schemas")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional extraction metadata"
    )
    total_documents_analyzed: int = Field(..., description="Number of documents analyzed")
    extraction_timestamp: datetime = Field(
        default_factory=datetime.now, description="When schema was induced"
    )
    llm_model: str = Field(..., description="LLM model used for induction")
    llm_tokens_used: int = Field(default=0, description="Total tokens consumed")
    
    def get_entity_by_name(self, name: str) -> Optional[EntitySchema]:
        """Find entity schema by name"""
        for entity in self.entities:
            if entity.name.lower() == name.lower():
                return entity
        return None
    
    def get_all_table_names(self) -> List[str]:
        """Get list of all table names"""
        return [e.table_name or e.name.lower() for e in self.entities]


class EntityInstance(BaseModel):
    """Single extracted entity instance from a document"""
    entity_type: str = Field(..., description="Entity type (e.g., 'Deal', 'Company')")
    attributes: Dict[str, Any] = Field(..., description="Attribute values")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    source_chunk_id: Optional[str] = Field(None, description="Source chunk ID for provenance")
    source_text: Optional[str] = Field(None, description="Relevant excerpt from source")
    extraction_timestamp: datetime = Field(default_factory=datetime.now)


class EntityExtractionResult(BaseModel):
    """Result from entity extraction process"""
    entities: List[EntityInstance] = Field(..., description="Extracted entity instances")
    document_id: str = Field(..., description="Source document ID")
    entity_type: str = Field(..., description="Entity type being extracted")
    total_entities_found: int = Field(..., description="Total count")
    llm_model: str = Field(..., description="Model used for extraction")
    llm_tokens_used: int = Field(default=0)


class QueryMetadata(BaseModel):
    """Metadata for a natural language query"""
    query_id: str = Field(..., description="Unique query identifier")
    original_query: str = Field(..., description="Original NL query")
    query_type: Literal[
        "count", "aggregation", "filter", "group_by", "join", "temporal", "ranking", "simple"
    ] = Field(..., description="Classified query type")
    requires_join: bool = Field(default=False, description="Whether query needs table joins")
    complexity: Literal["low", "medium", "high"] = Field(
        default="medium", description="Query complexity"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")


class SQLQueryResult(BaseModel):
    """Result from SQL query translation"""
    sql: str = Field(..., description="Generated SQL query")
    query_type: str = Field(..., description="Type of query")
    explanation: str = Field(..., description="Human-readable explanation")
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_safe: bool = Field(default=True, description="Whether query is safe to execute")
    safety_warnings: List[str] = Field(default_factory=list)
    
    @field_validator("sql")
    @classmethod
    def validate_sql_safety(cls, v: str) -> str:
        """Basic SQL safety check"""
        dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE"]
        v_upper = v.upper()
        for keyword in dangerous_keywords:
            if keyword in v_upper:
                raise ValueError(f"SQL contains dangerous keyword: {keyword}")
        return v


class QueryExecutionResult(BaseModel):
    """Complete query execution result with provenance"""
    query_id: str
    original_query: str
    sql_executed: str
    results: List[Dict[str, Any]] = Field(default_factory=list)
    result_count: int
    execution_time_ms: float
    answer: Optional[str] = Field(None, description="Natural language answer")
    source_documents: List[Dict[str, str]] = Field(
        default_factory=list, description="Source document metadata"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_markdown(self) -> str:
        """
        Format result as markdown
        
        Returns:
            Markdown-formatted string
        """
        md = f"## Query Result\n\n"
        md += f"**Query**: {self.original_query}\n\n"
        
        if self.answer:
            md += f"**Answer**: {self.answer}\n\n"
        
        if self.results:
            # Format as markdown table
            if len(self.results) > 0:
                columns = list(self.results[0].keys())
                md += "**Results**:\n\n"
                md += "| " + " | ".join(columns) + " |\n"
                md += "|" + "|".join(["---"] * len(columns)) + "|\n"
                for row in self.results[:20]:  # Limit to 20 rows
                    md += "| " + " | ".join([str(row.get(col, "")) for col in columns]) + " |\n"
                if len(self.results) > 20:
                    md += f"\n*({len(self.results) - 20} more rows)*\n"
        else:
            md += "*No results found.*\n"
        
        md += f"\n**Execution Time**: {self.execution_time_ms:.0f}ms\n"
        md += f"**Confidence**: {self.confidence:.2f}\n"
        
        if self.source_documents:
            md += "\n**Sources**:\n"
            for i, doc in enumerate(self.source_documents, 1):
                md += f"{i}. {doc.get('filename', 'Unknown')} (ID: {doc.get('doc_id', 'N/A')})\n"
        
        return md


class IngestionSummary(BaseModel):
    """Summary of document ingestion process"""
    corpus_path: str
    total_files: int
    files_processed: int
    files_failed: int
    total_chunks: int
    total_tokens: int
    parsers_used: Dict[str, int] = Field(
        default_factory=dict, description="Count of files per parser type"
    )
    processing_time_seconds: float
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class AuditSummary(BaseModel):
    """System-wide audit summary"""
    total_documents: int
    total_chunks: int
    total_queries: int
    total_entities: int
    entity_tables: List[str]
    date_range: Dict[str, Optional[str]] = Field(
        default_factory=dict, description="First and last activity dates"
    )
    top_queries: List[Dict[str, Any]] = Field(
        default_factory=list, description="Most frequent queries"
    )
    storage_size_mb: Optional[float] = None
