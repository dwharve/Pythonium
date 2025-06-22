"""
Sophisticated Python syntax analysis and repair functionality.

This module provides advanced capabilities for detecting and automatically
fixing Python syntax errors including indentation issues, missing colons,
unmatched brackets, and other common syntax problems.
"""

import ast
import re
import tokenize
import io
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PythonSyntaxError:
    """Represents a syntax error with location and description."""
    
    def __init__(self, line_no: int, column: int, message: str, error_type: str = "syntax"):
        self.line_no = line_no
        self.column = column
        self.message = message
        self.error_type = error_type
        
    def __str__(self):
        return f"Line {self.line_no}, Column {self.column}: {self.message}"


class SyntaxRepairEngine:
    """
    Advanced Python syntax repair engine that can detect and fix various
    types of syntax errors automatically.
    """
    
    def __init__(self):
        self.repair_strategies = [
            self._fix_indentation_errors,
            self._fix_missing_colons,
            self._fix_unmatched_brackets,
            self._fix_string_quoting,
            self._fix_common_typos,
            self._fix_import_errors,
            self._fix_function_definition_errors,
            self._fix_class_definition_errors,
        ]
    
    def analyze_and_repair(self, code: str, max_attempts: int = 5) -> Dict[str, Any]:
        """
        Analyze Python code for syntax errors and attempt to repair them.
        
        Args:
            code: Python source code as string
            max_attempts: Maximum number of repair attempts (default: 5)
            
        Returns:
            Dictionary with repair results including:
            - success: Whether all errors were fixed
            - fixed_code: The repaired code (only if success=True)
            - original_errors: List of errors found in original code
            - attempts: List of repair attempts made
            - final_errors: Any remaining errors after repair attempts
        """
        original_code = code
        current_code = code
        attempts = []
        
        # Analyze original code
        original_errors = self._analyze_syntax_errors(original_code)
        
        if not original_errors:
            return {
                "success": True,
                "fixed_code": original_code,
                "original_errors": [],
                "attempts": [],
                "final_errors": [],
                "message": "No syntax errors found in original code"
            }
        
        # Attempt repairs
        for attempt in range(max_attempts):
            errors = self._analyze_syntax_errors(current_code)
            
            if not errors:
                return {
                    "success": True,
                    "fixed_code": current_code,
                    "original_errors": [str(e) for e in original_errors],
                    "attempts": attempts,
                    "final_errors": [],
                    "message": f"Successfully fixed all syntax errors in {attempt + 1} attempt(s)"
                }
            
            # Try to fix the first error
            fixed_code = self._attempt_repair(current_code, errors[0])
            
            if fixed_code == current_code:
                # No changes made, try next strategy or give up
                attempts.append({
                    "attempt": attempt + 1,
                    "error": str(errors[0]),
                    "strategy": "no_applicable_strategy",
                    "success": False
                })
                break
            
            attempts.append({
                "attempt": attempt + 1,
                "error": str(errors[0]),
                "strategy": "applied_fix",
                "success": True,
                "changes_made": True
            })
            
            current_code = fixed_code
        
        # Final check
        final_errors = self._analyze_syntax_errors(current_code)
        
        return {
            "success": False,
            "fixed_code": None,
            "original_errors": [str(e) for e in original_errors],
            "attempts": attempts,
            "final_errors": [str(e) for e in final_errors],
            "message": f"Unable to fix all syntax errors after {max_attempts} attempts"
        }
    
    def _analyze_syntax_errors(self, code: str) -> List[PythonSyntaxError]:
        """Analyze code and return list of syntax errors."""
        errors = []
        
        # Try to parse with AST
        try:
            ast.parse(code)
            return []  # No syntax errors
        except SyntaxError as e:
            errors.append(PythonSyntaxError(
                line_no=e.lineno or 1,
                column=e.offset or 0,
                message=e.msg or "Syntax error",
                error_type="syntax"
            ))
        except Exception as e:
            errors.append(PythonSyntaxError(
                line_no=1,
                column=0,
                message=f"Parse error: {str(e)}",
                error_type="parse"
            ))
        
        # Additional tokenization analysis for more detailed errors
        try:
            tokens = list(tokenize.tokenize(io.BytesIO(code.encode()).readline))
        except tokenize.TokenError as e:
            errors.append(PythonSyntaxError(
                line_no=e.args[1][0] if len(e.args) > 1 else 1,
                column=e.args[1][1] if len(e.args) > 1 else 0,
                message=f"Token error: {e.args[0]}",
                error_type="token"
            ))
        except Exception:
            pass  # Skip additional analysis if tokenization fails
        
        return errors
    
    def _attempt_repair(self, code: str, error: PythonSyntaxError) -> str:
        """Attempt to repair a specific syntax error."""
        for strategy in self.repair_strategies:
            try:
                fixed_code = strategy(code, error)
                if fixed_code != code:
                    return fixed_code
            except Exception as e:
                logger.debug(f"Repair strategy failed: {e}")
                continue
        
        return code  # No repair possible
    
    def _fix_indentation_errors(self, code: str, error: PythonSyntaxError) -> str:
        """Fix indentation-related syntax errors."""
        is_indent_error = (
            "indent" in error.message.lower() or
            "expected an indented block" in error.message or
            "unindent does not match" in error.message
        )
        
        if not is_indent_error:
            return code
        
        lines = code.splitlines()
        if error.line_no > len(lines):
            return code
        
        # Detect indentation style
        indent_size = self._detect_indent_size(lines)
        
        # Handle "expected an indented block" errors
        if "expected an indented block" in error.message:
            error_line_idx = error.line_no - 1
            
            # Find the previous line that should start an indented block
            prev_line_idx = error_line_idx - 1
            while prev_line_idx >= 0:
                prev_line = lines[prev_line_idx].strip()
                if prev_line and not prev_line.startswith('#'):
                    break
                prev_line_idx -= 1
            
            if prev_line_idx >= 0:
                prev_line = lines[prev_line_idx]
                # Check if the line ends with colon (ignoring comments)
                line_without_comment = prev_line.split('#')[0].strip()
                
                if line_without_comment.endswith(':'):
                    # The line that ends with colon should be followed by indented block
                    if error_line_idx < len(lines):
                        error_line = lines[error_line_idx]
                        stripped = error_line.lstrip()
                        current_indent = len(error_line) - len(stripped)
                        
                        # Calculate expected indent (increase from previous line)
                        prev_indent = len(prev_line) - len(prev_line.lstrip())
                        expected_indent = prev_indent + indent_size
                        
                        if current_indent != expected_indent:
                            lines[error_line_idx] = ' ' * expected_indent + stripped
                            return '\n'.join(lines)
        
        # General indentation fixing
        fixed_lines = []
        indent_stack = [0]
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            current_indent = len(line) - len(stripped)
            
            # Calculate expected indentation
            expected_indent = self._calculate_expected_indent(
                lines, i, indent_stack, indent_size
            )
            
            # Apply fix if we're near the error line
            if abs(i + 1 - error.line_no) <= 1 and current_indent != expected_indent:
                fixed_line = ' ' * expected_indent + stripped
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
            
            # Update indent stack
            if stripped.endswith(':'):
                indent_stack.append(expected_indent + indent_size)
            elif expected_indent < indent_stack[-1]:
                while len(indent_stack) > 1 and indent_stack[-1] > expected_indent:
                    indent_stack.pop()
        
        return '\n'.join(fixed_lines)
    
    def _fix_missing_colons(self, code: str, error: PythonSyntaxError) -> str:
        """Fix missing colons in control structures."""
        if ":" not in error.message and "expected ':'" not in error.message:
            return code
        
        lines = code.splitlines()
        if error.line_no > len(lines):
            return code
        
        error_line = lines[error.line_no - 1]
        
        # Check if this line should end with a colon
        stripped = error_line.strip()
        
        # Remove comments for pattern matching
        line_without_comment = error_line.split('#')[0].strip()
        
        # Patterns that should end with colons
        colon_keywords = ['def ', 'class ', 'if ', 'elif ', 'else', 'for ', 'while ', 'try', 'except', 'finally', 'with ']
        
        should_have_colon = any(
            line_without_comment.startswith(keyword) or 
            f' {keyword.strip()}' in line_without_comment
            for keyword in colon_keywords
        )
        
        if should_have_colon and not line_without_comment.endswith(':'):
            # Find where to insert the colon (before comment if present)
            comment_pos = error_line.find('#')
            if comment_pos >= 0:
                lines[error.line_no - 1] = error_line[:comment_pos].rstrip() + ':  ' + error_line[comment_pos:]
            else:
                lines[error.line_no - 1] = error_line.rstrip() + ':'
            return '\n'.join(lines)
        
        return code
    
    def _fix_unmatched_brackets(self, code: str, error: PythonSyntaxError) -> str:
        """Fix unmatched brackets, parentheses, and braces."""
        is_bracket_error = (
            any(char in error.message for char in ['(', ')', '[', ']', '{', '}']) or
            'EOF in multi-line' in error.message or
            'was not closed' in error.message or
            'unmatched' in error.message.lower()
        )
        
        if not is_bracket_error:
            return code
        
        lines = code.splitlines()
        
        # Count bracket pairs
        bracket_pairs = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        for i, line in enumerate(lines):
            for j, char in enumerate(line):
                if char in bracket_pairs:
                    stack.append((char, i, j))
                elif char in bracket_pairs.values():
                    if stack and bracket_pairs[stack[-1][0]] == char:
                        stack.pop()
                    else:
                        # Mismatched closing bracket
                        if i + 1 == error.line_no:
                            # Try to fix by removing the problematic character
                            line_chars = list(line)
                            line_chars[j] = ''
                            lines[i] = ''.join(line_chars)
                            return '\n'.join(lines)
        
        # Unmatched opening brackets - add missing closing brackets
        if stack:
            opener, line_no, col = stack[-1]
            closer = bracket_pairs[opener]
            
            # Try to intelligently place the closing bracket
            if opener == '(':
                # For function calls/definitions, add at end of line or before comment
                target_line = lines[line_no]
                comment_pos = target_line.find('#')
                if comment_pos >= 0:
                    lines[line_no] = target_line[:comment_pos].rstrip() + closer + '  ' + target_line[comment_pos:]
                else:
                    lines[line_no] = target_line.rstrip() + closer
            else:
                # For other brackets, add at the end of the file or appropriate location
                lines.append(closer)
            
            return '\n'.join(lines)
        
        return code
    
    def _fix_string_quoting(self, code: str, error: PythonSyntaxError) -> str:
        """Fix string quoting issues."""
        if "quote" not in error.message.lower() and "string" not in error.message.lower():
            return code
        
        lines = code.splitlines()
        if error.line_no > len(lines):
            return code
        
        error_line = lines[error.line_no - 1]
        
        # Fix unmatched quotes
        single_quotes = error_line.count("'")
        double_quotes = error_line.count('"')
        
        if single_quotes % 2 == 1:
            # Odd number of single quotes, add one at the end
            lines[error.line_no - 1] = error_line + "'"
            return '\n'.join(lines)
        
        if double_quotes % 2 == 1:
            # Odd number of double quotes, add one at the end
            lines[error.line_no - 1] = error_line + '"'
            return '\n'.join(lines)
        
        return code
    
    def _fix_common_typos(self, code: str, error: PythonSyntaxError) -> str:
        """Fix common Python syntax typos."""
        lines = code.splitlines()
        if error.line_no > len(lines):
            return code
        
        error_line = lines[error.line_no - 1]
        
        # Common typos and their fixes
        typo_fixes = {
            r'\bpritn\b': 'print',
            r'\bimprot\b': 'import',
            r'\bfrom\s+(\w+)\s+improt\b': r'from \1 import',
            r'\bretrun\b': 'return',
            r'\bTrue\s*=': 'True ==',
            r'\bFalse\s*=': 'False ==',
            r'\bNone\s*=': 'None ==',
        }
        
        fixed_line = error_line
        for pattern, replacement in typo_fixes.items():
            fixed_line = re.sub(pattern, replacement, fixed_line)
        
        if fixed_line != error_line:
            lines[error.line_no - 1] = fixed_line
            return '\n'.join(lines)
        
        return code
    
    def _fix_import_errors(self, code: str, error: PythonSyntaxError) -> str:
        """Fix import statement syntax errors."""
        if "import" not in error.message.lower():
            return code
        
        lines = code.splitlines()
        if error.line_no > len(lines):
            return code
        
        error_line = lines[error.line_no - 1].strip()
        
        # Fix common import syntax errors
        import_fixes = [
            (r'^from\s+(\w+)\s*$', r'from \1 import *'),
            (r'^import\s*$', 'import sys'),
            (r'^from\s+(\w+)\s+import\s*$', r'from \1 import *'),
        ]
        
        for pattern, replacement in import_fixes:
            if re.match(pattern, error_line):
                lines[error.line_no - 1] = re.sub(pattern, replacement, error_line)
                return '\n'.join(lines)
        
        return code
    
    def _fix_function_definition_errors(self, code: str, error: PythonSyntaxError) -> str:
        """Fix function definition syntax errors."""
        lines = code.splitlines()
        if error.line_no > len(lines):
            return code
        
        error_line = lines[error.line_no - 1].strip()
        
        # Fix function definition issues
        if error_line.startswith('def '):
            # Missing parentheses
            if '(' not in error_line:
                func_name = error_line.split()[1] if len(error_line.split()) > 1 else 'function'
                lines[error.line_no - 1] = f'def {func_name}():'
                return '\n'.join(lines)
            
            # Missing colon
            if not error_line.endswith(':'):
                lines[error.line_no - 1] = error_line + ':'
                return '\n'.join(lines)
        
        return code
    
    def _fix_class_definition_errors(self, code: str, error: PythonSyntaxError) -> str:
        """Fix class definition syntax errors."""
        lines = code.splitlines()
        if error.line_no > len(lines):
            return code
        
        error_line = lines[error.line_no - 1].strip()
        
        # Fix class definition issues
        if error_line.startswith('class '):
            # Missing colon
            if not error_line.endswith(':'):
                lines[error.line_no - 1] = error_line + ':'
                return '\n'.join(lines)
        
        return code
    
    def _detect_indent_size(self, lines: List[str]) -> int:
        """Detect the indentation size used in the code."""
        indents = []
        
        for line in lines:
            stripped = line.lstrip()
            if stripped and not stripped.startswith('#'):
                indent = len(line) - len(stripped)
                if indent > 0:
                    indents.append(indent)
        
        if not indents:
            return 4  # Default to 4 spaces
        
        # Find the most common non-zero indent
        from collections import Counter
        indent_counts = Counter(indents)
        
        # Look for multiples of 2, 4, or 8
        for size in [2, 4, 8]:
            if any(indent % size == 0 for indent in indents):
                return size
        
        return 4  # Default fallback
    
    def _calculate_expected_indent(self, lines: List[str], line_idx: int, 
                                 indent_stack: List[int], indent_size: int) -> int:
        """Calculate the expected indentation for a line."""
        if line_idx < 0 or line_idx >= len(lines):
            return 0
        
        current_line = lines[line_idx].strip()
        
        # Look at previous non-empty line
        prev_line = ""
        for i in range(line_idx - 1, -1, -1):
            prev_stripped = lines[i].strip()
            if prev_stripped and not prev_stripped.startswith('#'):
                prev_line = prev_stripped
                break
        
        # Determine indentation based on previous line
        if prev_line.endswith(':'):
            # Increase indentation after colon
            return indent_stack[-1] + indent_size
        elif current_line.startswith(('else:', 'elif ', 'except:', 'except ', 'finally:')):
            # Same level as corresponding if/try
            return indent_stack[-1] if len(indent_stack) > 1 else 0
        else:
            # Same level as previous
            return indent_stack[-1]


def repair_python_syntax(code: str, max_attempts: int = 5) -> Dict[str, Any]:
    """
    Convenience function to repair Python syntax errors.
    
    Args:
        code: Python source code as string
        max_attempts: Maximum number of repair attempts
        
    Returns:
        Dictionary with repair results
    """
    engine = SyntaxRepairEngine()
    return engine.analyze_and_repair(code, max_attempts)


def repair_file_syntax(file_path: str, max_attempts: int = 5, 
                      backup: bool = True) -> Dict[str, Any]:
    """
    Repair syntax errors in a Python file.
    
    Args:
        file_path: Path to Python file
        max_attempts: Maximum number of repair attempts
        backup: Whether to create a backup of the original file
        
    Returns:
        Dictionary with repair results
    """
    path = Path(file_path)
    
    if not path.exists():
        return {
            "success": False,
            "message": f"File not found: {file_path}",
            "original_errors": [],
            "attempts": [],
            "final_errors": []
        }
    
    # Read original file
    try:
        with open(path, 'r', encoding='utf-8') as f:
            original_code = f.read()
    except Exception as e:
        return {
            "success": False,
            "message": f"Error reading file: {e}",
            "original_errors": [],
            "attempts": [],
            "final_errors": []
        }
    
    # Attempt repair
    result = repair_python_syntax(original_code, max_attempts)
    
    # Write repaired code if successful
    if result["success"] and result["fixed_code"]:
        try:
            # Create backup if requested
            if backup:
                backup_path = path.with_suffix(path.suffix + '.backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_code)
                result["backup_created"] = str(backup_path)
            
            # Write fixed code
            with open(path, 'w', encoding='utf-8') as f:
                f.write(result["fixed_code"])
            
            result["file_updated"] = True
            result["message"] += f" File updated: {file_path}"
            
        except Exception as e:
            result["success"] = False
            result["message"] = f"Error writing repaired file: {e}"
            result["file_updated"] = False
    
    return result
