"""
Entity Extraction Pipeline

Extracts structured entity instances from documents using LLM.
Stores entities in dynamically created DuckDB tables.
"""

import logging
from typing import List, Dict, Any, Optional
import json

from ..llm.provider import complete_with_fallback
from ..llm.prompts import (
    build_entity_extraction_prompt,
    SYSTEM_PROMPT_ENTITY_EXTRACTION
)
from ..storage.duckdb_manager import DuckDBManager
from ..storage.provenance import ProvenanceTracker
from .models import (
    EntitySchema,
    EntityInstance,
    EntityExtractionResult
)

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Extract entity instances from documents
    
    Usage:
        >>> extractor = EntityExtractor(db_manager, provenance)
        >>> result = extractor.extract_entities(
        ...     entity_schema=deal_schema,
        ...     document_id="doc_123"
        ... )
    """
    
    def __init__(
        self,
        db_manager: DuckDBManager,
        provenance: ProvenanceTracker
    ):
        self.db = db_manager
        self.provenance = provenance
    
    def extract_entities(
        self,
        entity_schema: EntitySchema,
        document_id: str,
        min_confidence: float = 0.7
    ) -> EntityExtractionResult:
        """
        Extract entities from a document
        
        Args:
            entity_schema: Schema definition for entity type
            document_id: Document to extract from
            min_confidence: Minimum confidence threshold
        
        Returns:
            EntityExtractionResult with extracted instances
        """
        logger.info(f"Extracting {entity_schema.name} entities from document {document_id}")
        
        # Get document text
        document_text = self._get_document_text(document_id)
        
        if not document_text:
            raise ValueError(f"Document {document_id} not found")
        
        # Build extraction prompt
        prompt = build_entity_extraction_prompt(
            entity_name=entity_schema.name,
            entity_schema=entity_schema.model_dump(),
            document_text=document_text
        )
        
        # Call LLM for extraction
        response = complete_with_fallback(
            system_prompt=SYSTEM_PROMPT_ENTITY_EXTRACTION,
            user_prompt=prompt,
            json_mode=True
        )
        
        if response.error:
            raise RuntimeError(f"Entity extraction failed: {response.error}")
        
        # Parse response
        try:
            extraction_data = json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {response.content}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        
        # Normalize Groq responses that may return a top-level list
        if isinstance(extraction_data, list):
            extraction_data = {"entities": extraction_data}
        
        # Convert to EntityInstance objects
        entities = []
        for entity_data in extraction_data.get("entities", []):
            if entity_data.get("confidence", 0) >= min_confidence:
                entity = EntityInstance(
                    entity_type=entity_schema.name,
                    attributes=entity_data["attributes"],
                    confidence=entity_data["confidence"],
                    source_chunk_id=None,  # Will be set when storing
                    source_text=entity_data.get("source_text")
                )
                entities.append(entity)
        
        result = EntityExtractionResult(
            entities=entities,
            document_id=document_id,
            entity_type=entity_schema.name,
            total_entities_found=len(entities),
            llm_model=response.model,
            llm_tokens_used=response.total_tokens
        )
        
        logger.info(f"Extracted {len(entities)} {entity_schema.name} entities")
        
        return result
    
    def extract_from_corpus(
        self,
        entity_schema: EntitySchema,
        batch_size: int = 10,
        min_confidence: float = 0.7
    ) -> List[EntityExtractionResult]:
        """
        Extract entities from entire document corpus
        
        Args:
            entity_schema: Schema for entity type
            batch_size: Number of documents to process in parallel
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of extraction results per document
        """
        logger.info(f"Extracting {entity_schema.name} from entire corpus")
        
        # Get all document IDs
        doc_ids = self._get_all_document_ids()
        
        if not doc_ids:
            logger.warning("No documents in corpus")
            return []
        
        logger.info(f"Processing {len(doc_ids)} documents")
        
        results = []
        for doc_id in doc_ids:
            try:
                result = self.extract_entities(
                    entity_schema=entity_schema,
                    document_id=doc_id,
                    min_confidence=min_confidence
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract from document {doc_id}: {str(e)}")
        
        logger.info(f"Extraction complete: {sum(r.total_entities_found for r in results)} total entities")
        
        return results
    
    def store_entities(
        self,
        entity_schema: EntitySchema,
        entities: List[EntityInstance]
    ):
        """
        Store extracted entities in DuckDB table
        
        Args:
            entity_schema: Schema definition
            entities: List of entity instances to store
        """
        if not entities:
            logger.warning("No entities to store")
            return
        
        table_name = entity_schema.table_name or entity_schema.name.lower()
        
        logger.info(f"Storing {len(entities)} entities in table '{table_name}'")
        
        # Build INSERT statements
        for entity in entities:
            # Add source_chunk_id for provenance if available
            if entity.source_chunk_id:
                entity.attributes["source_chunk_id"] = entity.source_chunk_id
            
            # Build column names and values
            columns = list(entity.attributes.keys())
            values = [entity.attributes[col] for col in columns]
            
            placeholders = ", ".join(["?"] * len(columns))
            columns_str = ", ".join(columns)
            
            insert_query = f"""
            INSERT INTO {table_name} ({columns_str})
            VALUES ({placeholders})
            """
            
            try:
                self.db.execute_query(insert_query, params=values)
            except Exception as e:
                logger.error(f"Failed to insert entity: {str(e)}")
                logger.debug(f"Query: {insert_query}, Values: {values}")
        
        logger.info(f"✓ Stored {len(entities)} entities in '{table_name}'")
    
    def _get_document_text(self, document_id: str) -> Optional[str]:
        """Get full document text by concatenating chunks"""
        query = """
        SELECT text
        FROM chunks
        WHERE doc_id = ?
        ORDER BY chunk_index
        """
        
        results = self.db.execute_query(query, params=[document_id])
        
        if not results:
            return None
        
        # Concatenate all chunks
        return "\n\n".join([row["text"] for row in results if row.get("text")])
    
    def _get_all_document_ids(self) -> List[str]:
        """Get all document IDs from corpus"""
        query = "SELECT DISTINCT doc_id FROM documents"
        results = self.db.execute_query(query)
        return [row["doc_id"] for row in results]
