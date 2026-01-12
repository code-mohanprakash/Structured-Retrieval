# StructRAG MCP

**The first open-source MCP server for Structured RAG**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-green.svg)](https://github.com/jlowin/fastmcp)

Automatically discover structure in unstructured documents and answer analytical queries (COUNT, AVG, SUM, TOP-N) that traditional RAG systems cannot handle.

## 🎯 What Makes This Different?

| Traditional RAG | StructRAG MCP |
|----------------|---------------|
| "Find me the answer" | "What do all these docs say?" |
| Returns passages | Returns aggregated facts |
| No COUNT/AVG/SUM | Full analytical queries |
| No provenance | Every answer traced to sources |
| Requires pre-built DB | Auto-discovers structure |

## ⚡ Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/structrag-mcp.git
cd structrag-mcp

# Install with Poetry
poetry install

# Configure API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "structrag": {
      "command": "poetry",
      "args": ["run", "python", "-m", "structrag_mcp.server"],
      "cwd": "/absolute/path/to/structrag-mcp"
    }
  }
}
```

Restart Claude Desktop and look for the 🔧 tool icon.

### Example Workflow

1. **Ingest documents**: Use `ingest_corpus` tool with `./data/sales_calls`
2. **Discover schema**: Use `build_structure` with `entity_hints: ["Deal", "Company", "Contact"]`
3. **Query data**: Use `query_structured` with `"Average deal size by industry?"`
4. **Audit sources**: Use `audit` to see provenance

## 🛠️ MCP Tools

StructRAG exposes 6 tools:

- **`ingest_corpus(input_path)`** - Load documents (PDF, CSV, text, markdown, JSON)
- **`build_structure(entity_hints, max_samples)`** - Auto-discover schema from documents
- **`explain_schema()`** - View current database schema
- **`query_structured(nl_query, format)`** - Natural language queries with SQL backend
- **`audit(query_id)`** - View query provenance and system stats
- **`query_hybrid(nl_query)`** - Semantic + structured search *(coming soon)*

## 📊 Architecture

```
Documents → Parsers → Chunker → DuckDB
                                   ↓
                        Schema Inductor (GPT-4o)
                                   ↓
                          Entity Extractor
                                   ↓
Query (NL) → Classifier → SQL Translator → Executor → Answer
                                                        ↓
                                                  Provenance
```

## 🚀 Tech Stack

- **FastMCP 0.3.0** - MCP server framework (10x less boilerplate)
- **DuckDB 1.1.3** - Analytical database (10-100x faster than PostgreSQL)
- **OpenAI GPT-4o** - Schema induction & NL-to-SQL translation
- **tiktoken** - Token counting for semantic chunking
- **Pydantic 2.5** - Type-safe data validation
- **Python 3.11+** - Modern async Python

## 📝 License

MIT License - see [LICENSE](LICENSE) for details

## 🤝 Contributing

Contributions welcome! This project is in active development. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📖 Citation

```bibtex
@software{structrag2025,
  title={StructRAG MCP: Structured Retrieval Augmented Generation},
  year={2025},
  url={https://github.com/yourusername/structrag-mcp}
}
```

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

## 🙏 Acknowledgments

- Built on the Model Context Protocol by Anthropic
- Inspired by research on Structured RAG
- Powered by FastMCP framework

---

**Status:** 🚧 Alpha - Building in public!  
**Follow development:** [GitHub Discussions](https://github.com/mohan/structrag-mcp/discussions)
