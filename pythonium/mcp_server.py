"""
Model Context Protocol (MCP) server implementation for Pythonium code health analysis.

This module has been refactored into a modular structure for better maintainability.
The main implementation is now in the mcp package.
"""

# Check MCP availability early
try:
    import mcp.server.stdio
    import mcp.types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from pythonium.mcp import PythoniumMCPServer

# Re-export for backward compatibility
__all__ = ["PythoniumMCPServer", "MCP_AVAILABLE", "main"]

def main():
    """Main entry point for MCP server."""
    import asyncio
    import sys
    
    try:
        from pythonium.mcp import PythoniumMCPServer
        from pythonium.mcp.debug import logger
        
        logger.info("Starting Pythonium MCP Server...")
        
        server = PythoniumMCPServer()
        
        # Run the server
        if len(sys.argv) > 1 and sys.argv[1] == "--transport":
            transport = sys.argv[2] if len(sys.argv) > 2 else "stdio"
            if transport == "stdio":
                asyncio.run(server.run_stdio())
            else:
                logger.error(f"Unsupported transport: {transport}")
                sys.exit(1)
        else:
            # Default to stdio
            asyncio.run(server.run_stdio())
            
    except Exception as e:
        print(f"Failed to start MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
