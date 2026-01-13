"""
Entity Extraction Pipeline

Extracts structured entity instances from documents using LLM.
Stores entities in dynamically created DuckDB tables.

Implements S-RAG paper Section 3.2.2: Record Prediction with value standardization
for cross-document consistency (e.g., "1M" → 1000000, "1,000" → 1000).
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional

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


# ============================================================================
# VALUE STANDARDIZATION (S-RAG Paper Section 3.2.2)
# ============================================================================

def standardize_value(value: Any, field_type: str = "TEXT") -> Any:
    """
    Standardize extracted values for cross-document consistency.
    
    Per S-RAG paper Section 3.2.2: "Since the meaning of a value can be 
    expressed in multiple ways (e.g., the number one million may appear 
    as 1,000,000, 1M, or simply 1), attribute descriptions and examples 
    are crucial for guiding the LLM in lexicalizing values."
    
    This function provides post-processing standardization.
    
    Args:
        value: Raw extracted value
        field_type: Expected data type (TEXT, INTEGER, REAL, etc.)
    
    Returns:
        Standardized value
    """
    if value is None:
        return None
    
    # Convert to string for processing
    str_value = str(value).strip()
    
    if not str_value or str_value.lower() in ['null', 'none', 'n/a', 'na', '-']:
        return None
    
    if field_type in ["INTEGER", "REAL"]:
        return _standardize_numeric(str_value, field_type)
    elif field_type == "BOOLEAN":
        return _standardize_boolean(str_value)
    elif field_type == "DATE":
        return _standardize_date(str_value)
    else:
        return _standardize_text(str_value)


def _standardize_numeric(value: str, field_type: str) -> Optional[Any]:
    """
    Standardize numeric values with SI prefixes and currency symbols.
    
    Handles:
    - Currency symbols: $1M → 1000000
    - SI prefixes: 1K, 1M, 1B, 1T
    - Thousands separators: 1,000,000 → 1000000
    - Percentages: 15% → 15
    """
    original_value = value
    
    # Remove currency symbols
    value = re.sub(r'[\$€£¥₹]', '', value).strip()
    
    # Handle percentage
    is_percentage = '%' in value
    value = value.replace('%', '').strip()
    
    # Remove thousands separators
    value = value.replace(',', '')
    
    # Handle SI suffixes (case insensitive)
    multiplier = 1
    suffix_match = re.search(r'([0-9.]+)\s*([kKmMbBtT])(?:illion)?$', value)
    if suffix_match:
        value = suffix_match.group(1)
        suffix = suffix_match.group(2).upper()
        multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000, 'T': 1000000000000}
        multiplier = multipliers.get(suffix, 1)
    
    # Also handle word forms
    word_match = re.search(r'([0-9.]+)\s*(thousand|million|billion|trillion)', value, re.IGNORECASE)
    if word_match:
        value = word_match.group(1)
        word = word_match.group(2).lower()
        word_multipliers = {
            'thousand': 1000, 'million': 1000000, 
            'billion': 1000000000, 'trillion': 1000000000000
        }
        multiplier = word_multipliers.get(word, 1)
    
    try:
        # Parse the numeric value
        num_value = float(value) * multiplier
        
        if field_type == "INTEGER":
            return int(num_value)
        else:
            return num_value
    except (ValueError, TypeError):
        logger.warning(f"Could not standardize numeric value: {original_value}")
        return None


def _standardize_boolean(value: str) -> Optional[bool]:
    """Standardize boolean values"""
    value_lower = value.lower().strip()
    
    true_values = {'true', 'yes', 'y', '1', 'on', 'enabled', 'available', 'included'}
    false_values = {'false', 'no', 'n', '0', 'off', 'disabled', 'unavailable', 'not included'}
    
    if value_lower in true_values:
        return True
    elif value_lower in false_values:
        return False
    else:
        return None


def _standardize_date(value: str) -> Optional[str]:
    """Standardize date values to ISO format YYYY-MM-DD"""
    import re
    from datetime import datetime
    
    # Common date patterns
    patterns = [
        (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),  # 2024-01-15
        (r'(\d{2})/(\d{2})/(\d{4})', '%m/%d/%Y'),  # 01/15/2024
        (r'(\d{2})-(\d{2})-(\d{4})', '%m-%d-%Y'),  # 01-15-2024
        (r'(\d{1,2})\s+(\w+)\s+(\d{4})', '%d %B %Y'),  # 15 January 2024
        (r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', '%B %d %Y'),  # January 15, 2024
    ]
    
    for pattern, date_format in patterns:
        match = re.search(pattern, value)
        if match:
            try:
                parsed = datetime.strptime(match.group(0).replace(',', ''), date_format)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue
    
    # Return original if no pattern matches
    return value


def _standardize_text(value: str) -> str:
    """Standardize text values"""
    # Normalize whitespace
    value = ' '.join(value.split())
    # Strip quotes
    value = value.strip('"\'')
    return value


def standardize_entity_attributes(
    attributes: Dict[str, Any], 
    schema: EntitySchema
) -> Dict[str, Any]:
    """
    Standardize all attributes of an entity based on schema field types.
    
    Args:
        attributes: Raw extracted attribute values
        schema: Entity schema with field type definitions
    
    Returns:
        Standardized attributes dictionary
    """
    standardized = {}
    
    # Build field type lookup
    field_types = {field.name: field.type for field in schema.attributes}
    
    for key, value in attributes.items():
        field_type = field_types.get(key, "TEXT")
        standardized[key] = standardize_value(value, field_type)
    
    return standardized


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
            json_mode=True,
            max_tokens=4000  # Increased for larger extractions
        )
        
        if response.error:
            raise RuntimeError(f"Entity extraction failed: {response.error}")
        
        # Parse response
        try:
            # Strip markdown and extract JSON
            content = response.content.strip()
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Extract JSON from mixed content
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1 and start < end:
                content = content[start:end+1]
            
            # Try to parse
            try:
                extraction_data = json.loads(content)
            except json.JSONDecodeError as e:
                # Try fixing common errors
                import re
                content = re.sub(r',\s*}', '}', content)
                content = re.sub(r',\s*]', ']', content)
                content = re.sub(r'}\s*{', '},{', content)
                content = content.replace("'", '"')
                extraction_data = json.loads(content)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {response.content[:1000]}")
            logger.error(f"Cleaned content: {content[:1000] if 'content' in locals() else 'N/A'}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        
        # Normalize Groq responses that may return a top-level list
        if isinstance(extraction_data, list):
            extraction_data = {"entities": extraction_data}
        
        # Convert to EntityInstance objects with value standardization (S-RAG Section 3.2.2)
        entities = []
        for entity_data in extraction_data.get("entities", []):
            if entity_data.get("confidence", 0) >= min_confidence:
                # Apply value standardization for cross-document consistency
                raw_attributes = entity_data["attributes"]
                standardized_attributes = standardize_entity_attributes(
                    raw_attributes, 
                    entity_schema
                )
                
                entity = EntityInstance(
                    entity_type=entity_schema.name,
                    attributes=standardized_attributes,
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
