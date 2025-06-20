"""
Core data models for Pythonium.

This module defines the fundamental data structures used throughout the
pythonium analysis system, including code symbols, issues, and the
code graph representation.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


@dataclass(frozen=True)
class Location:
    """
    Represents a location in source code.
    
    Attributes:
        file: Path to the source file
        line: Line number (1-indexed)
        column: Column number (0-indexed, optional)
        end_line: End line number for multi-line constructs (optional)
        end_column: End column number (optional)
    """
    file: Path
    line: int
    column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    
    def __str__(self) -> str:
        """Return human-readable location string."""
        location = f"{self.file}:{self.line}"
        if self.column:
            location += f":{self.column}"
        return location


@dataclass
class Symbol:
    """
    Represents a code symbol (function, class, method, variable, etc.).
    
    Attributes:
        fqname: Fully qualified name (e.g., "package.module.Class.method")
        ast_node: Associated AST node
        location: Source location of the symbol
        docstring: Documentation string if available
        references: Set of fqnames that reference this symbol
        metadata: Additional symbol-specific metadata
    """
    fqname: str
    ast_node: ast.AST
    location: Location
    docstring: Optional[str] = None
    references: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash based on unique identifier components."""
        return hash((self.fqname, str(self.location.file), self.location.line))
    
    @property
    def name(self) -> str:
        """Get the simple name (last component of fqname)."""
        return self.fqname.split('.')[-1]
    
    @property
    def module_name(self) -> str:
        """Get the module name (all components except the last)."""
        parts = self.fqname.split('.')
        return '.'.join(parts[:-1]) if len(parts) > 1 else ''


@dataclass
class Issue:
    """
    Represents an issue found by a detector.
    
    Attributes:
        id: Unique issue identifier (e.g., "dead_code.unused_function")
        severity: Issue severity level ("info", "warn", or "error")
        message: Human-readable description of the issue
        symbol: Associated symbol (optional)
        location: Source location (optional, derived from symbol if not provided)
        detector_id: ID of the detector that found this issue
        metadata: Additional issue-specific metadata
    """
    id: str
    severity: str
    message: str
    symbol: Optional[Symbol] = None
    location: Optional[Location] = None
    detector_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize computed fields."""
        # Use symbol's location if location not provided
        if self.location is None and self.symbol is not None:
            self.location = self.symbol.location
        
        # Validate severity
        if self.severity not in {"info", "warn", "error"}:
            raise ValueError(f"Invalid severity: {self.severity}")


@dataclass
class CodeGraph:
    """
    Represents the complete codebase as a graph of symbols and relationships.
    
    This is the primary data structure that contains all discovered symbols
    and their interconnections, used by detectors to perform analysis.
    
    Attributes:
        symbols: Mapping from fully qualified names to Symbol objects
        modules: Mapping from module paths to sets of symbol names
    """
    symbols: Dict[str, Symbol] = field(default_factory=dict)
    modules: Dict[str, Set[str]] = field(default_factory=dict)
    
    def add_symbol(self, symbol: Symbol) -> None:
        """
        Add a symbol to the code graph.
        
        Args:
            symbol: Symbol to add
        """
        self.symbols[symbol.fqname] = symbol
        
        # Track symbols by module
        module_name = symbol.module_name
        if module_name not in self.modules:
            self.modules[module_name] = set()
        self.modules[module_name].add(symbol.fqname)
    
    def get_symbol(self, fqname: str) -> Optional[Symbol]:
        """
        Get a symbol by its fully qualified name.
        
        Args:
            fqname: Fully qualified symbol name
            
        Returns:
            Symbol if found, None otherwise
        """
        return self.symbols.get(fqname)
    
    def find_symbols(self, pattern: str) -> List[Symbol]:
        """
        Find symbols matching a glob pattern.
        
        Args:
            pattern: Glob pattern to match against symbol names
            
        Returns:
            List of matching symbols
        """
        from fnmatch import fnmatch
        return [s for name, s in self.symbols.items() if fnmatch(name, pattern)]
    
    def get_symbols_by_type(self, node_type: Union[type, tuple]) -> List[Symbol]:
        """
        Get symbols by their AST node type.
        
        Args:
            node_type: AST node type or tuple of types
            
        Returns:
            List of symbols with matching AST node types
        """
        return [s for s in self.symbols.values() if isinstance(s.ast_node, node_type)]
    
    def get_module_symbols(self, module_name: str) -> List[Symbol]:
        """
        Get all symbols in a specific module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            List of symbols in the module
        """
        symbol_names = self.modules.get(module_name, set())
        return [self.symbols[name] for name in symbol_names if name in self.symbols]
    
    @property
    def symbol_count(self) -> int:
        """Get total number of symbols."""
        return len(self.symbols)
    
    @property
    def module_count(self) -> int:
        """Get total number of modules."""
        return len(self.modules)
