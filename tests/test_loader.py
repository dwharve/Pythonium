"""
Test module for the loader functionality.
"""

import ast
import tempfile
import unittest
from pathlib import Path


class TestCodeLoader(unittest.TestCase):
    """Test case for CodeLoader functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Create multiple test files
        test_contents = [
            (
                "module1.py",
                '''
def function_a():
    """Function in module 1."""
    return "a"

class ClassA:
    """Class in module 1."""
    def method_a(self):
        return "method_a"
'''
            ),
            (
                "module2.py", 
                '''
import module1

def function_b():
    """Function in module 2.""" 
    return module1.function_a()

class ClassB(module1.ClassA):
    """Class in module 2."""
    pass
'''
            ),
            (
                "subdir/__init__.py",
                '''
"""Subdir package."""
'''
            ),
            (
                "subdir/module3.py",
                '''
def function_c():
    """Function in subdir."""
    return "c"
'''
            )
        ]
        
        for filename, content in test_contents:
            filepath = Path(self.temp_dir) / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
            self.test_files.append(filepath)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_loader_creation(self):
        """Test CodeLoader creation."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        self.assertEqual(loader.root_path, Path(self.temp_dir))
        self.assertIsNotNone(loader.graph)
    
    def test_load_all_files(self):
        """Test loading all files in directory."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        graph = loader.load()
        
        self.assertIsNotNone(graph)
        self.assertGreater(len(graph.symbols), 0)
        
        # Check that we loaded symbols from multiple files
        # graph.symbols is a dict mapping fqnames to Symbol objects
        symbol_modules = set()
        for symbol in graph.symbols.values():
            symbol_modules.add(symbol.module_name)
        
        self.assertGreater(len(symbol_modules), 1)
    
    def test_load_specific_files(self):
        """Test loading specific files."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        
        # Load only the first test file
        specific_file = self.test_files[0]
        graph = loader.load([specific_file])
        
        self.assertIsNotNone(graph)
        self.assertGreater(len(graph.symbols), 0)
        
        # Check that symbols are only from the specific file
        for symbol in graph.symbols.values():
            self.assertTrue(symbol.location.file.name == specific_file.name)
    
    def test_load_file_method(self):
        """Test load_file method."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        
        # Load a single file
        test_file = self.test_files[0]
        tree, symbols = loader.load_file(test_file)
        
        self.assertIsInstance(tree, ast.AST)
        self.assertIsInstance(symbols, list)
        self.assertGreater(len(symbols), 0)
    
    def test_discover_python_files(self):
        """Test _discover_python_files method."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        
        # Test discovering files in the temp directory
        python_files = loader._discover_python_files(Path(self.temp_dir))
        
        self.assertIsInstance(python_files, list)
        self.assertGreater(len(python_files), 0)
        
        # All discovered files should be Python files
        for file_path in python_files:
            self.assertTrue(file_path.suffix == '.py')
    
    def test_calculate_module_name(self):
        """Test _calculate_module_name method."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        
        # Test module name calculation for different files
        test_file = Path(self.temp_dir) / "module1.py"
        module_name = loader._calculate_module_name(test_file)
        self.assertEqual(module_name, "module1")
        
        # Test with subdir file
        subdir_file = Path(self.temp_dir) / "subdir" / "module3.py"
        module_name = loader._calculate_module_name(subdir_file)
        self.assertEqual(module_name, "subdir.module3")
        
        # Test with __init__.py
        init_file = Path(self.temp_dir) / "subdir" / "__init__.py"
        module_name = loader._calculate_module_name(init_file)
        self.assertEqual(module_name, "subdir")
    
    def test_process_file_error_handling(self):
        """Test _process_file error handling."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        
        # Test with non-existent file
        non_existent = Path(self.temp_dir) / "non_existent.py"
        result = loader._process_file(non_existent)
        self.assertFalse(result)
        
        # Test with invalid Python syntax
        invalid_file = Path(self.temp_dir) / "invalid.py"
        invalid_file.write_text("invalid python syntax $$$ !!!")
        
        result = loader._process_file(invalid_file)
        self.assertFalse(result)
        
        # Check that parse errors were recorded
        self.assertGreater(len(loader._parse_errors), 0)
    
    def test_process_file_encoding_handling(self):
        """Test _process_file with different encodings."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        
        # Create a file with UTF-8 content
        utf8_file = Path(self.temp_dir) / "utf8_test.py"
        utf8_content = '''
# -*- coding: utf-8 -*-
def test_unicode():
    """Test with unicode: αβγ"""
    return "unicode test"
'''
        utf8_file.write_text(utf8_content, encoding='utf-8')
        
        result = loader._process_file(utf8_file)
        self.assertTrue(result)
    
    def test_load_with_no_python_files(self):
        """Test loading when no Python files exist."""
        from pythonium.loader import CodeLoader
        
        # Create empty directory
        empty_dir = Path(self.temp_dir) / "empty"
        empty_dir.mkdir()
        
        loader = CodeLoader(empty_dir)
        graph = loader.load()
        
        self.assertIsNotNone(graph)
        self.assertEqual(len(graph.symbols), 0)
    
    def test_load_with_already_processed_files(self):
        """Test loading when files are already processed."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        test_file = self.test_files[0]
        
        # Process file first time
        result1 = loader._process_file(test_file)
        self.assertTrue(result1)
        
        # Process same file again - should return True but not reprocess
        result2 = loader._process_file(test_file)
        self.assertTrue(result2)
        
        # File should be in processed files
        self.assertIn(test_file, loader._processed_files)
    
    def test_load_directory_vs_file(self):
        """Test loading directory vs individual file."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        
        # Test with directory
        graph1 = loader.load([Path(self.temp_dir)])
        symbols_from_dir = len(graph1.symbols)
        
        # Reset loader
        loader = CodeLoader(self.temp_dir)
        
        # Test with individual file
        graph2 = loader.load([self.test_files[0]])
        symbols_from_file = len(graph2.symbols)
        
        # Directory should have more symbols than single file
        self.assertGreater(symbols_from_dir, symbols_from_file)
    
    def test_load_with_invalid_path(self):
        """Test loading with invalid paths."""
        from pythonium.loader import CodeLoader
        
        loader = CodeLoader(self.temp_dir)
        
        # Test with non-existent path
        non_existent = Path("/non/existent/path.py")
        graph = loader.load([non_existent])
        
        # Should handle gracefully
        self.assertIsNotNone(graph)


if __name__ == "__main__":
    unittest.main()
