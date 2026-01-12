#!/bin/bash
# Installation script for StructRAG MCP

set -e

echo "🚀 Installing StructRAG MCP..."

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $python_version detected"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "📦 Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✓ Poetry available"

# Install dependencies
echo "📦 Installing dependencies..."
poetry install

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and add your OPENAI_API_KEY"
echo "2. Run: poetry run python -m structrag_mcp.server"
echo "3. Or add to Claude Desktop config (see README.md)"
