"""Entry point for running StructRAG MCP server as a module"""

if __name__ == "__main__":
    from structrag_mcp.server import mcp
    mcp.run()
