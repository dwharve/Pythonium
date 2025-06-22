"""
Code execution and repair MCP tool handlers for Pythonium.
"""

import sys
import asyncio
from pathlib import Path
from typing import Any, Dict, List

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from ..debug import profiler, profile_operation
from .base import BaseHandler


class ExecutionHandlers(BaseHandler):
    """Handlers for code execution and repair operations."""
    
    @profile_operation("execute_code")
    async def execute_code(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Execute Python code and return the output."""
        code = arguments.get("code")
        if not code:
            raise ValueError("Code is required")
        
        # Get timeout with validation and max limit (5 minutes)
        requested_timeout = arguments.get("timeout", 30)
        max_timeout = 300  # 5 minutes maximum
        timeout = min(requested_timeout, max_timeout)
        
        profiler.checkpoint("code_execution_setup", timeout=timeout)
        
        if requested_timeout > max_timeout:
            timeout_warning = f"Requested timeout ({requested_timeout}s) exceeds maximum allowed ({max_timeout}s). Using {max_timeout}s.\\n\\n"
        else:
            timeout_warning = ""
        
        try:
            # Create subprocess that reads from stdin
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            profiler.checkpoint("subprocess_created")
            
            # Send code to stdin and wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=code.encode('utf-8')), 
                timeout=timeout
            )
            
            profiler.checkpoint("code_execution_completed", exit_code=process.returncode)
            
            # Decode output
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            output_lines = [
                f"{timeout_warning}Python Code Execution Results",
                "=" * 35,
                f"Exit Code: {process.returncode}",
                f"Execution Time: ≤ {timeout}s",
                ""
            ]
            
            if stdout_text:
                output_lines.extend([
                    "STDOUT:",
                    stdout_text.rstrip(),
                    ""
                ])
            
            if stderr_text:
                output_lines.extend([
                    "STDERR:",
                    stderr_text.rstrip(),
                    ""
                ])
            
            if not stdout_text and not stderr_text:
                output_lines.append("No output produced.")
            
            return [types.TextContent(
                type="text",
                text="\n".join(output_lines)
            )]
            
        except asyncio.TimeoutError:
            profiler.checkpoint("code_execution_timeout")
            return [types.TextContent(
                type="text",
                text=f"{timeout_warning}Code execution timed out after {timeout} seconds."
            )]
        except Exception as e:
            profiler.checkpoint("code_execution_error", error=str(e))
            return [types.TextContent(
                type="text",
                text=f"{timeout_warning}Error executing code: {str(e)}"
            )]
    
    @profile_operation("repair_python_syntax")
    async def repair_python_syntax(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Analyze and repair Python syntax errors in a file."""
        from pythonium.syntax_repair import repair_file_syntax, repair_python_syntax
        
        file_path = arguments.get("file_path")
        if not file_path:
            raise ValueError("file_path is required")
        
        max_attempts = arguments.get("max_attempts", 5)
        create_backup = arguments.get("create_backup", True)
        dry_run = arguments.get("dry_run", False)
        
        # Validate max_attempts
        if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 20:
            raise ValueError("max_attempts must be an integer between 1 and 20")
        
        path = Path(file_path).resolve()
        profiler.checkpoint("path_validation", path=str(path), exists=path.exists())
        
        if not path.exists():
            return [types.TextContent(
                type="text",
                text=f"Error: File not found: {file_path}"
            )]
        
        if not path.suffix == '.py':
            return [types.TextContent(
                type="text",
                text=f"Error: File must be a Python file (.py), got: {path.suffix}"
            )]
        
        try:
            profiler.checkpoint("reading_file")
            
            # Read the original file
            with open(path, 'r', encoding='utf-8') as f:
                original_code = f.read()
            
            profiler.checkpoint("file_read", size=len(original_code))
            
            if dry_run:
                # Analyze only, don't modify file
                result = repair_python_syntax(original_code, max_attempts)
                profiler.checkpoint("dry_run_complete", success=result["success"])
                
                output_lines = [
                    f"DRY RUN: Python Syntax Analysis for {path.name}",
                    "=" * 60,
                    "",
                    f"Original errors found: {len(result['original_errors'])}",
                ]
                
                if result["original_errors"]:
                    output_lines.extend([
                        "",
                        "Original Syntax Errors:",
                        "-" * 25
                    ])
                    for error in result["original_errors"]:
                        output_lines.append(f"  • {error}")
                
                if result["attempts"]:
                    output_lines.extend([
                        "",
                        f"Repair Attempts ({len(result['attempts'])}/{max_attempts}):",
                        "-" * 30
                    ])
                    for i, attempt in enumerate(result["attempts"], 1):
                        status = "✓" if attempt.get("success") else "✗"
                        output_lines.append(f"  {status} Attempt {i}: {attempt.get('strategy', 'unknown')}")
                        if attempt.get("error"):
                            output_lines.append(f"      Error: {attempt['error']}")
                
                if result["success"]:
                    output_lines.extend([
                        "",
                        "✅ Result: All syntax errors can be automatically fixed!",
                        "",
                        "To apply the fixes, run this tool again with dry_run=false"
                    ])
                else:
                    output_lines.extend([
                        "",
                        "❌ Result: Unable to fix all syntax errors automatically",
                        "",
                        f"Remaining errors after {max_attempts} attempts:"
                    ])
                    for error in result.get("final_errors", []):
                        output_lines.append(f"  • {error}")
                
                return [types.TextContent(
                    type="text",
                    text="\n".join(output_lines)
                )]
            
            else:
                # Actually repair the file
                result = repair_file_syntax(str(path), max_attempts, create_backup)
                profiler.checkpoint("repair_complete", success=result["success"])
                
                output_lines = [
                    f"Python Syntax Repair Results for {path.name}",
                    "=" * 60,
                    ""
                ]
                
                if result["success"]:
                    output_lines.extend([
                        "✅ SUCCESS: All syntax errors have been fixed!",
                        "",
                        f"Original errors: {len(result.get('original_errors', []))}",
                        f"Repair attempts: {len(result.get('attempts', []))}",
                        f"File updated: {result.get('file_updated', False)}",
                    ])
                    
                    if result.get("backup_created"):
                        output_lines.append(f"Backup created: {result['backup_created']}")
                    
                    if result.get("attempts"):
                        output_lines.extend([
                            "",
                            "Repair Steps Taken:",
                            "-" * 20
                        ])
                        for i, attempt in enumerate(result["attempts"], 1):
                            if attempt.get("success"):
                                output_lines.append(f"  ✓ Step {i}: Fixed {attempt.get('error', 'unknown error')}")
                    
                else:
                    output_lines.extend([
                        "❌ FAILED: Could not fix all syntax errors",
                        "",
                        f"Original errors: {len(result.get('original_errors', []))}",
                        f"Repair attempts: {len(result.get('attempts', []))}",
                        "File was NOT modified (no partial fixes applied)",
                        ""
                    ])
                    
                    if result.get("final_errors"):
                        output_lines.extend([
                            "Remaining syntax errors:",
                            "-" * 25
                        ])
                        for error in result["final_errors"]:
                            output_lines.append(f"  • {error}")
                
                output_lines.extend([
                    "",
                    f"Message: {result.get('message', 'Operation completed')}"
                ])
                
                return [types.TextContent(
                    type="text",
                    text="\n".join(output_lines)
                )]
        
        except Exception as e:
            profiler.checkpoint("repair_error", error=str(e))
            return [types.TextContent(
                type="text",
                text=f"Error during syntax repair: {str(e)}"
            )]
