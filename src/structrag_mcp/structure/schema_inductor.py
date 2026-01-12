"""
Schema Induction Engine

Discovers structured schemas from unstructured documents using LLM analysis.
Implements guided mode with user-provided entity hints.
"""

import logging
from typing import List, Dict, Any, Optional
import json

from ..llm.provider import complete_with_fallback
from ..llm.prompts import (
    build_schema_induction_prompt,
    SYSTEM_PROMPT_SCHEMA_INDUCTION
)
from ..storage.duckdb_manager import DuckDBManager
from .models import (
    EntitySchema,
    FieldDefinition,
    EntityRelationship,
    SchemaInductionResult
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


class SchemaInductor:
    """
    Discovers entity schemas from document corpus
    
    Usage:
        >>> inductor = SchemaInductor(db_manager)
        >>> result = inductor.induce_schema(
        ...     entity_hints=["Deal", "Company", "Person"],
        ...     max_samples=10
        ... )
        >>> print(result.entities)
    """
    
    def __init__(self, db_manager: DuckDBManager):
        self.db = db_manager
    
    def induce_schema(
        self,
        entity_hints: List[str],
        max_samples: int = 10,
        min_confidence: float = 0.7
    ) -> SchemaInductionResult:
        """
        Induce schema from document corpus
        
        Args:
            entity_hints: User-provided entity types (e.g. ["Deal", "Company"])
            max_samples: Number of sample documents to analyze
            min_confidence: Minimum confidence threshold for attributes
        
        Returns:
            SchemaInductionResult with discovered entities
        """
        logger.info(f"Starting schema induction for entities: {entity_hints}")
        
        # Get sample documents from database
        sample_docs = self._get_sample_documents(max_samples)
        
        if not sample_docs:
            raise ValueError("No documents in corpus. Ingest documents first.")
        
        logger.info(f"Analyzing {len(sample_docs)} sample documents")
        
        # Build prompt with samples
        prompt = build_schema_induction_prompt(
            entity_hints=entity_hints,
            sample_documents=sample_docs,
            max_samples=max_samples
        )
        
        # Call LLM for schema extraction
        response = complete_with_fallback(
            system_prompt=SYSTEM_PROMPT_SCHEMA_INDUCTION,
            user_prompt=prompt,
            json_mode=True
        )
        
        if response.error:
            raise RuntimeError(f"Schema induction failed: {response.error}")
        
        # Parse and validate response
        try:
            # Strip markdown code blocks (Groq wraps JSON in ```json...```)
            clean_content = _strip_markdown_json(response.content)
            schema_data = json.loads(clean_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {response.content}")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
        
        # Convert to Pydantic models
        entities = []
        for entity_data in schema_data.get("entities", []):
            # Filter low-confidence attributes
            attributes = [
                FieldDefinition(**attr)
                for attr in entity_data.get("attributes", [])
                if attr.get("confidence", 0) >= min_confidence
            ]
            
            # Ensure primary key exists
            if not any(attr.is_primary_key for attr in attributes):
                # Add auto-generated ID as primary key
                attributes.insert(0, FieldDefinition(
                    name=f"{entity_data['name'].lower()}_id",
                    type="TEXT",
                    confidence=1.0,
                    is_primary_key=True,
                    is_nullable=False,
                    description="Auto-generated primary key"
                ))
            
            relationships = [
                EntityRelationship(**rel)
                for rel in entity_data.get("relationships", [])
            ]
            
            entity = EntitySchema(
                name=entity_data["name"],
                attributes=attributes,
                relationships=relationships,
                table_name=entity_data["name"].lower()
            )
            entities.append(entity)
        
        result = SchemaInductionResult(
            entities=entities,
            metadata=schema_data.get("metadata", {}),
            total_documents_analyzed=len(sample_docs),
            llm_model=response.model,
            llm_tokens_used=response.total_tokens
        )
        
        logger.info(f"Schema induction complete: {len(entities)} entities discovered")
        
        # Store schema in registry
        self._store_schema_in_registry(result)
        
        return result
    
    def _get_sample_documents(self, max_samples: int) -> List[str]:
        """
        Get sample document texts from database
        
        Args:
            max_samples: Maximum number of samples
        
        Returns:
            List of document text strings
        """
        query = f"""
        SELECT text
        FROM chunks
        ORDER BY RANDOM()
        LIMIT {max_samples}
        """
        
        results = self.db.execute_query(query)
        return [row["text"] for row in results if row.get("text")]
    
    def _store_schema_in_registry(self, result: SchemaInductionResult):
        """Store schema in DuckDB schema_registry table"""
        for entity in result.entities:
            schema_json = entity.model_dump_json()
            
            insert_query = """
            INSERT INTO schema_registry (table_name, entity_type, schema_json, created_at, confidence)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            """
            
            # Use entity name as table name (will be used for actual table creation)
            table_name = entity.name.lower()
            
            self.db.execute_query(
                insert_query,
                params=[table_name, entity.name, schema_json, result.metadata.get("confidence", 0.9)]
            )
        
        logger.info(f"Stored {len(result.entities)} schemas in registry")
    
    def create_tables_from_schema(self, result: SchemaInductionResult):
        """
        Create DuckDB tables from induced schema
        
        Args:
            result: SchemaInductionResult with entity definitions
        """
        for entity in result.entities:
            ddl = entity.to_duckdb_ddl()
            logger.info(f"Creating table: {entity.table_name}")
            logger.debug(f"DDL: {ddl}")
            
            try:
                self.db.execute_query(ddl)
                logger.info(f"✓ Table '{entity.table_name}' created successfully")
            except Exception as e:
                logger.error(f"✗ Failed to create table '{entity.table_name}': {str(e)}")
                raise
    
    def get_schema_from_registry(self, entity_name: str) -> Optional[EntitySchema]:
        """
        Retrieve schema from registry
        
        Args:
            entity_name: Name of entity
        
        Returns:
            EntitySchema if found, None otherwise
        """
        query = """
        SELECT schema_json
        FROM schema_registry
        WHERE entity_type = ?
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        results = self.db.execute_query(query, params=[entity_name])
        
        if not results:
            return None
        
        schema_json = results[0]["schema_json"]
        return EntitySchema.model_validate_json(schema_json)
    
    def list_all_schemas(self) -> List[EntitySchema]:
        """
        List all schemas in registry
        
        Returns:
            List of EntitySchema objects
        """
        query = """
        SELECT DISTINCT ON (entity_type) entity_type, schema_json
        FROM schema_registry
        ORDER BY entity_type, created_at DESC
        """
        
        results = self.db.execute_query(query)
        
        schemas = []
        for row in results:
            try:
                schema = EntitySchema.model_validate_json(row["schema_json"])
                schemas.append(schema)
            except Exception as e:
                logger.warning(f"Failed to parse schema for {row['entity_type']}: {str(e)}")
        
        return schemas
