"""
High-performance Python syntax analysis and repair functionality.

This module provides optimized capabilities for detecting and automatically
fixing Python syntax errors with special focus on common issues like:
- Indentation errors (off by a few spaces/tabs)
- Missing newlines causing two lines to be merged
- Other common syntax problems

The implementation uses fast-path detection for common cases to maximize performance.
"""

import ast
import re
import tokenize
import io
from typing import List, Tuple, Optional, Dict, Any, Set
from pathlib import Path
import logging
from functools import lru_cache

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


class OptimizedSyntaxRepairEngine:
    """
    High-performance Python syntax repair engine optimized for common cases.
    
    This engine uses a two-tier approach:
    1. Fast-path detection and repair for common issues (indentation, newlines)
    2. Fallback to comprehensive repair strategies for complex cases
    """
    
    def __init__(self):
        # Cache for parsed code to avoid repeated AST parsing
        self._parse_cache = {}
        self._error_cache = {}
        
        # Fast-path patterns for common issues
        self._indent_patterns = {
            'missing_indent': re.compile(r'^(\s*)(def|class|if|elif|else|for|while|try|except|finally|with)\s.*:$', re.MULTILINE),
            'extra_indent': re.compile(r'^(\s{5,})(\S.*)', re.MULTILINE),  # 5+ spaces might be wrong indent
            'mixed_indent': re.compile(r'^(\t+ +| +\t+)', re.MULTILINE),  # Mixed tabs and spaces
        }
        
        # Patterns for detecting merged lines
        self._merged_line_patterns = [
            re.compile(r':\s*\w'),  # colon followed immediately by code (should be newline)
            re.compile(r'(def|class|if|elif|else|for|while|try|except|finally|with)\s+[^:]*:\s*\w+'),
            re.compile(r'^\s*import\s+\w+\s+\w+'),  # Multiple statements on import line
        ]
        
        # Lightweight repair strategies (fast-path)
        self.fast_strategies = [
            self._fast_fix_indentation,
            self._fast_fix_merged_lines,
            self._fast_fix_missing_colons,
        ]
        
        # Comprehensive repair strategies (fallback)
        self.comprehensive_strategies = [
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
        Uses optimized fast-path detection for common issues.
        
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
            - fast_path_used: Whether fast-path optimization was used
        """
        original_code = code
        current_code = code
        attempts = []
        fast_path_used = False
        
        # Quick validation - check if code is already valid
        if self._is_valid_python(original_code):
            return {
                "success": True,
                "fixed_code": original_code,
                "original_errors": [],
                "attempts": [],
                "final_errors": [],
                "fast_path_used": False,
                "message": "No syntax errors found in original code"
            }
        
        # Analyze original code for errors
        original_errors = self._analyze_syntax_errors(original_code)
        
        # Try fast-path repairs first for common issues
        fast_path_result = self._try_fast_path_repairs(current_code, original_errors)
        if fast_path_result["success"]:
            return {
                "success": True,
                "fixed_code": fast_path_result["fixed_code"],
                "original_errors": [str(e) for e in original_errors],
                "attempts": fast_path_result["attempts"],
                "final_errors": [],
                "fast_path_used": True,
                "message": f"Successfully fixed all syntax errors using fast-path optimization in {len(fast_path_result['attempts'])} attempt(s)"
            }
        elif fast_path_result["fixed_code"] != current_code:
            # Fast path made some progress, continue with the improved code
            current_code = fast_path_result["fixed_code"]
            attempts.extend(fast_path_result["attempts"])
            fast_path_used = True
        
        # Fallback to comprehensive repair strategies
        for attempt in range(max_attempts - len(attempts)):
            errors = self._analyze_syntax_errors(current_code)
            
            if not errors:
                return {
                    "success": True,
                    "fixed_code": current_code,
                    "original_errors": [str(e) for e in original_errors],
                    "attempts": attempts,
                    "final_errors": [],
                    "fast_path_used": fast_path_used,
                    "message": f"Successfully fixed all syntax errors in {len(attempts)} attempt(s)"
                }
            
            # Try to fix the first error using comprehensive strategies
            fixed_code = self._attempt_comprehensive_repair(current_code, errors[0])
            
            if fixed_code == current_code:
                # No changes made, give up
                attempts.append({
                    "attempt": len(attempts) + 1,
                    "error": str(errors[0]),
                    "strategy": "no_applicable_strategy",
                    "success": False
                })
                break
            
            attempts.append({
                "attempt": len(attempts) + 1,
                "error": str(errors[0]),
                "strategy": "comprehensive_repair",
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
            "fast_path_used": fast_path_used,
            "message": f"Unable to fix all syntax errors after {max_attempts} attempts"
        }
    @lru_cache(maxsize=100)
    def _is_valid_python(self, code: str) -> bool:
        """Fast check if code is already valid Python."""
        try:
            ast.parse(code)
            return True
        except:
            return False
    
    def _try_fast_path_repairs(self, code: str, errors: List[PythonSyntaxError]) -> Dict[str, Any]:
        """Try fast-path repairs for common issues."""
        current_code = code
        attempts = []
        
        for strategy in self.fast_strategies:
            try:
                fixed_code = strategy(current_code, errors)
                if fixed_code != current_code:
                    attempts.append({
                        "attempt": len(attempts) + 1,
                        "strategy": strategy.__name__,
                        "success": True,
                        "fast_path": True
                    })
                    current_code = fixed_code
                    
                    # Check if we've fixed all issues
                    if self._is_valid_python(current_code):
                        return {
                            "success": True,
                            "fixed_code": current_code,
                            "attempts": attempts
                        }
            except Exception as e:
                logger.debug(f"Fast-path strategy {strategy.__name__} failed: {e}")
        
        return {
            "success": False,
            "fixed_code": current_code,
            "attempts": attempts
        }
    
    def _fast_fix_indentation(self, code: str, errors: List[PythonSyntaxError]) -> str:
        """Fast fix for simple indentation errors with proper scope tracking."""
        # Check if any errors are indentation-related or return outside function
        has_indent_error = any(
            "indent" in error.message.lower() or 
            "expected an indented block" in error.message or
            "unindent does not match" in error.message or
            "return" in error.message.lower() and "outside function" in error.message.lower()
            for error in errors
        )
        
        if not has_indent_error:
            return code
        
        lines = code.splitlines()
        if not lines:
            return code
        
        # Quick indent size detection
        indent_size = self._quick_detect_indent_size(lines)
        
        # Better scope tracking - track (scope_type, indent_level)
        scope_stack = []
        fixed_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            current_indent = len(line) - len(stripped)
            
            # Determine line type
            is_class_def = stripped.startswith('class ')
            is_func_def = stripped.startswith('def ')
            is_return = stripped.startswith('return ')
            is_control_flow = any(stripped.startswith(kw) for kw in ['for ', 'while ', 'if ', 'elif ', 'else:', 'try:', 'except', 'finally:', 'with '])
            ends_with_colon = line.rstrip().endswith(':')
            
            # Pop scopes that we've exited
            while scope_stack and current_indent <= scope_stack[-1][1]:
                # Special case: if this is a method definition and we're in a class,
                # and the current indent is class_indent + indent_size, keep the class scope
                if (is_func_def and scope_stack and scope_stack[-1][0] == 'class' and 
                    current_indent == scope_stack[-1][1] + indent_size):
                    break
                scope_stack.pop()
            
            # Determine expected indentation
            if not scope_stack:
                expected_indent = 0
            else:
                # We're inside some scope
                if is_func_def and scope_stack and scope_stack[-1][0] == 'class':
                    # Method definition inside class
                    expected_indent = scope_stack[-1][1] + indent_size
                elif is_class_def or (is_func_def and not scope_stack):
                    # Top-level class or function
                    expected_indent = 0
                elif is_return and scope_stack:
                    # Return statement should be inside nearest function
                    for scope_type, scope_indent in reversed(scope_stack):
                        if scope_type == 'function':
                            expected_indent = scope_indent + indent_size
                            break
                    else:
                        # No function scope found, this is an error
                        expected_indent = scope_stack[-1][1] + indent_size
                elif is_control_flow and scope_stack:
                    # Control flow should be at current scope level
                    expected_indent = scope_stack[-1][1] + indent_size
                else:
                    # Regular statement inside current scope
                    expected_indent = scope_stack[-1][1] + indent_size
            
            # Special handling: if this looks like code that should be inside the previous function
            if (current_indent == 0 and scope_stack and 
                (is_control_flow or is_return or stripped.startswith(('result', 'data', 'item', 'value'))) and
                scope_stack[-1][0] == 'function'):
                # This code probably belongs inside the function
                expected_indent = scope_stack[-1][1] + indent_size
            
            # Apply fix if needed
            if current_indent != expected_indent and abs(current_indent - expected_indent) <= 12:
                fixed_line = ' ' * expected_indent + stripped
                fixed_lines.append(fixed_line)
                current_indent = expected_indent
            else:
                fixed_lines.append(line)
            
            # Add new scope if this line starts one
            if ends_with_colon:
                if is_class_def:
                    scope_stack.append(('class', current_indent))
                elif is_func_def:
                    scope_stack.append(('function', current_indent))
                else:
                    scope_stack.append(('block', current_indent))
        
        return '\n'.join(fixed_lines)
    
    def _fast_fix_merged_lines(self, code: str, errors: List[PythonSyntaxError]) -> str:
        """Fast fix for lines that should be split (missing newlines)."""
        lines = code.splitlines()
        fixed_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            original_line = line
            line_was_split = False
            
            # Check for colon followed by non-whitespace (should be newline)
            if ':' in stripped and not stripped.endswith(':'):
                colon_pos = stripped.find(':')
                after_colon = stripped[colon_pos + 1:].strip()
                
                # If there's significant code after colon (not just a comment)
                if after_colon and not after_colon.startswith('#'):
                    # Check if this looks like it should be split
                    before_colon = stripped[:colon_pos + 1]
                    
                    # Keywords that should definitely be followed by newline
                    control_keywords = ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 'with']
                    should_split = any(before_colon.strip().startswith(f'{keyword} ') or before_colon.strip() == keyword for keyword in control_keywords)
                    
                    if should_split:
                        # Split the line
                        indent = len(line) - len(line.lstrip())
                        before_line = ' ' * indent + before_colon
                        
                        # Determine appropriate indent for the next line
                        next_indent = indent + self._quick_detect_indent_size(lines)
                        after_line = ' ' * next_indent + after_colon
                        
                        fixed_lines.append(before_line)
                        fixed_lines.append(after_line)
                        line_was_split = True
            
            # Check for multiple statements on one line (semicolon separated or space separated keywords)
            if not line_was_split:
                # Look for patterns like "import sys import os" or "a = 1; b = 2"
                if ';' in stripped:
                    # Split on semicolons
                    indent = len(line) - len(line.lstrip())
                    parts = [part.strip() for part in stripped.split(';') if part.strip()]
                    if len(parts) > 1:
                        for i, part in enumerate(parts):
                            fixed_lines.append(' ' * indent + part)
                        line_was_split = True
                
                # Look for import statements with multiple imports on one line
                elif 'import' in stripped and ' import ' in stripped:
                    # Check if this looks like "import sys import os"
                    import_parts = re.findall(r'\b(?:import|from)\s+\w+(?:\.\w+)*(?:\s+import\s+\w+)?', stripped)
                    if len(import_parts) > 1:
                        indent = len(line) - len(line.lstrip())
                        for part in import_parts:
                            fixed_lines.append(' ' * indent + part.strip())
                        line_was_split = True
            
            # If line wasn't split, keep the original
            if not line_was_split:
                fixed_lines.append(original_line)
        
        return '\n'.join(fixed_lines)
    
    def _fast_fix_missing_colons(self, code: str, errors: List[PythonSyntaxError]) -> str:
        """Fast fix for missing colons in control structures."""
        lines = code.splitlines()
        fixed_lines = []
        
        # Keywords that should end with colons
        colon_keywords = ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 'with']
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Check if line starts with a keyword that should end with colon
            should_have_colon = any(
                stripped.startswith(f'{keyword} ') or stripped == keyword
                for keyword in colon_keywords
            )
            
            if should_have_colon and not line.rstrip().endswith(':'):
                # Add missing colon
                comment_pos = line.find('#')
                if comment_pos >= 0:
                    fixed_line = line[:comment_pos].rstrip() + ':  ' + line[comment_pos:]
                else:
                    fixed_line = line.rstrip() + ':'
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _quick_detect_indent_size(self, lines: List[str]) -> int:
        """Quickly detect indentation size from first few indented lines."""
        for line in lines[:20]:  # Only check first 20 lines for speed
            stripped = line.lstrip()
            if stripped and not stripped.startswith('#'):
                indent = len(line) - len(stripped)
                if indent > 0:
                    # Common indent sizes
                    if indent % 4 == 0:
                        return 4
                    elif indent % 2 == 0:
                        return 2
                    elif indent % 8 == 0:
                        return 8
                    else:
                        return indent
        return 4  # Default fallback
    
    def _analyze_syntax_errors(self, code: str) -> List[PythonSyntaxError]:
        """Analyze code and return list of syntax errors with caching."""
        # Use cache to avoid repeated parsing
        code_hash = hash(code)
        if code_hash in self._error_cache:
            return self._error_cache[code_hash]
        
        errors = []
        
        # Try to parse with AST
        try:
            ast.parse(code)
            self._error_cache[code_hash] = []
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
        
        # Cache and return results
        self._error_cache[code_hash] = errors
        return errors
    
    def _attempt_comprehensive_repair(self, code: str, error: PythonSyntaxError) -> str:
        """Attempt to repair using comprehensive strategies (fallback)."""
        for strategy in self.comprehensive_strategies:
            try:
                fixed_code = strategy(code, error)
                if fixed_code != code:
                    return fixed_code
            except Exception as e:
                logger.debug(f"Comprehensive repair strategy failed: {e}")
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


# Backward compatibility class
class SyntaxRepairEngine(OptimizedSyntaxRepairEngine):
    """
    Backward compatibility wrapper around OptimizedSyntaxRepairEngine.
    
    This class maintains the same interface as the original SyntaxRepairEngine
    but uses the optimized implementation under the hood.
    """
    
    def __init__(self):
        super().__init__()
        # Map old repair_strategies to new comprehensive_strategies for compatibility
        self.repair_strategies = self.comprehensive_strategies


def repair_python_syntax(code: str, max_attempts: int = 5) -> Dict[str, Any]:
    """
    Convenience function to repair Python syntax errors using optimized engine.
    
    Args:
        code: Python source code as string
        max_attempts: Maximum number of repair attempts
        
    Returns:
        Dictionary with repair results
    """
    engine = OptimizedSyntaxRepairEngine()
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
