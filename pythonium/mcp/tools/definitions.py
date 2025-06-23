"""
Tool definitions for the Pythonium MCP server.
Static tool definitions separated from main server logic.
"""

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def get_tool_definitions() -> list:
    """Get MCP tool definitions."""
    if not MCP_AVAILABLE:
        return []
    
    return [
        types.Tool(
            name="analyze_code",
            description="Analyze Python code files or directories for code health issues using Pythonium detectors. Returns detailed findings with severity levels and locations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to a Python file (.py) or directory to analyze."
                    },
                    "detectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific detectors to run. Use list_detectors tool to see available options."
                    },
                    "config": {
                        "type": "object",
                        "description": "Optional configuration overrides for analysis behavior. This merges with sensible defaults that include path filtering for virtual environments, cache directories, etc."
                    }
                },
                "required": ["path"]
            }
        ),
        types.Tool(
            name="analyze_inline_code",
            description="Analyze Python code provided as a string rather than from a file. Perfect for analyzing code snippets, generated code, or code from external sources.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python source code to analyze as a string."
                    },
                    "detectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific detectors to run. Use list_detectors tool to see available options."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional filename to use in error reports (default: 'temp_code.py')."
                    },
                    "config": {
                        "type": "object",
                        "description": "Optional configuration overrides for analysis behavior. This merges with sensible defaults."
                    }
                },
                "required": ["code"]
            }
        ),
        types.Tool(
            name="execute_code",
            description="Execute Python code provided as a string and return the output. Perfect for running code snippets, testing small functions, or demonstrating code examples.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python source code to execute as a string."
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Maximum execution time in seconds (default: 30)."
                    },
                    "capture_output": {
                        "type": "boolean",
                        "description": "Whether to capture stdout/stderr output (default: true)."
                    }
                },
                "required": ["code"]
            }
        ),
        types.Tool(
            name="list_detectors",
            description="Get a comprehensive list of all available Pythonium code health detectors with their descriptions and purposes.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_detector_info",
            description="Get detailed information about a specific detector including its purpose, what it detects, and configuration options.",
            inputSchema={
                "type": "object",
                "properties": {
                    "detector_id": {
                        "type": "string",
                        "description": "ID of the detector to get detailed information for. Available detectors will be shown in list_detectors output."
                    }
                },
                "required": ["detector_id"]
            }
        ),
        types.Tool(
            name="analyze_issues",
            description="Generate a summary report and actionable recommendations for code health issues found in previous analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path that was previously analyzed with analyze_code."
                    },
                    "severity_filter": {
                        "type": "string",
                        "enum": ["info", "warn", "error"],
                        "description": "Minimum severity level to include in the summary."
                    }
                },
                "required": ["path"]
            }
        ),
        types.Tool(
            name="get_configuration_schema",
            description="Get comprehensive documentation of Pythonium's configuration system including file structure, global options, detector-specific settings, and usage examples.",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["overview", "detectors", "global", "examples", "precedence", "validation"],
                        "description": "Specific configuration section to focus on."
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="debug_profile",
            description="Get profiling information about MCP server operations to help debug performance issues.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reset": {
                        "type": "boolean",
                        "description": "Whether to reset the profiling data after returning the report."
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="update_issue",
            description="Update an issue's classification, status, severity, message, or add notes. Use this to classify issues and track their resolution progress.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_hash": {
                        "type": "string",
                        "description": "Hash of the issue to update (get from list_issues output)."
                    },
                    "classification": {
                        "type": "string",
                        "enum": ["unclassified", "true_positive", "false_positive"],
                        "description": "Classification of the issue (optional)."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "work_in_progress", "completed"],
                        "description": "Status of the issue (optional)."
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warn", "error"],
                        "description": "Severity level of the issue (optional)."
                    },
                    "message": {
                        "type": "string",
                        "description": "Updated issue message (optional)."
                    },
                    "notes": {
                        "type": "string",
                        "description": "Note to add to the issue (optional)."
                    }
                },
                "required": ["issue_hash"]
            }
        ),
        types.Tool(
            name="list_issues",
            description="List tracked issues with optional filtering by classification, status, or project. Shows issue hashes needed for other operations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to specific project to list issues for (optional, lists all projects if not provided)."
                    },
                    "classification": {
                        "type": "string",
                        "enum": ["unclassified", "true_positive", "false_positive"],
                        "description": "Filter by classification (optional)."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "work_in_progress", "completed"],
                        "description": "Filter by status (optional)."
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_issue",
            description="Get detailed information about a specific tracked issue including its analysis data and tracking metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_hash": {
                        "type": "string",
                        "description": "Hash of the issue to get information for (get from list_issues output)."
                    }
                },
                "required": ["issue_hash"]
            }
        ),
        types.Tool(
            name="repair_python_syntax",
            description="Automatically analyze and repair Python syntax errors in a file. Uses sophisticated error detection and multiple repair strategies. Will attempt repairs up to N times (default 5). Only modifies the file if ALL syntax errors can be resolved.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the Python file to analyze and repair."
                    },
                    "max_attempts": {
                        "type": "number",
                        "description": "Maximum number of repair attempts (default: 5)."
                    },
                    "create_backup": {
                        "type": "boolean",
                        "description": "Whether to create a backup of the original file before making changes (default: true)."
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, analyze and show what would be fixed without modifying the file (default: false)."
                    }
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="get_next_issue",
            description="Get details of the next issue that needs to be worked on. Returns the next actionable issue (first unclassified or pending issue) to streamline agent workflows.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to specific project to get next issue for (optional, gets from all projects if not provided)."
                    },
                    "priority_order": {
                        "type": "array",
                        "items": {
                            "type": "string", 
                            "enum": ["unclassified", "pending", "work_in_progress"]
                        },
                        "description": "Priority order for selecting issues (default: ['unclassified', 'pending', 'work_in_progress'])."
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="investigate_issue",
            description="Automatically investigate an issue and record findings. Analyzes code context, generates investigation details, and adds notes to track agent work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_hash": {
                        "type": "string",
                        "description": "Hash of the issue to investigate (get from list_issues output)."
                    }
                },
                "required": ["issue_hash"]
            }
        )
    ]
