"""
Model Context Protocol (MCP) server implementation for Pythonium code health analysis.

This module has been refactored into a modular structure for better maintainability.
The main implementation is now in the mcp package.
"""


import mcp.server.stdio
import mcp.types

from pythonium.mcp import PythoniumMCPServer

# Re-export for backward compatibility
__all__ = ["PythoniumMCPServer", "main"]

def main():
    """Main entry point for MCP server."""
    import asyncio
    import sys
    import logging
    
    try:
        from pythonium.mcp import PythoniumMCPServer
        
        # Parse arguments for debug flag
        debug_enabled = "--debug" in sys.argv
        
        if not debug_enabled:
            # Setup minimal logging for startup message
            logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
            logging.getLogger("pythonium.mcp").warning("Starting Pythonium MCP Server...")
        
        server = PythoniumMCPServer(debug=debug_enabled)
        
        # Run the server
        if len(sys.argv) > 1 and sys.argv[1] == "--transport":
            transport = sys.argv[2] if len(sys.argv) > 2 else "stdio"
            if transport == "stdio":
                asyncio.run(server.run_stdio())
            else:
                logging.getLogger("pythonium.mcp").error(f"Unsupported transport: {transport}")
                sys.exit(1)
        else:
            # Default to stdio
            asyncio.run(server.run_stdio())
            
    except Exception as e:
        logging.getLogger("pythonium.mcp").error(f"Failed to start MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
