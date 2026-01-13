"""
Schema Induction Engine

Implements S-RAG paper Section 3.2.1: Iterative Schema Prediction
- Uses 4 iterations to refine schema
- Zero-shot prompting with 12 documents and 10 questions
- Captures recurring attributes across documents

Reference: arXiv:2511.08505v1 "Structured RAG for Answering Aggregative Questions"
"""

import logging
from typing import List, Dict, Any, Optional
import json

from ..llm.provider import complete_with_fallback
from ..llm.prompts import (
    build_schema_induction_prompt,
    build_iterative_schema_first_prompt,
    build_iterative_schema_refinement_prompt,
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

# S-RAG Paper constants (Section 3.2.1)
SRAG_NUM_ITERATIONS = 4
SRAG_NUM_DOCUMENTS = 12
SRAG_NUM_QUESTIONS = 10

logger = logging.getLogger(__name__)


def _strip_markdown_json(content: str) -> str:
    """Strip markdown code blocks and extra text from LLM response"""
    content = content.strip()
    
    # Remove markdown code block markers
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    
    content = content.strip()
    
    # Try to extract JSON if there's extra text
    # Look for the first { and last }
    start = content.find('{')
    end = content.rfind('}')
    
    if start != -1 and end != -1 and start < end:
        content = content[start:end+1]
    
    # Also check for array format
    if content.find('[') != -1 and content.rfind(']') != -1:
        arr_start = content.find('[')
        arr_end = content.rfind(']')
        if arr_start < arr_end:
            # If array comes before object, prefer object
            if start == -1 or arr_start < start:
                content = content[arr_start:arr_end+1]
    
    return content.strip()


def _fix_json_errors(json_str: str) -> str:
    """Try to fix common JSON errors from LLM responses"""
    import re
    
    # Fix trailing commas before closing braces/brackets
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix missing commas between objects/arrays
    json_str = re.sub(r'}\s*{', '},{', json_str)
    json_str = re.sub(r']\s*\[', '],[', json_str)
    json_str = re.sub(r'"\s*"', '","', json_str)
    
    # Fix single quotes (should be double quotes)
    json_str = json_str.replace("'", '"')
    
    # Remove comments (// or /* */)
    json_str = re.sub(r'//.*?\n', '\n', json_str)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # Fix unquoted keys (common LLM error)
    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
    
    # Fix already quoted keys that got double-quoted
    json_str = re.sub(r'""(\w+)"":', r'"\1":', json_str)
    
    return json_str


def _validate_and_filter_attributes(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out list and nested attributes per S-RAG paper footnote 3
    
    Paper states: "For simplicity at inference time, we exclude list and nested attributes."
    This function removes any properties with type: "array" or type: "object".
    
    Args:
        properties: Dictionary of property definitions from JSON Schema
    
    Returns:
        Filtered properties dictionary excluding array and object types
    
    Raises:
        ValueError: If a nested/array type is found and filtered out, logs warning
    """
    filtered = {}
    excluded = []
    
    for prop_name, prop_def in properties.items():
        if isinstance(prop_def, dict):
            prop_type = prop_def.get("type", "string")
            
            # Exclude arrays and objects per paper's simplifying assumption
            if prop_type == "array":
                excluded.append((prop_name, "array"))
                logger.warning(
                    f"Filtering out array attribute '{prop_name}' per S-RAG paper footnote 3: "
                    f"'For simplicity at inference time, we exclude list and nested attributes.'"
                )
            elif prop_type == "object":
                excluded.append((prop_name, "object"))
                logger.warning(
                    f"Filtering out nested object attribute '{prop_name}' per S-RAG paper footnote 3: "
                    f"'For simplicity at inference time, we exclude list and nested attributes.'"
                )
            else:
                # Keep non-list, non-nested attributes
                filtered[prop_name] = prop_def
        else:
            # Keep non-dict properties as-is
            filtered[prop_name] = prop_def
    
    if excluded:
        logger.info(f"Excluded {len(excluded)} nested/array attributes: {excluded}")
    
    return filtered


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
            json_mode=True,
            max_tokens=4000  # Increased for larger schemas
        )
        
        if response.error:
            raise RuntimeError(f"Schema induction failed: {response.error}")
        
        # Parse and validate response
        try:
            # Strip markdown code blocks and extract JSON
            clean_content = _strip_markdown_json(response.content)
            
            # Try to parse directly first
            try:
                schema_data = json.loads(clean_content)
            except json.JSONDecodeError as e:
                # Try fixing common JSON errors
                logger.warning(f"Initial JSON parse failed, attempting to fix: {str(e)}")
                fixed_content = _fix_json_errors(clean_content)
                schema_data = json.loads(fixed_content)
                logger.info("Successfully parsed JSON after fixes")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response even after fixes. Error: {str(e)}")
            logger.error(f"FULL Response content:\n{response.content}")
            logger.error(f"FULL Cleaned content:\n{clean_content if 'clean_content' in locals() else 'N/A'}")
            logger.error(f"FULL Fixed content:\n{fixed_content if 'fixed_content' in locals() else 'N/A'}")
            
            # Last resort: try to extract just the entities array
            try:
                import re
                entities_match = re.search(r'"entities"\s*:\s*\[.*?\]', clean_content, re.DOTALL)
                if entities_match:
                    logger.warning("Attempting to extract just the entities array...")
                    schema_data = json.loads('{' + entities_match.group(0) + '}')
                    logger.info("Successfully extracted entities array")
                else:
                    raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
            except:
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
    
    def induce_schema_iterative(
        self,
        entity_hints: List[str],
        sample_questions: Optional[List[str]] = None,
        num_iterations: int = SRAG_NUM_ITERATIONS,
        num_documents: int = SRAG_NUM_DOCUMENTS,
        num_questions: int = SRAG_NUM_QUESTIONS,
        min_confidence: float = 0.7
    ) -> SchemaInductionResult:
        """
        Iterative schema induction per S-RAG paper Section 3.2.1
        
        The paper describes: "We implement this stage using an iterative algorithm 
        in which an LLM is instructed to create and refine a JSON schema given a 
        small set of documents and questions."
        
        Args:
            entity_hints: User-provided entity types
            sample_questions: Representative questions for schema refinement
            num_iterations: Number of refinement iterations (default 4 per paper)
            num_documents: Number of documents to analyze (default 12 per paper)
            num_questions: Number of questions for refinement (default 10 per paper)
            min_confidence: Minimum confidence threshold for attributes
        
        Returns:
            SchemaInductionResult with iteratively refined schema
        """
        logger.info(f"Starting iterative schema induction (S-RAG): {num_iterations} iterations")
        
        # Get sample documents
        sample_docs = self._get_sample_documents(num_documents)
        
        if not sample_docs:
            raise ValueError("No documents in corpus. Ingest documents first.")
        
        logger.info(f"Using {len(sample_docs)} documents for schema induction")
        
        # Default sample questions if none provided
        if not sample_questions:
            sample_questions = self._generate_default_questions(entity_hints)
        
        # Track total tokens used
        total_tokens = 0
        current_schema = None
        
        for iteration in range(num_iterations):
            logger.info(f"Schema iteration {iteration + 1}/{num_iterations}")
            
            if iteration == 0:
                # First iteration: zero-shot schema extraction
                prompt = build_iterative_schema_first_prompt(
                    sample_documents=sample_docs,
                    max_samples=num_documents
                )
            else:
                # Subsequent iterations: refine with questions
                prompt = build_iterative_schema_refinement_prompt(
                    existing_schema=current_schema,
                    sample_questions=sample_questions[:num_questions],
                    sample_documents=sample_docs,
                    max_samples=num_documents
                )
            
            # Call LLM
            response = complete_with_fallback(
                system_prompt=SYSTEM_PROMPT_SCHEMA_INDUCTION,
                user_prompt=prompt,
                json_mode=True,
                max_tokens=4000
            )
            
            if response.error:
                logger.error(f"Iteration {iteration + 1} failed: {response.error}")
                if current_schema is None:
                    raise RuntimeError(f"First iteration failed: {response.error}")
                # Continue with previous schema
                continue
            
            total_tokens += response.total_tokens
            
            # Parse response
            try:
                clean_content = _strip_markdown_json(response.content)
                try:
                    schema_data = json.loads(clean_content)
                except json.JSONDecodeError:
                    fixed_content = _fix_json_errors(clean_content)
                    schema_data = json.loads(fixed_content)
                
                current_schema = schema_data
                logger.info(f"Iteration {iteration + 1}: Schema has {len(schema_data.get('properties', {}))} properties")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse iteration {iteration + 1} response: {e}")
                if current_schema is None:
                    raise ValueError(f"Failed to parse first iteration schema: {e}")
        
        # Convert final schema to EntitySchema format
        entities = self._convert_json_schema_to_entities(
            current_schema, 
            entity_hints, 
            min_confidence
        )
        
        result = SchemaInductionResult(
            entities=entities,
            metadata={
                "iterations": num_iterations,
                "documents_analyzed": len(sample_docs),
                "questions_used": len(sample_questions[:num_questions]),
                "extraction_method": "iterative_srag"
            },
            total_documents_analyzed=len(sample_docs),
            llm_model=response.model,
            llm_tokens_used=total_tokens
        )
        
        logger.info(f"Iterative schema induction complete: {len(entities)} entities discovered")
        
        # Store schema in registry
        self._store_schema_in_registry(result)
        
        return result
    
    def _generate_default_questions(self, entity_hints: List[str]) -> List[str]:
        """Generate default sample questions based on entity hints"""
        questions = []
        for entity in entity_hints:
            questions.extend([
                f"How many {entity}s are there?",
                f"What is the average value across all {entity}s?",
                f"Which {entity} has the highest value?",
                f"List all {entity}s with specific criteria",
                f"What are the common attributes of {entity}s?"
            ])
        return questions[:SRAG_NUM_QUESTIONS]
    
    def _convert_json_schema_to_entities(
        self,
        json_schema: Dict[str, Any],
        entity_hints: List[str],
        min_confidence: float
    ) -> List[EntitySchema]:
        """Convert JSON Schema format to EntitySchema format"""
        entities = []
        
        # Handle S-RAG JSON Schema format
        properties = json_schema.get("properties", {})
        title = json_schema.get("title", entity_hints[0] if entity_hints else "Entity")
        required_fields = json_schema.get("required", [])
        
        # Validate and filter out nested/array attributes per S-RAG paper
        properties = _validate_and_filter_attributes(properties)
        
        attributes = []
        
        # Add auto-generated primary key
        attributes.append(FieldDefinition(
            name=f"{title.lower()}_id",
            type="TEXT",
            confidence=1.0,
            is_primary_key=True,
            is_nullable=False,
            description="Auto-generated primary key"
        ))
        
        # Convert properties to FieldDefinitions
        for prop_name, prop_def in properties.items():
            if isinstance(prop_def, dict):
                # Map JSON Schema types to DuckDB types
                json_type = prop_def.get("type", "string")
                if json_type == "integer":
                    db_type = "INTEGER"
                elif json_type == "number":
                    db_type = "REAL"
                elif json_type == "boolean":
                    db_type = "BOOLEAN"
                else:
                    db_type = "TEXT"
                
                # Get examples if available
                examples = prop_def.get("examples", [])
                if not isinstance(examples, list):
                    examples = [examples] if examples else []
                
                # Convert examples to strings
                examples = [str(ex) for ex in examples[:5]]
                
                field = FieldDefinition(
                    name=prop_name.lower().replace(" ", "_"),
                    type=db_type,
                    confidence=0.9,  # Default confidence for iterative method
                    is_primary_key=False,
                    is_nullable=prop_name not in required_fields,
                    description=prop_def.get("description", ""),
                    examples=examples
                )
                attributes.append(field)
        
        entity = EntitySchema(
            name=title,
            attributes=attributes,
            relationships=[],
            table_name=title.lower()
        )
        entities.append(entity)
        
        return entities

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
            
            # Use entity name as table name (will be used for actual table creation)
            table_name = entity.name.lower()
            
            # Check if schema already exists, if so update it
            check_query = "SELECT COUNT(*) as cnt FROM schema_registry WHERE table_name = ?"
            try:
                existing = self.db.execute_query(check_query, params=[table_name])
                # Handle different result formats (dict vs tuple)
                count = 0
                if existing and len(existing) > 0:
                    if isinstance(existing[0], dict):
                        count = existing[0].get("cnt", 0)
                    else:
                        count = existing[0][0] if len(existing[0]) > 0 else 0
                
                if count > 0:
                    # Update existing schema
                    update_query = """
                    UPDATE schema_registry 
                    SET entity_type = ?, schema_json = ?, confidence = ?
                    WHERE table_name = ?
                    """
                    self.db.execute_query(
                        update_query,
                        params=[entity.name, schema_json, result.metadata.get("confidence", 0.9), table_name]
                    )
                    logger.info(f"Updated schema for {table_name}")
                else:
                    # Insert new schema
                    insert_query = """
                    INSERT INTO schema_registry (table_name, entity_type, schema_json, created_at, confidence)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """
                    self.db.execute_query(
                        insert_query,
                        params=[table_name, entity.name, schema_json, result.metadata.get("confidence", 0.9)]
                    )
                    logger.info(f"Inserted new schema for {table_name}")
            except Exception as e:
                logger.warning(f"Error checking/storing schema for {table_name}: {e}. Attempting insert...")
                # Fallback: try insert, ignore if duplicate
                try:
                    insert_query = """
                    INSERT INTO schema_registry (table_name, entity_type, schema_json, created_at, confidence)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """
                    self.db.execute_query(
                        insert_query,
                        params=[table_name, entity.name, schema_json, result.metadata.get("confidence", 0.9)]
                    )
                except Exception as insert_err:
                    logger.info(f"Schema {table_name} already exists: {insert_err}")
        
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
