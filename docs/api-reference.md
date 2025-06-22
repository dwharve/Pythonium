# Python API Reference

Complete reference for using Pythonium programmatically in Python applications.

## Installation

```bash
pip install pythonium

# With optional dependencies
pip install pythonium[mcp]  # For MCP server
pip install pythonium[dev]  # For development tools
```

## Quick Start

```python
from pythonium import Analyzer
from pathlib import Path

# Create analyzer
analyzer = Analyzer(root_path=Path("my_project/"))

# Run analysis
issues = analyzer.analyze()

# Process results
for issue in issues:
    print(f"{issue.severity}: {issue.message}")
```

## Core Classes

### Analyzer

The main analysis class that coordinates code loading, detector execution, and result aggregation.

#### Constructor

```python
Analyzer(
    root_path: Path,
    config: Optional[Dict] = None,
    settings: Optional[Settings] = None
)
```

**Parameters:**
- `root_path` - Root directory for analysis
- `config` - Configuration dictionary (overrides file-based config)
- `settings` - Settings instance (created from config if not provided)

**Example:**
```python
from pythonium import Analyzer
from pathlib import Path

# Basic usage
analyzer = Analyzer(root_path=Path("src/"))

# With configuration
config = {
    "detectors": {
        "dead_code": {"enabled": True},
        "security_smell": {"enabled": True}
    }
}
analyzer = Analyzer(root_path=Path("src/"), config=config)
```

#### Methods

##### `analyze(paths: Optional[List[Path]] = None) -> List[Issue]`

Run analysis on specified paths or entire root directory.

**Parameters:**
- `paths` - Specific files/directories to analyze (optional)

**Returns:**
- List of `Issue` objects

**Example:**
```python
# Analyze entire project
all_issues = analyzer.analyze()

# Analyze specific files
specific_issues = analyzer.analyze([
    Path("src/main.py"),
    Path("src/utils/")
])
```

##### `list_detectors() -> Dict[str, DetectorInfo]`

Get information about available detectors.

**Returns:**
- Dictionary mapping detector IDs to detector information

**Example:**
```python
detectors = analyzer.list_detectors()
for detector_id, info in detectors.items():
    print(f"{detector_id}: {info['name']}")
    print(f"  Description: {info['description']}")
    print(f"  Type: {info['type']}")
```

##### `load_detectors_from_entry_points()`

Load detectors from setuptools entry points.

##### `load_default_detectors()`

Load built-in detectors from the detectors package.

### Issue

Represents a single code health issue found during analysis.

#### Attributes

```python
class Issue:
    id: str                          # Unique issue identifier
    severity: str                    # "error", "warn", or "info"
    message: str                     # Human-readable description
    symbol: Optional[Symbol]         # Related symbol (if any)
    location: Optional[Location]     # Source location
    detector_id: str                 # Detector that found this issue
    metadata: Dict[str, Any]         # Additional metadata
```

#### Example

```python
# Working with issues
for issue in issues:
    print(f"ID: {issue.id}")
    print(f"Severity: {issue.severity}")
    print(f"Message: {issue.message}")
    
    if issue.location:
        print(f"File: {issue.location.file}")
        print(f"Line: {issue.location.line}")
    
    if issue.symbol:
        print(f"Symbol: {issue.symbol.fqname}")
    
    # Access detector-specific metadata
    if issue.detector_id == "security_smell":
        pattern = issue.metadata.get("pattern")
        if pattern:
            print(f"Pattern: {pattern}")
```

### Symbol

Represents a code symbol (function, class, variable, etc.).

#### Attributes

```python
class Symbol:
    name: str                        # Symbol name
    fqname: str                      # Fully qualified name
    type: str                        # "function", "class", "variable", etc.
    location: Location               # Source location
    references: List[Location]       # Where symbol is referenced
    ast_node: Optional[ast.AST]      # AST node (if available)
    metadata: Dict[str, Any]         # Additional metadata
```

#### Example

```python
# Analyzing symbols
graph = analyzer._build_graph()
for file_path, symbols in graph.files.items():
    for symbol in symbols:
        print(f"Symbol: {symbol.fqname}")
        print(f"Type: {symbol.type}")
        print(f"Location: {symbol.location.file}:{symbol.location.line}")
        print(f"References: {len(symbol.references)}")
```

### Location

Represents a location in source code.

#### Attributes

```python
class Location:
    file: Path                       # File path
    line: int                        # Line number (1-based)
    column: Optional[int]            # Column number (0-based)
    end_line: Optional[int]          # End line number
    end_column: Optional[int]        # End column number
```

### CodeGraph

Represents the analyzed code structure with symbols and relationships.

#### Attributes

```python
class CodeGraph:
    files: Dict[Path, List[Symbol]]  # Symbols by file
    symbols: Dict[str, Symbol]       # All symbols by fully qualified name
    references: Dict[str, Set[str]]  # Symbol reference relationships
```

#### Methods

##### `get_references(symbol: Symbol) -> List[Symbol]`

Get symbols that reference the given symbol.

##### `get_dependencies(symbol: Symbol) -> List[Symbol]`

Get symbols that the given symbol depends on.

### Settings

Configuration management class.

#### Constructor

```python
Settings(
    config_dict: Optional[Dict] = None,
    config_file: Optional[Path] = None
)
```

#### Methods

##### `get_detector_options(detector_id: str) -> Dict[str, Any]`

Get configuration options for a specific detector.

##### `is_detector_enabled(detector_id: str) -> bool`

Check if a detector is enabled.

##### `get_severity_override(detector_id: str, issue_id: str) -> Optional[str]`

Get severity override for specific issue types.

## Detector Development

### BaseDetector

Base class for creating custom detectors.

```python
from pythonium.detectors import BaseDetector
from pythonium.models import CodeGraph, Issue

class MyDetector(BaseDetector):
    id = "my_detector"
    name = "My Custom Detector"
    description = "Detects custom issues"
    
    def __init__(self, settings=None, **options):
        super().__init__(settings, **options)
        self.threshold = options.get('threshold', 5)
    
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        issues = []
        
        for file_path, symbols in graph.files.items():
            for symbol in symbols:
                if self._is_problematic(symbol):
                    issue = self.create_issue(
                        issue_id=f"problematic_{symbol.name}",
                        message=f"Symbol {symbol.name} is problematic",
                        severity="warn",
                        symbol=symbol
                    )
                    issues.append(issue)
        
        return issues
    
    def _is_problematic(self, symbol: Symbol) -> bool:
        # Your detection logic here
        return False
```

### Detector Protocol

All detectors must implement the `Detector` protocol:

```python
from typing import Protocol
from pythonium.models import CodeGraph, Issue

class Detector(Protocol):
    id: str
    name: str
    description: str
    
    def analyze(self, graph: CodeGraph) -> List[Issue]:
        ...
```

## Advanced Usage

### Custom Analysis Pipeline

```python
from pythonium import Analyzer
from pythonium.loader import CodeLoader
from pythonium.models import CodeGraph
from pathlib import Path

# Custom analysis pipeline
class CustomAnalyzer:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.loader = CodeLoader(root_path)
    
    def analyze_with_custom_logic(self):
        # Load code
        files = self.loader.discover_python_files([self.root_path])
        graph = CodeGraph()
        
        for file_path in files:
            symbols = self.loader.load_file(file_path)
            graph.files[file_path] = symbols
        
        # Custom analysis logic
        issues = []
        for file_path, symbols in graph.files.items():
            # Your custom analysis
            pass
        
        return issues
```

### Filtering and Processing

```python
from typing import List
from pythonium.models import Issue

def filter_issues(issues: List[Issue], **filters) -> List[Issue]:
    """Filter issues by various criteria."""
    filtered = issues
    
    if 'severity' in filters:
        severity = filters['severity']
        filtered = [i for i in filtered if i.severity == severity]
    
    if 'detector' in filters:
        detector = filters['detector']
        filtered = [i for i in filtered if i.detector_id == detector]
    
    if 'file_pattern' in filters:
        import fnmatch
        pattern = filters['file_pattern']
        filtered = [
            i for i in filtered 
            if i.location and fnmatch.fnmatch(str(i.location.file), pattern)
        ]
    
    return filtered

# Usage
issues = analyzer.analyze()
security_issues = filter_issues(issues, detector='security_smell')
critical_issues = filter_issues(issues, severity='error')
```

### Async Analysis

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List
from pathlib import Path

class AsyncAnalyzer:
    def __init__(self, root_path: Path, max_workers: int = 4):
        self.root_path = root_path
        self.max_workers = max_workers
    
    async def analyze_async(self, paths: List[Path]) -> List[Issue]:
        """Analyze multiple paths concurrently."""
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            tasks = []
            for path in paths:
                analyzer = Analyzer(root_path=path)
                task = loop.run_in_executor(executor, analyzer.analyze)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
        
        # Flatten results
        all_issues = []
        for issues in results:
            all_issues.extend(issues)
        
        return all_issues

# Usage
async def main():
    analyzer = AsyncAnalyzer(Path("."))
    paths = [Path("src/"), Path("tests/")]
    issues = await analyzer.analyze_async(paths)
    print(f"Found {len(issues)} issues")

# Run async analysis
asyncio.run(main())
```

### Caching

```python
from pythonium.performance import AnalysisCache

# Use caching for faster repeated analysis
cache = AnalysisCache(cache_path=Path(".pythonium/cache.db"))

# Check if file needs re-analysis
file_path = Path("src/main.py")
cached_symbols = cache.get_cached_symbols(file_path)

if cached_symbols is None:
    # File not in cache or modified, analyze it
    symbols = loader.load_file(file_path)
    cache.cache_symbols(file_path, symbols)
else:
    # Use cached symbols
    symbols = cached_symbols
```

### Integration with Other Tools

#### Pytest Plugin

```python
import pytest
from pythonium import Analyzer
from pathlib import Path

def pytest_configure(config):
    """Run Pythonium analysis before tests."""
    if config.getoption("--pythonium"):
        analyzer = Analyzer(root_path=Path.cwd())
        issues = analyzer.analyze()
        
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            print(f"Found {len(errors)} code quality errors:")
            for issue in errors[:5]:  # Show first 5
                print(f"  {issue.location.file}:{issue.location.line}: {issue.message}")
            
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")

def pytest_addoption(parser):
    parser.addoption(
        "--pythonium",
        action="store_true",
        help="Run Pythonium analysis before tests"
    )
```

#### Flask Web Interface

```python
from flask import Flask, jsonify, render_template
from pythonium import Analyzer
from pathlib import Path

app = Flask(__name__)

@app.route("/api/analyze")
def analyze_api():
    """API endpoint for code analysis."""
    analyzer = Analyzer(root_path=Path("."))
    issues = analyzer.analyze()
    
    return jsonify([
        {
            "id": issue.id,
            "severity": issue.severity,
            "message": issue.message,
            "file": str(issue.location.file) if issue.location else None,
            "line": issue.location.line if issue.location else None,
        }
        for issue in issues
    ])

@app.route("/")
def dashboard():
    """Web dashboard for analysis results."""
    analyzer = Analyzer(root_path=Path("."))
    issues = analyzer.analyze()
    
    # Group by severity
    by_severity = {}
    for issue in issues:
        by_severity.setdefault(issue.severity, []).append(issue)
    
    return render_template("dashboard.html", issues_by_severity=by_severity)
```

## Error Handling

```python
from pythonium import Analyzer, AnalysisError
from pathlib import Path

try:
    analyzer = Analyzer(root_path=Path("nonexistent/"))
    issues = analyzer.analyze()
except AnalysisError as e:
    print(f"Analysis failed: {e}")
except FileNotFoundError as e:
    print(f"Path not found: {e}")
except PermissionError as e:
    print(f"Permission denied: {e}")
```

## Performance Optimization

### Parallel Analysis

```python
from pythonium.performance import ParallelAnalyzer
from pathlib import Path

# Use parallel analyzer for better performance
analyzer = ParallelAnalyzer(
    root_path=Path("."),
    workers=4  # Number of parallel workers
)

issues = analyzer.analyze()
```

### Memory Management

```python
import gc
from pythonium import Analyzer

# For large codebases, manage memory explicitly
analyzer = Analyzer(root_path=Path("large_project/"))

# Process in chunks
chunk_size = 100
files = list(analyzer.loader.discover_python_files([analyzer.root_path]))

all_issues = []
for i in range(0, len(files), chunk_size):
    chunk = files[i:i + chunk_size]
    chunk_issues = analyzer.analyze(chunk)
    all_issues.extend(chunk_issues)
    
    # Force garbage collection between chunks
    gc.collect()
```

## Testing

### Unit Testing Detectors

```python
import unittest
from pathlib import Path
from pythonium.detectors.dead_code import DeadCodeDetector
from pythonium.models import CodeGraph, Symbol, Location

class TestMyDetector(unittest.TestCase):
    def setUp(self):
        self.detector = DeadCodeDetector()
    
    def test_detector_finds_issue(self):
        # Create test graph
        graph = CodeGraph()
        symbol = Symbol(
            name="unused_function",
            fqname="module.unused_function",
            type="function",
            location=Location(file=Path("test.py"), line=1),
            references=[]  # No references = dead code
        )
        graph.files[Path("test.py")] = [symbol]
        graph.symbols[symbol.fqname] = symbol
        
        # Run detector
        issues = self.detector.analyze(graph)
        
        # Assert results
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].detector_id, "dead_code")
        self.assertEqual(issues[0].severity, "warn")
```

### Integration Testing

```python
import tempfile
import unittest
from pathlib import Path
from pythonium import Analyzer

class TestAnalyzerIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root_path = Path(self.temp_dir)
    
    def test_full_analysis(self):
        # Create test file
        test_file = self.root_path / "test.py"
        test_file.write_text('''
def used_function():
    return "hello"

def unused_function():
    return "unused"

result = used_function()
''')
        
        # Run analysis
        analyzer = Analyzer(root_path=self.root_path)
        issues = analyzer.analyze()
        
        # Check results
        dead_code_issues = [i for i in issues if i.detector_id == "dead_code"]
        self.assertGreater(len(dead_code_issues), 0)
        
        # Check that unused_function is flagged
        unused_issues = [
            i for i in dead_code_issues 
            if "unused_function" in i.message
        ]
        self.assertGreater(len(unused_issues), 0)
```

This API reference provides comprehensive documentation for using Pythonium programmatically. The examples show real-world usage patterns for integration into larger applications and workflows.
