# Output Formats

Pythonium supports multiple output formats to integrate with different tools and workflows. This guide covers all available formats, their use cases, and customization options.

## Overview

Pythonium supports four main output formats:

- **Text** - Human-readable console output
- **JSON** - Machine-readable structured data
- **SARIF** - Static Analysis Results Interchange Format
- **HTML** - Interactive web dashboard

Choose the format based on your use case:

- **Development**: Text format for immediate feedback
- **CI/CD Integration**: JSON or SARIF for automated processing
- **Reporting**: HTML for stakeholder presentations
- **Tool Integration**: SARIF for IDE and security tool integration

## Text Format

The default human-readable format designed for console output and development use.

### Basic Usage

```bash
pythonium crawl
pythonium crawl --format text
```

### Output Structure

```
path/to/file.py:line:column: SEVERITY: message (detector_id)
```

### Example Output

```
src/main.py:15:5: ERROR: Hardcoded password detected (security_smell)
src/utils.py:42: WARN: Function 'unused_helper' is defined but never used (dead_code)
src/models.py:128:12: INFO: Consider using list comprehension (semantic_equivalence)

Found 3 issues
```

### Customization

Configure text output in `.pythonium.yml`:

```yaml
output:
  text:
    # Custom format template
    template: "{file}:{line}: {severity}: {message}"
    
    # Include source code context
    include_context: true
    context_lines: 2
    
    # Color output (auto-detected for TTY)
    color: auto  # always, never, auto
    
    # Show issue counts by severity
    show_summary: true
    
    # Group issues by file
    group_by_file: true
```

### Advanced Templates

Use custom templates with available placeholders:

```yaml
output:
  text:
    template: "[{severity}] {detector_name}: {message} at {file}:{line}"
```

Available placeholders:
- `{file}` - File path
- `{line}` - Line number
- `{column}` - Column number
- `{severity}` - Issue severity
- `{message}` - Issue description
- `{detector_id}` - Detector identifier
- `{detector_name}` - Human-readable detector name
- `{symbol}` - Symbol name (if available)

## JSON Format

Structured data format ideal for tool integration and automated processing.

### Basic Usage

```bash
pythonium crawl --format json
pythonium crawl --format json --output results.json
```

### Schema

```json
[
  {
    "id": "string",              // Unique issue identifier
    "severity": "string",        // error|warn|info
    "message": "string",         // Human-readable description
    "location": {                // Source location (optional)
      "file": "string",          // File path
      "line": number,            // Line number
      "column": number,          // Column number (optional)
      "end_line": number,        // End line (optional)
      "end_column": number       // End column (optional)
    },
    "symbol": "string",          // Symbol name (optional)
    "metadata": {                // Additional data
      "detector_name": "string",
      "detector_description": "string",
      // ... detector-specific metadata
    }
  }
]
```

### Example Output

```json
[
  {
    "id": "security_smell.hardcoded_password",
    "severity": "error",
    "message": "Hardcoded password detected in assignment",
    "location": {
      "file": "src/auth.py",
      "line": 15,
      "column": 5,
      "end_line": 15,
      "end_column": 25
    },
    "symbol": "auth.login",
    "metadata": {
      "detector_name": "Security Smell Detector",
      "detector_description": "Detects potential security vulnerabilities",
      "pattern": "password\\s*=\\s*['\"]\\w+['\"]",
      "confidence": 0.95
    }
  },
  {
    "id": "dead_code.unused_function",
    "severity": "warn",
    "message": "Function 'helper' is defined but never used",
    "location": {
      "file": "src/utils.py",
      "line": 42,
      "column": 1
    },
    "symbol": "utils.helper",
    "metadata": {
      "detector_name": "Dead Code Detector",
      "function_name": "helper",
      "defined_line": 42
    }
  }
]
```

### Customization

```yaml
output:
  json:
    # Pretty-print output
    pretty: true
    
    # Include source code in output
    include_source: true
    
    # Include full metadata
    include_metadata: true
    
    # Sort issues by severity then file
    sort_by: ["severity", "file", "line"]
```

### Processing JSON Output

#### Python

```python
import json

with open('results.json', 'r') as f:
    issues = json.load(f)

# Filter by severity
errors = [issue for issue in issues if issue['severity'] == 'error']

# Group by file
from collections import defaultdict
by_file = defaultdict(list)
for issue in issues:
    if issue.get('location'):
        by_file[issue['location']['file']].append(issue)
```

#### jq Examples

```bash
# Count issues by severity
jq 'group_by(.severity) | map({severity: .[0].severity, count: length})' results.json

# Get all security issues
jq '.[] | select(.id | startswith("security_"))' results.json

# Files with most issues
jq 'group_by(.location.file) | map({file: .[0].location.file, count: length}) | sort_by(.count) | reverse' results.json
```

## SARIF Format

Static Analysis Results Interchange Format (SARIF) is an industry standard for static analysis tool output, supported by many IDEs and security platforms.

### Basic Usage

```bash
pythonium crawl --format sarif
pythonium crawl --format sarif --output results.sarif
```

### Schema

SARIF 2.1.0 compliant output with:
- Tool information and version
- Rules (detectors) with descriptions
- Results with locations and metadata
- Taxonomies for categorization

### Example Output

```json
{
  "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "Pythonium",
          "version": "0.1.0",
          "informationUri": "https://github.com/dwharve/pythonium",
          "rules": [
            {
              "id": "security_smell",
              "name": "Security Smell Detector",
              "shortDescription": {
                "text": "Detects potential security vulnerabilities"
              },
              "fullDescription": {
                "text": "Identifies common security anti-patterns and vulnerabilities in Python code"
              },
              "defaultConfiguration": {
                "level": "error"
              },
              "helpUri": "https://pythonium.readthedocs.io/detectors/security/"
            }
          ]
        }
      },
      "results": [
        {
          "ruleId": "security_smell",
          "ruleIndex": 0,
          "message": {
            "text": "Hardcoded password detected in assignment"
          },
          "level": "error",
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": {
                  "uri": "src/auth.py"
                },
                "region": {
                  "startLine": 15,
                  "startColumn": 5,
                  "endLine": 15,
                  "endColumn": 25
                }
              }
            }
          ],
          "properties": {
            "pattern": "password\\s*=\\s*['\"]\\w+['\"]",
            "confidence": 0.95
          }
        }
      ]
    }
  ]
}
```

### IDE Integration

#### Visual Studio Code

1. Install the SARIF Viewer extension
2. Run analysis: `pythonium crawl --format sarif --output results.sarif`
3. Open SARIF file in VS Code
4. Navigate directly to issues in source code

#### GitHub Integration

```yaml
# .github/workflows/code-analysis.yml
- name: Upload SARIF results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: results.sarif
```

### Customization

```yaml
output:
  sarif:
    # Include source code snippets
    include_source: true
    
    # Add taxonomies for categorization
    include_taxonomies: true
    
    # Custom tool metadata
    tool:
      name: "Custom Pythonium"
      version: "1.0.0"
      information_uri: "https://example.com/docs"
```

## HTML Format

Interactive web dashboard for comprehensive reporting and analysis review.

### Basic Usage

```bash
pythonium crawl --format html --output report.html
```

### Features

- **Summary Dashboard**: Issue counts, severity distribution, trends
- **Issue Browser**: Filterable and sortable issue list
- **Source Viewer**: Syntax-highlighted code with inline issues
- **Detector Information**: Descriptions and configuration options
- **Charts and Graphs**: Visual analysis of code health metrics
- **Export Options**: PDF generation, CSV export

### Example Output

The HTML report includes:

1. **Executive Summary**
   - Total issues found
   - Issues by severity
   - Issues by detector
   - Top affected files

2. **Detailed Issue List**
   - Filterable by severity, detector, file
   - Sortable by any column
   - Click to jump to source code

3. **Source Code Viewer**
   - Syntax highlighting
   - Issue annotations
   - Context lines around issues

4. **Detector Information**
   - What each detector finds
   - Configuration options
   - Related detectors

### Customization

```yaml
output:
  html:
    # Report title
    title: "Code Quality Report"
    
    # Include source code
    include_source: true
    
    # Theme
    theme: "light"  # light, dark, auto
    
    # Custom CSS
    custom_css: "path/to/custom.css"
    
    # Logo URL
    logo_url: "https://example.com/logo.png"
    
    # Additional metadata
    metadata:
      project: "My Project"
      version: "1.0.0"
      generated_by: "CI Pipeline"
```

### Template Customization

Create custom HTML templates:

```yaml
output:
  html:
    template_dir: "templates/"
    templates:
      main: "custom_report.html"
      issue_list: "custom_issues.html"
```

## Format Comparison

| Feature | Text | JSON | SARIF | HTML |
|---------|------|------|-------|------|
| Human Readable | ✅ | ❌ | ❌ | ✅ |
| Machine Readable | ❌ | ✅ | ✅ | ❌ |
| IDE Integration | ❌ | ❌ | ✅ | ❌ |
| CI/CD Integration | ✅ | ✅ | ✅ | ❌ |
| Interactive | ❌ | ❌ | ❌ | ✅ |
| Standardized | ❌ | ❌ | ✅ | ❌ |
| Customizable | ✅ | ✅ | ✅ | ✅ |
| Source Code | ❌ | ✅ | ✅ | ✅ |

## Multi-Format Output

Generate multiple formats in one run:

```bash
# Generate both JSON and HTML
pythonium crawl --format json --output results.json
pythonium crawl --format html --output report.html

# Or use configuration
```

```yaml
output:
  formats:
    - type: json
      path: "results.json"
    - type: html
      path: "report.html"
    - type: sarif
      path: "results.sarif"
```

## Integration Examples

### CI/CD Pipeline

```bash
#!/bin/bash
# Generate multiple outputs for different consumers

# JSON for automated processing
pythonium crawl --format json --output ci/results.json

# SARIF for security dashboard
pythonium crawl --format sarif --output security/results.sarif

# HTML for human review
pythonium crawl --format html --output reports/latest.html
```

### Makefile Integration

```makefile
.PHONY: analyze
analyze:
	@echo "Running code analysis..."
	pythonium crawl --format json --output analysis.json
	pythonium crawl --format html --output report.html
	@echo "Results: analysis.json, report.html"

.PHONY: security-scan
security-scan:
	pythonium crawl \
		--detectors security_smell \
		--format sarif \
		--output security.sarif \
		--fail-on error
```

### Python Integration

```python
import subprocess
import json

def run_analysis(path, detectors=None):
    """Run Pythonium analysis and return results."""
    cmd = ["pythonium", "crawl", "--format", "json", path]
    if detectors:
        cmd.extend(["--detectors", ",".join(detectors)])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        return json.loads(result.stdout)
    return []

# Usage
issues = run_analysis("src/", ["security_smell", "dead_code"])
security_issues = [i for i in issues if i["id"].startswith("security_")]
```

## Best Practices

### Development Workflow

1. **Local Development**: Use text format for immediate feedback
2. **Code Review**: Generate HTML reports for thorough review
3. **CI/CD**: Use JSON/SARIF for automated processing
4. **Security Review**: Use SARIF for security tool integration

### Performance Considerations

1. **Large Projects**: JSON format is fastest for large outputs
2. **Network Transfer**: SARIF is most compact for similar information
3. **Interactive Review**: HTML generation takes longer but provides rich experience

### Output Management

```bash
# Organized output structure
mkdir -p reports/{json,html,sarif}

pythonium crawl --format json --output reports/json/$(date +%Y%m%d).json
pythonium crawl --format html --output reports/html/$(date +%Y%m%d).html
pythonium crawl --format sarif --output reports/sarif/$(date +%Y%m%d).sarif
```
