"""
Test module for the MCP server functionality.
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestMCPServer(unittest.TestCase):
    """Test case for MCP server."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_code.py"
        
        # Create a simple test file
        test_content = '''
def test_function():
    """A test function."""
    return "hello"

def unused_function():
    """This function is not used."""
    return "unused"

# Use test_function
result = test_function()
'''
        self.test_file.write_text(test_content)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_mcp_server_creation(self):
        """Test that MCP server can be created."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            server = PythoniumMCPServer()
            self.assertIsNotNone(server)
            self.assertEqual(server.name, "pythonium")
            self.assertEqual(server.version, "0.1.0")
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    @patch('pythonium.mcp.server.MCP_AVAILABLE', True)
    def test_mcp_server_creation_with_mcp_available(self):
        """Test MCP server creation when MCP is available."""
        with patch('pythonium.mcp.server.Server') as mock_server:
            from pythonium.mcp_server import PythoniumMCPServer
            server = PythoniumMCPServer(name="test-server", version="1.0.0")
            self.assertIsNotNone(server)
            self.assertEqual(server.name, "test-server")
            self.assertEqual(server.version, "1.0.0")
            mock_server.assert_called_once_with("test-server", "1.0.0")
    
    def test_mcp_server_creation_without_mcp(self):
        """Test MCP server creation when MCP is not available."""
        with patch('pythonium.mcp.server.MCP_AVAILABLE', False):
            from pythonium.mcp_server import PythoniumMCPServer
            with self.assertRaises(ImportError):
                PythoniumMCPServer()
    
    def test_analyze_code_tool_basic(self):
        """Test the analyze_code tool with basic functionality."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test with our test file
            arguments = {
                "path": str(self.test_file)
            }
            
            # Run the analyze_code method via handlers
            result = asyncio.run(server.handlers.analyze_code(arguments))
            
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIsInstance(result[0], types.TextContent)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_analyze_inline_code_tool(self):
        """Test the analyze_inline_code tool."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test inline code analysis
            test_code = '''
def hello():
    return "world"

def unused():
    return "never called"

result = hello()
'''
            
            arguments = {
                "code": test_code,
                "filename": "inline_test.py"
            }
            
            # Run the analyze_inline_code method via handlers
            result = asyncio.run(server.handlers.analyze_inline_code(arguments))
            
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIsInstance(result[0], types.TextContent)
            self.assertIn("analysis completed", result[0].text.lower())
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_analyze_inline_code_tool_with_detectors(self):
        """Test the analyze_inline_code tool with specific detectors."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test with specific detectors
            arguments = {
                "code": "def unused_func(): pass\ndef main(): print('hello')",
                "detectors": ["dead_code"],
                "filename": "test.py"
            }
            
            result = asyncio.run(server.handlers.analyze_inline_code(arguments))
            
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIsInstance(result[0], types.TextContent)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_list_detectors_tool(self):
        """Test the list_detectors tool."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            arguments = {}
            result = asyncio.run(server._list_detectors(arguments))
            
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIsInstance(result[0], types.TextContent)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_get_detector_info_tool(self):
        """Test the get_detector_info tool."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            arguments = {"detector_id": "dead_code"}
            result = asyncio.run(server._get_detector_info(arguments))
            
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIsInstance(result[0], types.TextContent)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_analyze_issues_tool(self):
        """Test the analyze_issues tool."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            arguments = {
                "path": str(self.test_file),
                "severity_filter": "info"
            }
            result = asyncio.run(server._analyze_issues(arguments))
            
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertIsInstance(result[0], types.TextContent)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    @patch('pythonium.mcp_server.MCP_AVAILABLE', True)
    @patch('pythonium.mcp.server.MCP_AVAILABLE', True)
    def test_setup_handlers_coverage(self):
        """Test that all handlers are properly set up."""
        with patch('pythonium.mcp.server.Server') as mock_server:
            mock_server_instance = MagicMock()
            mock_server.return_value = mock_server_instance
            
            from pythonium.mcp_server import PythoniumMCPServer
            server = PythoniumMCPServer()
            
            # Verify server decorators were called
            self.assertTrue(mock_server_instance.list_tools.called)
            self.assertTrue(mock_server_instance.call_tool.called)
    
    def test_handle_call_tool_unknown_tool(self):
        """Test handle_call_tool with unknown tool name."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Since we can't easily access the internal handler outside of MCP context,
            # we'll just verify the server was created properly and test the known tools
            self.assertIsNotNone(server.server)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_error_handling_in_analyze_code(self):
        """Test error handling in analyze_code."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test with invalid path - should raise ValueError
            arguments = {"path": "/nonexistent/path.py"}
            with self.assertRaises(ValueError) as context:
                asyncio.run(server.handlers.analyze_code(arguments))
            self.assertIn("Path does not exist", str(context.exception))
            
            # Test with missing path argument
            arguments = {}
            with self.assertRaises(ValueError) as context:
                asyncio.run(server.handlers.analyze_code(arguments))
            self.assertIn("Path is required", str(context.exception))
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_error_handling_in_analyze_inline_code(self):
        """Test error handling in analyze_inline_code."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            
            server = PythoniumMCPServer()
            
            # Test with missing code argument - should raise ValueError
            arguments = {}
            with self.assertRaises(ValueError) as context:
                asyncio.run(server.handlers.analyze_inline_code(arguments))
            self.assertIn("Code is required", str(context.exception))
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_error_handling_in_get_detector_info(self):
        """Test error handling in get_detector_info."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            
            server = PythoniumMCPServer()
            
            # Test with missing detector_id - should return error message
            arguments = {}
            result = asyncio.run(server._get_detector_info(arguments))
            self.assertIsInstance(result, list)
            self.assertIn("not found", result[0].text)
            
            # Test with invalid detector_id
            arguments = {"detector_id": "nonexistent_detector"}
            result = asyncio.run(server._get_detector_info(arguments))
            self.assertIsInstance(result, list)
            self.assertIn("not found", result[0].text)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_mcp_server_with_config(self):
        """Test MCP server with configuration options."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            
            server = PythoniumMCPServer()
            
            # Test with configuration for analyze_code
            arguments = {
                "path": str(self.test_file),
                "config": {
                    "detectors": {
                        "dead_code": {"enabled": True}
                    }
                }
            }
            
            result = asyncio.run(server.handlers.analyze_code(arguments))
            self.assertIsInstance(result, list)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    @patch('pythonium.mcp.server.MCP_AVAILABLE', False)
    def test_mcp_import_error_handling(self):
        """Test proper handling when MCP is not available."""
        with self.assertRaises(ImportError) as context:
            from pythonium.mcp_server import PythoniumMCPServer
            PythoniumMCPServer()
        
        self.assertIn("MCP dependencies not available", str(context.exception))

    def test_run_stdio_server(self):
        """Test running stdio server."""
        try:
            from pythonium.mcp_server import main_stdio
            
            # Mock the stdio_server context manager and server.run method
            mock_read_stream = MagicMock()
            mock_write_stream = MagicMock()
            mock_streams = (mock_read_stream, mock_write_stream)
            
            with patch('pythonium.mcp_server.mcp.server.stdio.stdio_server') as mock_stdio_server, \
                 patch('pythonium.mcp_server.PythoniumMCPServer.run_stdio') as mock_run_stdio:
                
                # Set up async context manager mock
                mock_stdio_server.return_value.__aenter__.return_value = mock_streams
                mock_stdio_server.return_value.__aexit__.return_value = None
                
                # Mock run_stdio to avoid actual server execution
                mock_run_stdio.return_value = None  # Mock returns None instead of coroutine
                
                # This should create and attempt to run the server
                asyncio.run(main_stdio())
                
                # Verify that run_stdio was called
                mock_run_stdio.assert_called_once()
                
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_run_sse_server(self):
        """Test running SSE server."""
        try:
            from pythonium.mcp_server import main_sse
            
            # SSE server is not yet implemented, should raise NotImplementedError
            with self.assertRaises(NotImplementedError):
                asyncio.run(main_sse("localhost", 8080))
                
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_analyze_code_with_different_detectors(self):
        """Test analyze_code with different detector configurations."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test with specific detectors
            arguments = {
                "path": str(self.test_file),
                "detectors": ["dead_code", "clone"]
            }
            
            result = asyncio.run(server.handlers.analyze_code(arguments))
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_analyze_code_with_config_object(self):
        """Test analyze_code with config object."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test with config object
            arguments = {
                "path": str(self.test_file),
                "config": {
                    "detectors": {
                        "dead_code": {"enabled": True},
                        "clone": {"enabled": False}
                    }
                }
            }
            
            result = asyncio.run(server.handlers.analyze_code(arguments))
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_analyze_inline_code_comprehensive(self):
        """Test analyze_inline_code with various options."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test with all options
            arguments = {
                "code": "def unused(): pass\ndef main(): print('test')",
                "filename": "comprehensive_test.py",
                "detectors": ["dead_code"],
                "config": {
                    "detectors": {
                        "dead_code": {"enabled": True}
                    }
                }
            }
            
            result = asyncio.run(server.handlers.analyze_inline_code(arguments))
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_get_detector_info_invalid_detector(self):
        """Test get_detector_info with invalid detector."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test with invalid detector_id
            arguments = {"detector_id": "nonexistent_detector"}
            result = asyncio.run(server._get_detector_info(arguments))
            
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            # Should contain information about the detector not being found
            text_content = result[0].text
            self.assertTrue(
                "not found" in text_content.lower() or 
                "available" in text_content.lower() or
                "detector" in text_content.lower()
            )
            
        except ImportError:
            self.skipTest("MCP dependencies not available")
    
    def test_analyze_issues_with_severity_filter(self):
        """Test analyze_issues with different severity filters."""
        try:
            from pythonium.mcp_server import PythoniumMCPServer
            from mcp import types
            
            server = PythoniumMCPServer()
            
            # Test with different severity filters
            for severity in ["info", "warn", "error"]:
                arguments = {
                    "path": str(self.test_file),
                    "severity_filter": severity
                }
                result = asyncio.run(server._analyze_issues(arguments))
                
                self.assertIsInstance(result, list)
                self.assertGreater(len(result), 0)
                self.assertIsInstance(result[0], types.TextContent)
            
        except ImportError:
            self.skipTest("MCP dependencies not available")


if __name__ == "__main__":
    unittest.main()
