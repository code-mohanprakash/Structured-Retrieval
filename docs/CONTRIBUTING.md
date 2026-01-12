# Contributing to StructRAG MCP

Thank you for your interest in contributing to StructRAG MCP! This guide will help you get started.

## 🚀 Quick Start for Contributors

### 1. Fork and Clone

```bash
git clone https://github.com/yourusername/structrag-mcp.git
cd structrag-mcp
```

### 2. Install Dependencies

```bash
# Option A: With Poetry (recommended)
poetry install
poetry shell

# Option B: With pip
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Set Up Environment

```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### 4. Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=structrag_mcp

# Run specific test file
poetry run pytest tests/test_parsers.py -v
```

### 5. Code Quality

```bash
# Format code
poetry run black .

# Check linting
poetry run ruff check .

# Type checking
poetry run mypy src/
```

## 📋 Development Workflow

### Branch Naming

- `feature/add-xyz` - New features
- `fix/issue-123` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/cleanup-code` - Code improvements

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add ChromaDB hybrid search
fix: handle empty document gracefully
docs: update API documentation
test: add integration tests for query engine
refactor: simplify schema inductor
```

### Pull Request Process

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Make changes**: Implement your feature with tests
3. **Run tests**: Ensure all tests pass
4. **Format code**: Run black and ruff
5. **Commit**: Use conventional commit format
6. **Push**: `git push origin feature/your-feature`
7. **PR**: Open pull request with clear description

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature that causes existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests pass locally

## Checklist
- [ ] Code follows style guidelines (black, ruff)
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings generated
```

## 🛠️ Project Structure

```
structrag-mcp/
├── src/structrag_mcp/
│   ├── ingestion/        # Document parsers, chunkers
│   ├── storage/          # DuckDB, provenance tracking
│   ├── structure/        # Schema induction, entity extraction
│   ├── query/            # Query engine, NL-to-SQL
│   ├── llm/              # LLM provider abstraction
│   └── server.py         # FastMCP server with 6 tools
├── tests/
│   ├── test_parsers.py
│   ├── test_integration.py
│   └── ...
├── examples/             # Example notebooks and scripts
├── docs/                 # Documentation
└── data/                 # Data directory (gitignored)
```

## 🎯 Areas We Need Help

### High Priority

- [ ] **ChromaDB Integration** - Implement hybrid structured+semantic search
- [ ] **Anthropic Fallback** - Complete Anthropic provider implementation
- [ ] **Confidence Tuning** - Improve entity extraction accuracy
- [ ] **Error Handling** - Robust error messages and recovery
- [ ] **Demo Dataset** - Generate 100 realistic sales call transcripts

### Medium Priority

- [ ] **More Parsers** - Excel, Word, PowerPoint support
- [ ] **Query Optimization** - SQL query optimization hints
- [ ] **Caching** - Cache LLM responses for repeated queries
- [ ] **Observability** - Add OpenTelemetry tracing
- [ ] **Documentation** - API docs, tutorials, examples

### Low Priority

- [ ] **Docker Compose** - Easy deployment setup
- [ ] **Web UI** - Simple web interface (optional)
- [ ] **Benchmarks** - Performance benchmarking suite
- [ ] **Localization** - Multi-language support

## 🧪 Testing Guidelines

### Unit Tests

Focus on individual components:

```python
def test_text_parser():
    parser = TextParser()
    result = parser.parse("sample.txt")
    assert "text" in result
    assert "metadata" in result
```

### Integration Tests

Test component interactions:

```python
def test_ingestion_to_query():
    # Ingest document
    db.insert_document(...)
    
    # Query data
    result = query_engine.query("How many deals?")
    assert result.result_count > 0
```

### E2E Tests

Test full user workflows:

```python
def test_complete_workflow():
    # 1. Ingest corpus
    ingest_corpus("./data/sales")
    
    # 2. Build structure
    build_structure(["Deal", "Company"])
    
    # 3. Query
    result = query_structured("Top 10 deals by value")
    assert len(result.results) == 10
```

## 📚 Documentation

### Code Comments

- Use docstrings for all public functions/classes
- Include type hints
- Explain "why" not "what"

```python
def extract_entities(
    self,
    entity_schema: EntitySchema,
    document_id: str
) -> EntityExtractionResult:
    """
    Extract entity instances from a document using LLM.
    
    Uses few-shot prompting to guide extraction and reduce hallucination.
    Filters results by confidence threshold to ensure quality.
    
    Args:
        entity_schema: Schema definition with attributes
        document_id: Document to extract from
    
    Returns:
        EntityExtractionResult with discovered entities
    """
```

### README Updates

If adding new features, update:
- README.md (user-facing)
- API documentation
- Examples

## 🐛 Bug Reports

Use GitHub Issues with this template:

**Describe the bug**
Clear description of the issue

**To Reproduce**
Steps to reproduce:
1. Ingest documents from '...'
2. Run query '...'
3. See error

**Expected behavior**
What should happen

**Actual behavior**
What actually happens

**Environment**
- OS: macOS 14.2
- Python: 3.11.5
- StructRAG version: 0.1.0

**Logs**
```
Error traceback or relevant logs
```

## 💡 Feature Requests

Use GitHub Issues with this template:

**Feature Description**
Clear description of proposed feature

**Use Case**
Why is this needed? What problem does it solve?

**Proposed Solution**
How would you implement this?

**Alternatives Considered**
Any other approaches?

**Additional Context**
Screenshots, mockups, examples

## 📝 Code Style

### Python Style

- Follow PEP 8
- Use Black formatter (line length: 100)
- Use type hints
- Prefer descriptive names over short ones

```python
# Good
def extract_entities_from_document(
    document_id: str,
    entity_schema: EntitySchema
) -> List[EntityInstance]:
    ...

# Avoid
def extract(doc_id, schema):
    ...
```

### Import Order

1. Standard library
2. Third-party packages
3. Local imports

```python
import os
import logging
from typing import List, Dict

import duckdb
from openai import OpenAI

from ..storage import DuckDBManager
from .models import EntitySchema
```

## 🤝 Community

- **GitHub Discussions** - Ask questions, share ideas
- **Discord** - Real-time chat (coming soon)
- **Twitter** - Follow [@structrag](https://twitter.com/structrag) for updates

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Thanked in release notes
- Eligible for "Top Contributor" badge

Thank you for contributing to StructRAG MCP! 🎉
