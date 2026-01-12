#!/usr/bin/env python3
"""
Quick validation script to check if StructRAG MCP is properly installed
"""

import sys
import importlib

def check_import(module_name, friendly_name):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✓ {friendly_name}")
        return True
    except ImportError as e:
        print(f"✗ {friendly_name}: {str(e)}")
        return False

def main():
    print("🔍 Validating StructRAG MCP Installation...\n")
    
    # Check Python version
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.11+)")
        return False
    
    # Check core dependencies
    checks = [
        ("duckdb", "DuckDB"),
        ("tiktoken", "tiktoken"),
        ("pydantic", "Pydantic"),
        ("openai", "OpenAI SDK"),
        ("pypdf", "pypdf"),
        ("pandas", "pandas"),
        ("mcp.server.fastmcp", "FastMCP"),
    ]
    
    all_passed = True
    for module, name in checks:
        if not check_import(module, name):
            all_passed = False
    
    print()
    
    # Check StructRAG modules
    structrag_modules = [
        ("structrag_mcp.ingestion", "Ingestion"),
        ("structrag_mcp.storage", "Storage"),
        ("structrag_mcp.structure", "Structure"),
        ("structrag_mcp.query", "Query"),
        ("structrag_mcp.llm", "LLM"),
    ]
    
    for module, name in structrag_modules:
        if not check_import(module, f"StructRAG {name}"):
            all_passed = False
    
    print()
    
    if all_passed:
        print("✅ All checks passed! StructRAG MCP is ready to use.")
        print("\nNext steps:")
        print("1. Set OPENAI_API_KEY in .env file")
        print("2. Run: python -m structrag_mcp.server")
        return True
    else:
        print("❌ Some checks failed. Run: pip install -e .")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
