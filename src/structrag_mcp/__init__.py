"""
StructRAG MCP - Structured Retrieval Augmented Generation

A Model Context Protocol server that combines structured SQL analytics
with document RAG for hybrid intelligence.
"""

__version__ = "0.1.0"
__author__ = "StructRAG Team"
__license__ = "MIT"

from .server import mcp

__all__ = ["mcp"]
