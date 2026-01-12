"""Structure discovery package"""

from .models import (
    FieldDefinition,
    EntityRelationship,
    EntitySchema,
    SchemaInductionResult,
    EntityInstance,
    EntityExtractionResult,
    QueryMetadata,
    SQLQueryResult,
    QueryExecutionResult,
    IngestionSummary,
    AuditSummary
)
from .schema_inductor import SchemaInductor
from .entity_extractor import EntityExtractor

__all__ = [
    "FieldDefinition",
    "EntityRelationship",
    "EntitySchema",
    "SchemaInductionResult",
    "EntityInstance",
    "EntityExtractionResult",
    "QueryMetadata",
    "SQLQueryResult",
    "QueryExecutionResult",
    "IngestionSummary",
    "AuditSummary",
    "SchemaInductor",
    "EntityExtractor"
]
