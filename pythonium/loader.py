"""
Code loader module for parsing Python files and building a code graph.

This module provides functionality to discover, parse, and analyze Python source
files to build a comprehensive code graph that can be used by detectors.
"""

import ast
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from .models import CodeGraph, Location, Symbol

logger = logging.getLogger(__name__)


class CallVisitor(ast.NodeVisitor):
    """AST visitor to extract function call relationships."""
    
    def __init__(self, file_path: str, graph: CodeGraph):
        self.file_path = file_path
        self.graph = graph
        self.current_function = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition and track calls within it."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition and track calls within it."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call and record the relationship."""
        if self.current_function is not None:
            # Extract called function name
            called_name = self._extract_call_name(node)
            if called_name:
                caller = self.current_function
                if caller not in self.graph.calls:
                    self.graph.calls[caller] = []
                if called_name not in self.graph.calls[caller]:
                    self.graph.calls[caller].append(called_name)
        
        self.generic_visit(node)
    
    def _extract_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract the name of a function being called."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract import relationships."""
    
    def __init__(self, file_path: str, graph: CodeGraph):
        self.file_path = file_path
        self.graph = graph
        self.module_name = self._get_module_name(file_path)
    
    def _get_module_name(self, file_path: str) -> str:
        """Convert file path to module name."""
        # Simple conversion - could be enhanced based on project structure
        path = Path(file_path)
        if path.stem == "__init__":
            return path.parent.name
        return path.stem
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            imported_module = alias.name
            if self.module_name not in self.graph.imports:
                self.graph.imports[self.module_name] = []
            if imported_module not in self.graph.imports[self.module_name]:
                self.graph.imports[self.module_name].append(imported_module)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statement."""
        if node.module:
            imported_module = node.module
            if self.module_name not in self.graph.imports:
                self.graph.imports[self.module_name] = []
            if imported_module not in self.graph.imports[self.module_name]:
                self.graph.imports[self.module_name].append(imported_module)


class InheritanceVisitor(ast.NodeVisitor):
    """AST visitor to extract inheritance relationships."""
    
    def __init__(self, file_path: str, graph: CodeGraph):
        self.file_path = file_path
        self.graph = graph
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition and extract base classes."""
        if node.bases:
            class_name = node.name
            base_names = []
            
            for base in node.bases:
                base_name = self._extract_class_name(base)
                if base_name:
                    base_names.append(base_name)
            
            if base_names:
                self.graph.inheritance[class_name] = base_names
        
        self.generic_visit(node)
    
    def _extract_class_name(self, node: ast.AST) -> Optional[str]:
        """Extract class name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None


class CodeLoader:
    """
    Loads Python source files and builds a code graph.
    
    This class is responsible for discovering Python files, parsing them
    into AST representations, and extracting symbols to build a complete
    code graph for analysis.
    """
    
    def __init__(self, root_path: Union[str, Path]):
        """
        Initialize the code loader.
        
        Args:
            root_path: Root directory containing Python source files
        """
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")
        
        self.graph = CodeGraph()
        self._processed_files: Set[Path] = set()
        self._parse_errors: List[tuple[Path, Exception]] = []
    
    def load(self, paths: Optional[List[Union[str, Path]]] = None) -> CodeGraph:
        """
        Load Python source files and build the code graph with parsed repository.
        
        Args:
            paths: List of files or directories to load. If None, loads all
                  Python files under the root path.
                  
        Returns:
            The populated code graph with parsed repository
            
        Raises:
            ValueError: If no valid Python files are found
        """
        self._reset_state()
        
        if paths is None:
            # Load all Python files under root path
            file_paths = self._discover_python_files(self.root_path)
        else:
            # Convert paths to absolute paths and find all Python files
            file_paths = []
            for path in paths:
                abs_path = Path(path).resolve()
                if abs_path.is_file() and abs_path.suffix == '.py':
                    file_paths.append(abs_path)
                elif abs_path.is_dir():
                    file_paths.extend(self._discover_python_files(abs_path))
                else:
                    logger.warning("Skipping invalid path: %s", path)
        
        if not file_paths:
            logger.warning("No Python files found to process")
            return self.graph
        
        # Phase 1: Build parsed repository
        logger.info("Building parsed repository for %d files...", len(file_paths))
        self._build_parsed_repository(file_paths)
        
        # Phase 2: Extract symbols from parsed repository
        logger.info("Extracting symbols from parsed repository...")
        self._extract_symbols_from_repository()
        
        # Phase 3: Build relationships from parsed repository
        logger.info("Building relationships from parsed repository...")
        self._build_relationships_from_repository()
        
        logger.info(
            "Processed %d/%d Python files successfully (%d symbols, %d files in repository)", 
            len(self.graph.parsed_files), len(file_paths), 
            len(self.graph.symbols), len(self.graph.parsed_files)
        )
        
        if self._parse_errors:
            logger.warning(
                "Failed to parse %d files due to syntax or encoding errors",
                len(self._parse_errors)
            )
        
        return self.graph
    
    def load_file(self, file_path: Union[str, Path]) -> tuple[ast.AST, List[Symbol]]:
        """
        Load a single Python file and return its AST and symbols.
        
        Args:
            file_path: Path to the Python file to load
            
        Returns:
            Tuple of (AST tree, list of symbols)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            SyntaxError: If file has syntax errors
        """
        file_path = Path(file_path).resolve()
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.suffix == '.py':
            raise ValueError(f"Not a Python file: {file_path}")
        
        # Parse the file
        try:
            from .ast_parser import ASTParser
            
            ast_tree = ASTParser.parse_file(str(file_path))
            if ast_tree is None:
                raise SyntaxError(f"Failed to parse {file_path}")
            
            # Read source code for symbol extraction
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Extract symbols
            symbols = self._extract_symbols(ast_tree, file_path, source_code)

            return ast_tree, symbols
            
        except UnicodeDecodeError as e:
            logger.error("Failed to decode file %s: %s", file_path, e)
            raise
        except SyntaxError as e:
            logger.error("Syntax error in file %s: %s", file_path, e)
            raise
    
    def _reset_state(self) -> None:
        """Reset internal state for a fresh load operation."""
        self.graph = CodeGraph()
        self._processed_files.clear()
        self._parse_errors.clear()
    
    def _discover_python_files(self, root: Path) -> List[Path]:
        """
        Discover all Python files in a directory tree.
        
        Args:
            root: Root directory to search
            
        Returns:
            List of Python file paths
        """
        python_files = []
        
        try:
            for path in root.rglob("*.py"):
                # Skip __pycache__ directories and files
                if "__pycache__" in path.parts:
                    continue
                
                # Skip hidden directories (starting with .)
                if any(part.startswith('.') for part in path.parts):
                    continue
                
                python_files.append(path)
        except PermissionError as e:
            logger.warning("Permission denied accessing %s: %s", root, e)
        
        return python_files
    
    def _process_file(self, file_path: Path) -> bool:
        """
        Process a single Python file and add its contents to the code graph.
        
        Args:
            file_path: Path to the Python file to process
            
        Returns:
            True if file was processed successfully, False otherwise
        """
        try:
            # Skip already processed files
            if file_path in self._processed_files:
                return True
            
            logger.debug("Processing file: %s", file_path)
            
            # Read and parse the file using centralized parser
            from .ast_parser import ASTParser
            
            tree = ASTParser.parse_file_with_fallback_encoding(str(file_path))
            if tree is None:
                self._parse_errors.append((file_path, SyntaxError("Failed to parse file")))
                logger.debug("Failed to parse %s", file_path)
                return False
            
            # Calculate the module name
            module_name = self._calculate_module_name(file_path)
            
            # Process the AST
            self._process_ast_node(tree, module_name, file_path)
            
            # Mark file as processed
            self._processed_files.add(file_path)
            return True
            
        except Exception as e:
            self._parse_errors.append((file_path, e))
            logger.error("Error processing %s: %s", file_path, e)
            return False
    
    def _calculate_module_name(self, file_path: Path) -> str:
        """
        Calculate the module name for a given file path.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Module name string
        """
        try:
            rel_path = file_path.relative_to(self.root_path)
        except ValueError:
            # File is outside root_path, use absolute path logic
            rel_path = file_path
        
        module_parts = list(rel_path.parts)
        
        # Handle __init__.py files
        if module_parts[-1] == "__init__.py":
            module_parts = module_parts[:-1]
        else:
            # Remove .py extension
            module_parts[-1] = module_parts[-1][:-3]
        
        return ".".join(module_parts) if module_parts else "__main__"
    
    
    def _process_ast_node(
        self,
        node: ast.AST,
        module_name: str,
        file_path: Path,
        class_stack: Optional[List[str]] = None,
    ) -> None:
        """
        Recursively process an AST node and its children.
        
        Args:
            node: AST node to process
            module_name: Name of the current module
            file_path: Path to the source file
            class_stack: Stack of containing class names
        """
        if class_stack is None:
            class_stack = []
        
        # Create a symbol for functions and classes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbol = self._create_symbol(node, module_name, file_path, class_stack)
            if symbol:
                self.graph.add_symbol(symbol)
        
        # Update class stack for nested processing
        new_class_stack = class_stack.copy()
        if isinstance(node, ast.ClassDef):
            new_class_stack.append(node.name)
        
        # Process child nodes
        self._process_child_nodes(node, module_name, file_path, new_class_stack)
    
    def _create_symbol(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef],
        module_name: str,
        file_path: Path,
        class_stack: List[str],
    ) -> Optional[Symbol]:
        """
        Create a Symbol object from an AST node.
        
        Args:
            node: AST node representing a function or class
            module_name: Name of the containing module
            file_path: Path to the source file
            class_stack: Stack of containing class names
            
        Returns:
            Symbol object or None if creation failed
        """
        try:
            # Build fully qualified name
            name_parts = [module_name] + class_stack + [node.name]
            fqname = ".".join(filter(None, name_parts))
            
            # Create location
            location = Location(
                file=file_path,
                line=node.lineno,
                column=getattr(node, 'col_offset', 0),
                end_line=getattr(node, 'end_lineno', None),
                end_column=getattr(node, 'end_col_offset', None),
            )
            
            # Extract docstring
            docstring = ast.get_docstring(node)
            
            # Create and return symbol
            return Symbol(
                fqname=fqname,
                ast_node=node,
                location=location,
                docstring=docstring,
            )
        
        except Exception as e:
            logger.warning(
                "Failed to create symbol for %s in %s: %s",
                getattr(node, 'name', 'unknown'), file_path, e
            )
            return None
    
    def _process_child_nodes(
        self,
        node: ast.AST,
        module_name: str,
        file_path: Path,
        class_stack: List[str],
    ) -> None:
        """
        Process all child nodes of an AST node.
        
        Args:
            node: Parent AST node
            module_name: Name of the current module
            file_path: Path to the source file
            class_stack: Stack of containing class names
        """
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self._process_ast_node(item, module_name, file_path, class_stack)
            elif isinstance(value, ast.AST):
                self._process_ast_node(value, module_name, file_path, class_stack)
    
    @property
    def parse_errors(self) -> List[tuple[Path, Exception]]:
        """Get list of files that had parse errors."""
        return self._parse_errors.copy()
    
    @property
    def processed_files(self) -> Set[Path]:
        """Get set of successfully processed files."""
        return self._processed_files.copy()
    
    def _extract_symbols(
        self, tree: ast.AST, file_path: Path, source_code: str
    ) -> List[Symbol]:
        """
        Extract symbols from the AST of a Python file.
        
        Args:
            tree: AST tree of the Python file
            file_path: Path to the Python file
            source_code: Source code of the Python file
            
        Returns:
            List of extracted symbols
        """
        symbols: List[Symbol] = []
        
        class StackCollector(ast.NodeVisitor):
            """AST visitor that collects function and class definitions."""
            
            def __init__(self, module_name: str, file_path: Path):
                self.module_name = module_name
                self.file_path = file_path
                self.class_stack: List[str] = []
            
            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                """Visit a class definition node."""
                symbol = _create_symbol(node, self.module_name, self.file_path, self.class_stack)
                if symbol:
                    symbols.append(symbol)
                
                # Enter the class scope
                self.class_stack.append(node.name)
                self.generic_visit(node)
                self.class_stack.pop()
            
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                """Visit a function definition node."""
                symbol = _create_symbol(node, self.module_name, self.file_path, self.class_stack)
                if symbol:
                    symbols.append(symbol)
                
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                """Visit an async function definition node."""
                symbol = _create_symbol(node, self.module_name, self.file_path, self.class_stack)
                if symbol:
                    symbols.append(symbol)
                
                self.generic_visit(node)
        
        def _create_symbol(
            node: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef],
            module_name: str,
            file_path: Path,
            class_stack: List[str],
        ) -> Optional[Symbol]:
            """Create a Symbol object from an AST node."""
            try:
                # Build fully qualified name
                name_parts = [module_name] + class_stack + [node.name]
                fqname = ".".join(filter(None, name_parts))
                
                # Create location
                location = Location(
                    file=file_path,
                    line=node.lineno,
                    column=getattr(node, 'col_offset', 0),
                    end_line=getattr(node, 'end_lineno', None),
                    end_column=getattr(node, 'end_col_offset', None),
                )
                
                # Extract docstring
                docstring = ast.get_docstring(node)
                
                # Create and return symbol
                return Symbol(
                    fqname=fqname,
                    ast_node=node,
                    location=location,
                    docstring=docstring,
                )
            
            except Exception as e:
                logger.warning(
                    "Failed to create symbol for %s in %s: %s",
                    getattr(node, 'name', 'unknown'), file_path, e
                )
                return None
        
        # Collect symbols using the AST visitor
        collector = StackCollector(self._calculate_module_name(file_path), file_path)
        collector.visit(tree)
        
        return symbols

    def _build_parsed_repository(self, file_paths: List[Path]) -> None:
        """
        Parse all files and add them to the CodeGraph repository.
        
        Args:
            file_paths: List of file paths to parse
        """
        from .ast_parser import ASTParser
        
        for file_path in file_paths:
            try:
                # Use centralized AST parser with caching
                ast_tree = ASTParser.parse_file_with_fallback_encoding(str(file_path))
                if ast_tree is None:
                    logger.warning("Failed to parse %s", file_path)
                    continue
                
                # Read content for the repository
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Fallback to latin-1 encoding
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    logger.debug("Used latin-1 encoding for %s", file_path)
                
                # Add to parsed repository
                self.graph.add_parsed_file(str(file_path), ast_tree, content)
                self._processed_files.add(file_path)
                
                logger.debug("Added %s to parsed repository", file_path)
                
            except Exception as e:
                self._parse_errors.append((file_path, e))
                logger.error("Error processing %s: %s", file_path, e)
    
    def _extract_symbols_from_repository(self) -> None:
        """Extract symbols from all files in the parsed repository."""
        for file_path, ast_tree in self.graph.parsed_files.items():
            try:
                # Get content for symbol extraction
                content = self.graph.get_content(file_path)
                if content is None:
                    logger.warning("No content found for %s", file_path)
                    continue
                
                # Extract symbols using the cached AST
                file_symbols = self._extract_symbols(ast_tree, Path(file_path), content)
                
                # Add symbols to graph
                for symbol in file_symbols:
                    self.graph.add_symbol(symbol)
                    
                logger.debug("Extracted %d symbols from %s", len(file_symbols), file_path)
                
            except Exception as e:
                logger.error("Error extracting symbols from %s: %s", file_path, e)
    
    def _build_relationships_from_repository(self) -> None:
        """Build call graphs and other relationships from the parsed repository."""
        for file_path, ast_tree in self.graph.parsed_files.items():
            try:
                # Build relationships using cached AST
                self._analyze_relationships(ast_tree, file_path)
                
            except Exception as e:
                logger.error("Error building relationships for %s: %s", file_path, e)
    
    def _analyze_relationships(self, ast_tree: ast.AST, file_path: str) -> None:
        """
        Analyze relationships in a parsed AST and update the CodeGraph.
        
        Args:
            ast_tree: Pre-parsed AST
            file_path: Path to the source file
        """
        # Extract call relationships
        call_visitor = CallVisitor(file_path, self.graph)
        call_visitor.visit(ast_tree)
        
        # Extract import relationships
        import_visitor = ImportVisitor(file_path, self.graph)
        import_visitor.visit(ast_tree)
        
        # Extract inheritance relationships  
        inheritance_visitor = InheritanceVisitor(file_path, self.graph)
        inheritance_visitor.visit(ast_tree)
