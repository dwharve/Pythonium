# Creating Custom Detectors for Pythonium

This guide explains how to create custom detectors for the Pythonium static analysis tool. Detectors are the core components that analyze Python code and identify potential issues.

## Table of Contents

1. [Overview](#overview)
2. [Detector Architecture](#detector-architecture)
3. [Creating Your First Detector](#creating-your-first-detector)
4. [Advanced Features](#advanced-features)
5. [Testing Your Detector](#testing-your-detector)
6. [Integration and Distribution](#integration-and-distribution)
7. [Best Practices](#best-practices)
8. [Examples](#examples)

## Overview

Pythonium detectors are Python classes that analyze the code graph and return a list of issues. Each detector focuses on a specific type of code health problem, such as:

- Dead code
- Code duplication
- Security vulnerabilities
- Complexity issues
- API consistency
- And more...

## Detector Architecture

### Core Components

Every detector must implement the `Detector` protocol which requires:

- `id`: Unique identifier for the detector
- `name`: Human-readable name
- `description`: Description of what it detects
- `analyze(graph: CodeGraph) -> List[Issue]`: The main analysis method

### Base Classes

Pythonium provides a `BaseDetector` class that offers common functionality:

```python
from pythonium.detectors import BaseDetector
from pythonium.models import CodeGraph, Issue, Location
```

## Creating Your First Detector

### Step 1: Create the Detector File

Create a new Python file in the `pythonium/detectors/` directory:

```python
# pythonium/detectors/my_detector.py
"""
My Custom Detector

This detector identifies [describe what your detector finds].
"""

import ast
import logging
from typing import List, Set, Dict, Optional
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector

logger = logging.getLogger(__name__)

class MyCustomDetector(BaseDetector):
    """
    Detects [specific code issues].
    
    This detector analyzes [what it analyzes] and identifies [what it finds].
    
    Attributes:
        threshold: Configurable threshold for detection sensitivity
        ignore_patterns: Patterns to ignore during analysis
    """
    
    id = "my_custom"
    name = "My Custom Detector"
    description = "Detects custom code issues"
    category = "Code Quality"  # or "Security & Safety", "Code Duplication", etc.
    usage_tips = "Run this detector to find [specific issues]"
    typical_severity = "warn"  # "error", "warn", or "info"
    
    def __init__(self, settings=None, **options):
        """Initialize the detector with configuration options."""
        super().__init__(settings, **options)
        self.threshold = options.get('threshold', 5)
        self.ignore_patterns = options.get('ignore_patterns', [])
    
    def analyze(self, graph: CodeGraph) -> List[Issue]:
        """
        Analyze the code graph and return issues.
        
        Args:
            graph: The code graph containing all symbols and relationships
            
        Returns:
            List of issues found during analysis
        """
        issues = []
        
        # Iterate through all files in the graph
        for file_path, symbols in graph.files.items():
            # Skip files matching ignore patterns
            if self._should_ignore_file(file_path):
                continue
                
            # Analyze symbols in this file
            file_issues = self._analyze_file(file_path, symbols, graph)
            issues.extend(file_issues)
        
        logger.info(f"MyCustomDetector found {len(issues)} issues")
        return issues
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if a file should be ignored based on ignore patterns."""
        import fnmatch
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(str(file_path), pattern):
                return True
        return False
    
    def _analyze_file(self, file_path: Path, symbols: List[Symbol], graph: CodeGraph) -> List[Issue]:
        """Analyze a single file for issues."""
        issues = []
        
        for symbol in symbols:
            # Implement your detection logic here
            if self._is_problematic(symbol, graph):
                issue = Issue(
                    id=f"{self.id}_{symbol.name}",
                    detector=self.id,
                    message=f"Found issue with {symbol.name}: [describe the issue]",
                    severity="warn",  # "error", "warn", or "info"
                    location=Location(
                        file=file_path,
                        line=symbol.start_line,
                        column=symbol.start_column,
                        end_line=symbol.end_line,
                        end_column=symbol.end_column
                    ),
                    metadata={
                        "symbol_type": symbol.type,
                        "symbol_name": symbol.name,
                        "custom_data": "additional_info"
                    }
                )
                issues.append(issue)
        
        return issues
    
    def _is_problematic(self, symbol: Symbol, graph: CodeGraph) -> bool:
        """Determine if a symbol represents a problem."""
        # Implement your specific detection logic here
        # This is where you analyze the symbol and determine if it's problematic
        
        # Example: Check if a function is too complex
        if symbol.type == "function":
            complexity = self._calculate_complexity(symbol)
            return complexity > self.threshold
        
        return False
    
    def _calculate_complexity(self, symbol: Symbol) -> int:
        """Calculate complexity metric for a symbol."""
        # Implement your complexity calculation
        # This could be cyclomatic complexity, lines of code, etc.
        return len(symbol.body) if hasattr(symbol, 'body') else 0
```

### Step 2: Register the Detector

Add your detector to the `__init__.py` file:

```python
# pythonium/detectors/__init__.py

# Add this import
from .my_detector import MyCustomDetector

# Add to the AVAILABLE_DETECTORS list
AVAILABLE_DETECTORS = [
    # ... existing detectors ...
    MyCustomDetector,
]
```

## Advanced Features

### Configuration Support

Detectors can be configured through the `.pythonium.yml` file:

```yaml
detectors:
  my_custom:
    enabled: true
    threshold: 10
    ignore_patterns:
      - "**/test_*.py"
      - "**/__init__.py"
```

Access configuration in your detector:

```python
def __init__(self, settings=None, **options):
    super().__init__(settings, **options)
    config = settings.get('detectors', {}).get('my_custom', {}) if settings else {}
    
    self.threshold = config.get('threshold', options.get('threshold', 5))
    self.ignore_patterns = config.get('ignore_patterns', options.get('ignore_patterns', []))
```

### AST Analysis

For complex analysis, you can work directly with the AST:

```python
def _analyze_ast(self, symbol: Symbol) -> bool:
    """Analyze the AST of a symbol."""
    if not symbol.ast_node:
        return False
    
    # Use AST visitors to analyze the code
    class ComplexityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.complexity = 1
        
        def visit_If(self, node):
            self.complexity += 1
            self.generic_visit(node)
        
        def visit_For(self, node):
            self.complexity += 1
            self.generic_visit(node)
        
        def visit_While(self, node):
            self.complexity += 1
            self.generic_visit(node)
    
    visitor = ComplexityVisitor()
    visitor.visit(symbol.ast_node)
    return visitor.complexity > self.threshold
```

### Cross-Reference Analysis

Analyze relationships between symbols:

```python
def _analyze_dependencies(self, symbol: Symbol, graph: CodeGraph) -> bool:
    """Analyze symbol dependencies."""
    # Find all symbols that reference this symbol
    references = graph.get_references(symbol)
    
    # Find all symbols this symbol references
    dependencies = graph.get_dependencies(symbol)
    
    # Implement your logic based on relationships
    return len(references) == 0  # Example: unused symbol
```

## Testing Your Detector

### Unit Tests

Create comprehensive tests for your detector:

```python
# tests/test_my_detector.py
import unittest
import tempfile
from pathlib import Path
from pythonium.detectors.my_detector import MyCustomDetector
from pythonium.analyzer import Analyzer

class TestMyCustomDetector(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.detector = MyCustomDetector()
    
    def test_detects_issue(self):
        """Test that the detector finds the expected issue."""
        # Create test code with known issues
        test_code = '''
def complex_function():
    if True:
        if True:
            if True:
                if True:
                    if True:
                        return "very complex"
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(test_code)
        
        # Analyze the code
        analyzer = Analyzer(root_path=Path(self.temp_dir))
        graph = analyzer._build_graph()
        issues = self.detector.analyze(graph)
        
        # Assert issues were found
        self.assertGreater(len(issues), 0)
        self.assertEqual(issues[0].detector, "my_custom")
    
    def test_ignores_simple_code(self):
        """Test that the detector ignores simple code."""
        test_code = '''
def simple_function():
    return "hello"
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(test_code)
        
        analyzer = Analyzer(root_path=Path(self.temp_dir))
        graph = analyzer._build_graph()
        issues = self.detector.analyze(graph)
        
        # Assert no issues were found
        self.assertEqual(len(issues), 0)
    
    def test_configuration(self):
        """Test detector configuration."""
        detector = MyCustomDetector(threshold=10)
        self.assertEqual(detector.threshold, 10)
```

### Integration Tests

Test your detector with the full analysis pipeline:

```python
def test_full_analysis_integration(self):
    """Test detector integration with full analysis."""
    from pythonium.cli import main
    import sys
    from io import StringIO
    
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        # Run analysis with your detector
        main(['crawl', self.temp_dir, '--format', 'json'])
        output = captured_output.getvalue()
        
        # Verify your detector ran and found issues
        self.assertIn('my_custom', output)
    finally:
        sys.stdout = old_stdout
```

## Integration and Distribution

### Adding to Core

To add your detector to the core Pythonium distribution:

1. Follow the code structure above
2. Add comprehensive tests
3. Update documentation
4. Submit a pull request

### Custom Plugins

For standalone detectors, create a plugin package:

```python
# setup.py for your plugin
from setuptools import setup, find_packages

setup(
    name="pythonium-my-detector",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["pythonium"],
    entry_points={
        "pythonium.detectors": [
            "my_custom = my_detector_package:MyCustomDetector"
        ]
    }
)
```

## Best Practices

### Performance

1. **Efficient Analysis**: Minimize expensive operations
2. **Early Returns**: Skip unnecessary analysis when possible
3. **Caching**: Cache expensive computations
4. **Batch Processing**: Process multiple symbols together when beneficial

```python
def analyze(self, graph: CodeGraph) -> List[Issue]:
    # Use early returns to skip unnecessary work
    if not graph.files:
        return []
    
    # Cache expensive computations
    if not hasattr(self, '_complexity_cache'):
        self._complexity_cache = {}
    
    # Process in batches for efficiency
    issues = []
    for file_batch in self._batch_files(graph.files.items()):
        batch_issues = self._analyze_batch(file_batch, graph)
        issues.extend(batch_issues)
    
    return issues
```

### Error Handling

1. **Graceful Degradation**: Handle parsing errors gracefully
2. **Logging**: Log warnings and errors appropriately
3. **Validation**: Validate inputs and configuration

```python
def _analyze_file(self, file_path: Path, symbols: List[Symbol], graph: CodeGraph) -> List[Issue]:
    try:
        # Your analysis logic
        return self._do_analysis(file_path, symbols, graph)
    except Exception as e:
        logger.warning(f"Error analyzing {file_path}: {e}")
        return []  # Return empty list instead of crashing
```

### User Experience

1. **Clear Messages**: Write helpful, actionable issue messages
2. **Metadata**: Include relevant metadata in issues
3. **Configuration**: Make detectors configurable
4. **Documentation**: Document configuration options and behavior

```python
# Good issue message
Issue(
    message=f"Function '{symbol.name}' has cyclomatic complexity {complexity} "
            f"(threshold: {self.threshold}). Consider breaking it into smaller functions.",
    # ... other fields
)

# Bad issue message
Issue(
    message=f"Function too complex",
    # ... other fields
)
```

## Examples

### Example 1: Long Function Detector

```python
class LongFunctionDetector(BaseDetector):
    """Detects functions that are too long."""
    
    id = "long_function"
    name = "Long Function Detector"
    description = "Identifies functions with too many lines"
    
    def __init__(self, settings=None, **options):
        super().__init__(settings, **options)
        self.max_lines = options.get('max_lines', 50)
    
    def analyze(self, graph: CodeGraph) -> List[Issue]:
        issues = []
        
        for file_path, symbols in graph.files.items():
            for symbol in symbols:
                if symbol.type == "function":
                    line_count = symbol.end_line - symbol.start_line + 1
                    if line_count > self.max_lines:
                        issues.append(Issue(
                            id=f"long_function_{symbol.name}",
                            detector=self.id,
                            message=f"Function '{symbol.name}' is {line_count} lines long "
                                   f"(max: {self.max_lines}). Consider breaking it into smaller functions.",
                            severity="warn",
                            location=Location(
                                file=file_path,
                                line=symbol.start_line,
                                column=symbol.start_column
                            ),
                            metadata={"line_count": line_count, "max_lines": self.max_lines}
                        ))
        
        return issues
```

### Example 2: Magic Number Detector

```python
class MagicNumberDetector(BaseDetector):
    """Detects magic numbers in code."""
    
    id = "magic_number"
    name = "Magic Number Detector"
    description = "Identifies magic numbers that should be constants"
    
    def __init__(self, settings=None, **options):
        super().__init__(settings, **options)
        self.allowed_numbers = set(options.get('allowed_numbers', [0, 1, -1]))
    
    def analyze(self, graph: CodeGraph) -> List[Issue]:
        issues = []
        
        for file_path, symbols in graph.files.items():
            # Parse the file to find numeric literals
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                visitor = MagicNumberVisitor(self.allowed_numbers)
                visitor.visit(tree)
                
                for number, line, col in visitor.magic_numbers:
                    issues.append(Issue(
                        id=f"magic_number_{file_path.name}_{line}",
                        detector=self.id,
                        message=f"Magic number {number} found. Consider using a named constant.",
                        severity="info",
                        location=Location(file=file_path, line=line, column=col),
                        metadata={"number": number}
                    ))
            
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
        
        return issues

class MagicNumberVisitor(ast.NodeVisitor):
    def __init__(self, allowed_numbers):
        self.allowed_numbers = allowed_numbers
        self.magic_numbers = []
    
    def visit_Num(self, node):  # Python < 3.8
        if node.n not in self.allowed_numbers:
            self.magic_numbers.append((node.n, node.lineno, node.col_offset))
    
    def visit_Constant(self, node):  # Python >= 3.8
        if isinstance(node.value, (int, float)) and node.value not in self.allowed_numbers:
            self.magic_numbers.append((node.value, node.lineno, node.col_offset))
```

## Conclusion

Creating custom detectors for Pythonium allows you to extend the tool's capabilities to match your specific code quality requirements. By following this guide and the best practices outlined, you can create robust, efficient, and user-friendly detectors that integrate seamlessly with the Pythonium ecosystem.

Remember to:
- Start simple and iterate
- Write comprehensive tests
- Document your detector's behavior
- Handle edge cases gracefully
- Consider performance implications
- Make your detector configurable

Happy detecting!
