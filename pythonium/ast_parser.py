"""
Centralized AST parser with caching support.

This module provides a unified interface for parsing Python files to AST objects,
with built-in caching to avoid re-parsing unchanged files. This improves performance
and ensures consistency across different components that need to parse the same files.
"""

import ast
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ASTParser:
    """Centralized AST parser with caching."""
    
    @staticmethod
    def parse_file(file_path: str) -> Optional[ast.AST]:
        """
        Parse a Python file to AST, using cache when possible.
        
        Args:
            file_path: Path to the Python file to parse
            
        Returns:
            Parsed AST object or None if parsing failed
        """
        from .performance import get_ast_cache
        
        ast_cache = get_ast_cache()
        
        # Try to get from cache first
        if ast_cache:
            cached_ast = ast_cache.get_ast(file_path)
            if cached_ast is not None:
                logger.debug(f"Using cached AST for {file_path}")
                return cached_ast
        
        try:
            # Read and parse the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            ast_node = ast.parse(content, filename=file_path)
            
            # Cache the result
            if ast_cache:
                ast_cache.set_ast(file_path, ast_node, content)
                
            logger.debug(f"Parsed and cached AST for {file_path}")
            return ast_node
            
        except (SyntaxError, OSError, IOError, UnicodeDecodeError) as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None
    
    @staticmethod
    def parse_content(content: str, filename: str = "<string>") -> Optional[ast.AST]:
        """
        Parse Python content directly (no caching for dynamic content).
        
        Args:
            content: Python source code to parse
            filename: Filename to use in error messages
            
        Returns:
            Parsed AST object or None if parsing failed
        """
        try:
            return ast.parse(content, filename=filename)
        except SyntaxError as e:
            logger.error(f"Syntax error in {filename}: {e}")
            return None
    
    @staticmethod
    def parse_file_with_fallback_encoding(file_path: str) -> Optional[ast.AST]:
        """
        Parse a Python file with fallback encoding support.
        
        This method tries UTF-8 first, then falls back to latin-1 encoding
        for files that can't be decoded with UTF-8.
        
        Args:
            file_path: Path to the Python file to parse
            
        Returns:
            Parsed AST object or None if parsing failed
        """
        from .performance import get_ast_cache
        
        ast_cache = get_ast_cache()
        
        # Try to get from cache first
        if ast_cache:
            cached_ast = ast_cache.get_ast(file_path)
            if cached_ast is not None:
                logger.debug(f"Using cached AST for {file_path}")
                return cached_ast
        
        content = None
        
        # Try UTF-8 encoding first
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                logger.debug(f"Used latin-1 encoding for {file_path}")
            except (OSError, IOError) as e:
                logger.error(f"Error reading {file_path}: {e}")
                return None
        except (OSError, IOError) as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
        
        if content is None:
            return None
        
        try:
            ast_node = ast.parse(content, filename=file_path)
            
            # Cache the result
            if ast_cache:
                ast_cache.set_ast(file_path, ast_node, content)
                
            logger.debug(f"Parsed and cached AST for {file_path}")
            return ast_node
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return None
