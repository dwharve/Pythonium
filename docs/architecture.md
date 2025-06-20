# Architecture Overview

This document provides a comprehensive overview of Pythonium's internal architecture, design patterns, and extensibility mechanisms.

## High-Level Architecture

Pythonium follows a modular, plugin-based architecture designed for extensibility and maintainability:

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                            │
├─────────────────────────────────────────────────────────────┤
│                     Analysis Engine                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Loader    │  │  Analyzer   │  │   Output Formatter  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Detector Framework                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Dead Code   │  │    Clone    │  │     Security        │  │
│  │ Detector    │  │  Detector   │  │     Detector        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                     Core Models                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ CodeGraph   │  │   Symbol    │  │       Issue         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                  Infrastructure                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Cache     │  │    Hooks    │  │    Configuration    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Analysis Engine

The analysis engine coordinates the entire analysis process:

#### Analyzer (`pythonium/analyzer.py`)

The central orchestrator that:
- Loads configuration and settings
- Discovers and loads detectors
- Builds the code graph from source files
- Executes detectors in parallel
- Aggregates and filters results
- Applies post-processing (deduplication, suppression)

**Key Methods:**
```python
class Analyzer:
    def analyze(self, paths: List[Path]) -> List[Issue]:
        """Main analysis entry point"""
        
    def _build_graph(self) -> CodeGraph:
        """Build code graph from source files"""
        
    def _run_detectors(self, graph: CodeGraph) -> List[Issue]:
        """Execute all enabled detectors"""
```

#### CodeLoader (`pythonium/loader.py`)

Responsible for discovering and parsing Python source files:
- File discovery with glob patterns
- AST parsing and error handling
- Symbol extraction and metadata collection
- Module dependency tracking

**Key Features:**
- Handles encoding detection and errors
- Supports include/exclude patterns
- Caches parsed ASTs for performance
- Extracts comprehensive symbol information

### 2. Code Graph Model

The code graph represents the analyzed codebase structure:

#### CodeGraph (`pythonium/models.py`)

Central data structure containing:
```python
class CodeGraph:
    files: Dict[Path, List[Symbol]]      # Symbols by file
    symbols: Dict[str, Symbol]           # All symbols by FQN
    references: Dict[str, Set[str]]      # Reference relationships
    imports: Dict[Path, List[Import]]    # Import statements
    
    def get_references(self, symbol: Symbol) -> List[Symbol]:
        """Get symbols that reference this symbol"""
        
    def get_dependencies(self, symbol: Symbol) -> List[Symbol]:
        """Get symbols this symbol depends on"""
```

#### Symbol (`pythonium/models.py`)

Represents code symbols (functions, classes, variables):
```python
class Symbol:
    name: str                    # Symbol name
    fqname: str                 # Fully qualified name
    type: str                   # function, class, variable, etc.
    location: Location          # Source location
    references: List[Location]   # Where it's referenced
    ast_node: Optional[ast.AST] # Original AST node
    metadata: Dict[str, Any]    # Additional data
```

### 3. Detector Framework

Pythonium uses a plugin-based detector system:

#### Base Detector (`pythonium/detectors/__init__.py`)

All detectors inherit from `BaseDetector`:
```python
class BaseDetector:
    id: str                     # Unique identifier
    name: str                   # Human-readable name  
    description: str            # What it detects
    category: str               # Categorization
    
    def analyze(self, graph: CodeGraph) -> List[Issue]:
        """Main detection logic"""
        
    def create_issue(self, **kwargs) -> Issue:
        """Helper to create consistent issues"""
```

#### Detector Discovery

Detectors are discovered through:
1. **Directory scanning**: All `*Detector` classes in `pythonium/detectors/`
2. **Entry points**: Setuptools entry points for external detectors
3. **Manual registration**: Programmatic detector registration

#### Detector Categories

| Category | Detectors | Purpose |
|----------|-----------|---------|
| Code Quality | `dead_code`, `complexity_hotspot` | Maintainability |
| Duplication | `clone`, `block_clone`, `semantic_equivalence` | DRY principle |
| Security | `security_smell`, `deprecated_api` | Security best practices |
| Architecture | `circular_deps`, `inconsistent_api` | Design quality |
| Patterns | `advanced_patterns`, `alt_implementation` | Code organization |

### 4. Configuration System

Multi-layered configuration system:

#### Settings (`pythonium/settings.py`)

Manages configuration from multiple sources:
```python
class Settings:
    def __init__(self, config_dict: Dict = None, config_file: Path = None):
        """Load configuration from dict or file"""
        
    def get_detector_options(self, detector_id: str) -> Dict:
        """Get detector-specific configuration"""
        
    def is_detector_enabled(self, detector_id: str) -> bool:
        """Check if detector is enabled"""
```

**Configuration Precedence:**
1. Built-in defaults
2. Configuration file (`.pythonium.yml`)
3. Environment variables
4. Command-line arguments

### 5. Performance Infrastructure

#### Caching (`pythonium/performance.py`)

SQLite-based caching system:
```python
class AnalysisCache:
    def cache_symbols(self, file_path: Path, symbols: List[Symbol]):
        """Cache parsed symbols for file"""
        
    def get_cached_symbols(self, file_path: Path) -> Optional[List[Symbol]]:
        """Retrieve cached symbols if file unchanged"""
        
    def invalidate_file(self, file_path: Path):
        """Remove cached data for modified file"""
```

**Cache Invalidation:**
- File modification time tracking
- Content hash verification
- Python version compatibility
- Dependency change detection

#### Parallel Analysis (`pythonium/performance.py`)

Multi-process detector execution:
```python
class ParallelAnalyzer:
    def analyze_parallel(self, detectors: List[Detector], 
                        graph: CodeGraph) -> List[Issue]:
        """Run detectors in parallel worker processes"""
```

### 6. Hook System

Extensible hook system for customization:

#### Hook Types (`pythonium/hooks.py`)

```python
class HookManager:
    def register_file_parse_hook(self, hook: FileParseHook):
        """Called after each file is parsed"""
        
    def register_issue_hook(self, hook: IssueHook):
        """Called when each issue is found"""
        
    def register_finish_hook(self, hook: FinishHook):
        """Called after analysis completes"""
```

**Built-in Hooks:**
- **MetricsHook**: Collect analysis statistics
- **SeverityFilterHook**: Filter issues by severity
- **SuppressionHook**: Apply suppression rules

### 7. Output System

Pluggable output formatters:

#### Formatters

Each format has a dedicated formatter:
- **TextFormatter**: Console-friendly output
- **JSONFormatter**: Structured data output  
- **SARIFFormatter**: Industry standard format
- **HTMLFormatter**: Interactive web reports

#### Dashboard (`pythonium/dashboard.py`)

Rich HTML reporting with:
- Issue statistics and charts
- Interactive source code viewer
- Filtering and sorting capabilities
- Export functionality

## Design Patterns

### 1. Plugin Architecture

Pythonium uses plugin architecture for extensibility:

**Registry Pattern**: Detectors self-register through metaclasses
**Factory Pattern**: Detector loading and instantiation
**Strategy Pattern**: Different analysis strategies per detector

### 2. Observer Pattern

Hook system implements observer pattern:
- Analysis events trigger registered hooks
- Loose coupling between core and extensions
- Extensible without modifying core code

### 3. Builder Pattern

CodeGraph construction uses builder pattern:
- Incremental graph building
- Validation at each step
- Flexible graph construction strategies

### 4. Command Pattern

CLI implements command pattern:
- Each command encapsulates operation
- Easy to add new commands
- Consistent error handling and logging

## Data Flow

### 1. Analysis Pipeline

```
Input Files → CodeLoader → AST Parsing → Symbol Extraction → CodeGraph
                ↓
Issue Filtering ← Result Aggregation ← Detector Execution ← CodeGraph
                ↓
Output Formatting → File/Console Output
```

### 2. Detector Execution

```
CodeGraph → Detector Pool → Parallel Execution → Issue Collection
                                   ↓
                            Individual Detector Analysis
                                   ↓
                            Issue Creation & Metadata
```

### 3. Configuration Flow

```
Defaults → Config File → Environment → CLI Args → Final Settings
                                   ↓
                            Detector Configuration
                                   ↓
                            Analysis Execution
```

## Extensibility Points

### 1. Custom Detectors

Add new detectors by:
```python
from pythonium.detectors import BaseDetector

class MyDetector(BaseDetector):
    id = "my_detector"
    name = "My Custom Detector"
    description = "Finds custom issues"
    
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        # Your detection logic
        return issues
```

### 2. Output Formats

Add new output formats:
```python
class MyFormatter:
    def format_issues(self, issues: List[Issue]) -> str:
        # Your formatting logic
        return formatted_output
```

### 3. Hooks

Add custom hooks:
```python
class MyHook(BaseHook):
    def on_issue_found(self, context: HookContext, issue: Issue):
        # Your custom logic
        pass
```

### 4. Configuration

Extend configuration schema:
```yaml
# .pythonium.yml
my_extension:
  option1: value1
  option2: value2
```

## Performance Considerations

### 1. Memory Management

- **Lazy Loading**: ASTs loaded only when needed
- **Symbol Caching**: Reuse parsed symbols across detectors
- **Graph Cleanup**: Release unused graph data
- **Streaming**: Process large files in chunks

### 2. CPU Optimization

- **Parallel Detectors**: Multi-process detector execution
- **Smart Caching**: Avoid re-parsing unchanged files
- **Early Termination**: Skip processing when possible
- **Efficient Algorithms**: Optimized detection algorithms

### 3. I/O Optimization

- **Batch File Reading**: Read multiple files together
- **Compressed Caching**: Compress cached symbol data
- **Async I/O**: Non-blocking file operations
- **Memory Mapping**: Map large files to memory

## Security Considerations

### 1. Input Validation

- **Path Traversal**: Prevent directory traversal attacks
- **File Size Limits**: Limit analyzed file sizes
- **Encoding Safety**: Safe handling of file encodings
- **AST Safety**: Safe AST parsing and traversal

### 2. Execution Safety

- **Sandboxing**: Detector execution isolation
- **Resource Limits**: CPU and memory limits
- **Safe Evaluation**: No arbitrary code execution
- **Error Containment**: Isolated error handling

## Testing Architecture

### 1. Test Structure

```
tests/
├── unit/                    # Unit tests for components
│   ├── test_analyzer.py
│   ├── test_detectors/
│   └── test_models.py
├── integration/             # Integration tests
│   ├── test_cli.py
│   └── test_full_analysis.py
└── fixtures/               # Test data and fixtures
    ├── sample_projects/
    └── expected_results/
```

### 2. Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Full pipeline testing
- **Performance Tests**: Speed and memory testing
- **Regression Tests**: Bug prevention testing

## Deployment Architecture

### 1. Distribution

- **PyPI Package**: Standard Python package distribution
- **Docker Images**: Containerized deployment
- **Binary Releases**: Standalone executables
- **CI/CD Integration**: Pipeline-friendly installation

### 2. Dependencies

- **Core Dependencies**: Minimal required packages
- **Optional Dependencies**: Feature-specific packages
- **Development Dependencies**: Testing and development tools
- **Version Compatibility**: Python 3.8+ support

This architecture supports Pythonium's goals of extensibility, performance, and maintainability while providing a solid foundation for future enhancements.
