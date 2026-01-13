"""
StructRAG MCP - Structured Retrieval Augmented Generation

A Model Context Protocol server that combines structured SQL analytics
with document RAG for hybrid intelligence.

Implements S-RAG paper (arXiv:2511.08505v1) "Structured RAG for Answering 
Aggregative Questions" by AI21 Labs.

Key Features:
- Iterative schema refinement (Section 3.2.1)
- Value standardization for cross-document consistency (Section 3.2.2)
- Column statistics for text-to-SQL (Section 3.3)
- Hybrid inference mode (Section 3.3)
- LLM-as-judge evaluation (Section 5.5)
"""

__version__ = "0.2.0"
__author__ = "StructRAG Team"
__license__ = "MIT"

from .server import mcp

__all__ = ["mcp"]
