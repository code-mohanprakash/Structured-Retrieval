# 📦 StructRAG Distribution & Usage Guide

## 🎯 How Users Would Use This

Your StructRAG is an **MCP Server** that integrates with Claude Desktop (or other MCP clients). Here are the distribution options:

---

## Option 1: Publish to PyPI (Recommended for Public Use)

### What is PyPI?
- Python Package Index (like npm for Python)
- Users install with: `pip install structrag-mcp`
- Easiest for end users

### How to Publish

**Step 1: Prepare Package**
```bash
# Your package is already set up! (pyproject.toml exists)
# Just update version in pyproject.toml

# Build the package
pip install build twine
python -m build
```

**Step 2: Publish to PyPI**
```bash
# Create account at https://pypi.org
# Get API token from account settings

# Upload to PyPI
python -m twine upload dist/*
```

**Step 3: Users Install**
```bash
# Users would run:
pip install structrag-mcp
```

---

## Option 2: Install from GitHub (Current Setup)

### How It Works
Users clone your repo and install locally.

**Your Users Would Run:**
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/structrag-mcp.git
cd structrag-mcp

# Install
pip install -e .

# Configure (create .env)
cp .env.example .env
# Edit .env with their Groq API key
```

**To Set This Up:**
1. Create GitHub repository
2. Push your code:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/structrag-mcp.git
   git push -u origin main
   ```

---

## Option 3: MCP Server (Use with Claude Desktop)

### What is MCP?
**Model Context Protocol** - allows Claude Desktop to access your tools as plugins.

### How Users Would Use It

**Step 1: Install StructRAG**
```bash
# From PyPI (if published)
pip install structrag-mcp

# OR from GitHub
git clone https://github.com/YOUR_USERNAME/structrag-mcp.git
cd structrag-mcp
pip install -e .
```

**Step 2: Configure Claude Desktop**

Users edit their Claude Desktop config file:

**On macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**On Windows:** `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "structrag": {
      "command": "python",
      "args": [
        "-m",
        "structrag_mcp.server"
      ],
      "env": {
        "GROQ_API_KEY": "gsk_YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**Step 3: Use in Claude Desktop**

Once configured, users can:
- Open Claude Desktop
- Your StructRAG tools appear automatically
- Use tools like: "Ingest this PDF folder", "Build schema", "Query: what was revenue?"

---

## 📋 What Users Need

### Requirements
1. **Python 3.11+** (already specified in pyproject.toml)
2. **Groq API Key** (or OpenAI/Anthropic)
3. **Claude Desktop** (optional, for MCP usage)

### Installation Size
- Base package: ~50 KB (your code)
- Dependencies: ~200 MB (DuckDB, PyPDF, etc.)
- Runtime: ~500 MB with model cache

---

## 🚀 Recommended Distribution Method

### For Your Use Case (PDFs → SQL):

**Best Approach: PyPI + GitHub**

```
1. Publish to PyPI → Easy installation
2. Keep GitHub repo → Documentation + examples
3. Provide MCP config → Claude Desktop integration
```

### Complete User Journey:

```bash
# 1. Install
pip install structrag-mcp

# 2. Configure
echo 'GROQ_API_KEY=gsk_xxx' > .env

# 3. Use
python3 << 'EOF'
from structrag_mcp.server import ingest_corpus, build_structure, query_structured

# Ingest PDFs
ingest_corpus("my_contracts/")

# Discover schema
build_structure(entity_hints=["Contract", "Party", "Payment"])

# Query
answer = query_structured("What's the total contract value?")
print(answer)
EOF
```

---

## 📝 Files You Need to Add Before Publishing

### 1. MANIFEST.in (Include non-Python files)
```
include LICENSE
include README.md
include .env.example
recursive-include src/structrag_mcp/llm *.txt
```

### 2. Update pyproject.toml
```toml
[project]
name = "structrag-mcp"
version = "0.1.0"  # Semantic versioning
description = "Convert PDFs to queryable SQL using AI-powered schema discovery"
authors = [{name = "Your Name", email = "your@email.com"}]
readme = "README.md"
license = {text = "MIT"}
keywords = ["mcp", "pdf", "sql", "rag", "ai", "llm"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
]

[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/structrag-mcp"
Documentation = "https://github.com/YOUR_USERNAME/structrag-mcp#readme"
Repository = "https://github.com/YOUR_USERNAME/structrag-mcp.git"
Issues = "https://github.com/YOUR_USERNAME/structrag-mcp/issues"
```

### 3. Create CHANGELOG.md
```markdown
# Changelog

## [0.1.0] - 2026-01-12
### Added
- PDF ingestion with semantic chunking
- AI-powered schema discovery
- Natural language to SQL query translation
- Groq LLM integration
- DuckDB storage backend
- MCP server implementation

### Features
- Support for PDF, CSV, TXT documents
- Automatic entity schema discovery
- Provenance tracking
- Query validation and safety checks
```

---

## 🔧 Current Status of Your Package

### ✅ Already Done
- ✅ `pyproject.toml` exists (package configuration)
- ✅ `src/` layout (proper package structure)
- ✅ Dependencies listed
- ✅ Entry points defined
- ✅ `.gitignore` exists
- ✅ LICENSE file exists

### ⚠️ Need to Add (Before Publishing)

1. **Add your info to pyproject.toml:**
   - Your name
   - Your email
   - GitHub repository URL

2. **Update README.md:**
   - Add installation instructions
   - Add quick start example
   - Add MCP configuration example

3. **Test packaging:**
   ```bash
   python -m build
   # Check dist/ folder has .whl and .tar.gz
   ```

4. **Test installation:**
   ```bash
   pip install dist/structrag_mcp-0.1.0-*.whl
   # Verify it works
   ```

---

## 📊 Distribution Comparison

| Method | Ease for Users | Ease for You | Updates | Best For |
|--------|---------------|--------------|---------|----------|
| **PyPI** | ⭐⭐⭐⭐⭐ (pip install) | ⭐⭐⭐ (setup once) | Easy | Public use |
| **GitHub** | ⭐⭐⭐ (git clone) | ⭐⭐⭐⭐⭐ (just push) | Easy | Development |
| **Local** | ⭐ (manual copy) | ⭐⭐⭐⭐⭐ (nothing) | Hard | Your use only |

---

## 🎯 Recommendation: Publish to PyPI

### Why?
1. **Easy for users:** Just `pip install structrag-mcp`
2. **Professional:** Shows on PyPI, searchable
3. **Updates simple:** `pip install --upgrade structrag-mcp`
4. **No setup needed:** Works immediately

### How to Do It (10 minutes)

```bash
# 1. Update pyproject.toml with your details
nano pyproject.toml

# 2. Build package
pip install build twine
python -m build

# 3. Create PyPI account
# Visit: https://pypi.org/account/register/

# 4. Get API token
# Visit: https://pypi.org/manage/account/token/

# 5. Upload
python -m twine upload dist/*
# Enter __token__ as username
# Paste your token as password

# Done! Users can now:
pip install structrag-mcp
```

---

## 🔐 Security Notes

### Don't Include:
- ❌ Your `.env` file (has API keys)
- ❌ Test PDFs with sensitive data
- ❌ Database files (`.db`)
- ❌ `__pycache__/` directories

### Already Protected (in .gitignore):
```
.env
*.db
__pycache__/
*.pdf
data/
```

---

## 📞 Support Options for Users

### Option A: GitHub Issues (Recommended)
```markdown
Users report bugs at:
https://github.com/YOUR_USERNAME/structrag-mcp/issues
```

### Option B: Documentation
```markdown
Create docs/ folder with:
- Installation guide
- Configuration guide  
- API reference
- Troubleshooting
```

### Option C: Examples
```markdown
Create examples/ with:
- Basic usage
- Multi-document analysis
- Custom schemas
- Claude Desktop integration
```

---

## 🎉 Summary

### Current State:
- ✅ Package is **ready to use locally**
- ✅ Can be installed with `pip install -e .`
- ✅ Can be used as MCP server with Claude Desktop

### To Share Publicly:
1. **Easy way:** Push to GitHub → Users clone and install
2. **Professional way:** Publish to PyPI → Users just `pip install`

### Users Would:
```bash
# Install
pip install structrag-mcp  # (if on PyPI)
# OR
git clone https://github.com/YOUR_USERNAME/structrag-mcp.git
cd structrag-mcp
pip install -e .

# Configure
cp .env.example .env
# Add their Groq API key

# Use
python3 -c "
from structrag_mcp.server import ingest_corpus
ingest_corpus('my_pdfs/')
"
```

---

## 💡 Quick Decision

**Do you want to:**

**A. Keep it private (just you):**
- Nothing to do! Current setup works

**B. Share with colleagues:**
- Push to GitHub (private repo)
- Share repo link
- They clone and install

**C. Share publicly:**
- Publish to PyPI (10 minutes)
- Anyone can `pip install structrag-mcp`

**Which one do you want?** 🤔
