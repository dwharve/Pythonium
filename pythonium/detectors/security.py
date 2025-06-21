"""
Security Smell Detector

This module detects common security smells and potential vulnerabilities using
heuristics and pattern matching. While not a comprehensive security scanner,
it identifies common Python security anti-patterns and dangerous practices
that could lead to vulnerabilities.

The detector identifies:
- Hardcoded credentials and secrets
- Weak cryptographic practices
- Dangerous function calls (eval, exec, etc.)
- SQL injection vulnerabilities
- Insecure file operations
- Command injection risks
- Weak random number generation
- SSL/TLS configuration issues

Note: This detector uses heuristics and may produce false positives.
It is intended as a first-line defense and should be supplemented with
dedicated security tools for comprehensive security analysis.

Example:
    ```python
    detector = SecuritySmellDetector()
    issues = detector.analyze(graph)
    
    for issue in issues:
        if issue.severity == "critical":
            print(f"Security issue: {issue.message}")
    ```
"""

import ast
import re
import logging
from typing import List, Set, Dict, Any, Pattern
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol
from . import BaseDetector

logger = logging.getLogger(__name__)


class SecuritySmellDetector(BaseDetector):
    """
    Detects common security smells and potential vulnerabilities.
    
    This detector uses pattern matching and heuristics to identify common
    security anti-patterns in Python code. It is designed to catch obvious
    security issues and educate developers about secure coding practices.
    
    Detection categories:
    - Hardcoded credentials (passwords, API keys, tokens)
    - Weak cryptographic practices (MD5, SHA1, weak random)
    - Dangerous function calls (eval, exec, pickle.loads)
    - SQL injection vulnerabilities
    - Command injection risks
    - Insecure file operations
    - SSL/TLS configuration issues
    
    Note: This detector uses heuristics and may produce false positives.
    Manual review is recommended for all findings.
    
    Attributes:
        hardcoded_credential_patterns: Regex patterns for credential detection
        weak_crypto_patterns: Patterns for weak cryptographic usage
        dangerous_functions: Set of function names considered dangerous
        sql_injection_patterns: Patterns for SQL injection detection
    """
    
    id = "security_smell"
    name = "Security Smell Detector"
    description = "Detects potential security vulnerabilities and anti-patterns"
    
    # Enhanced metadata for MCP server
    category = "Security & Safety"
    usage_tips = "Run before production deployments and during security reviews to identify potential vulnerabilities"
    related_detectors = ["deprecated_api"]
    typical_severity = "error"
    detailed_description = ("Identifies potential security vulnerabilities, unsafe practices, and code patterns "
                           "that could lead to security issues including hardcoded secrets, weak cryptography, "
                           "dangerous function calls, and injection vulnerabilities.")
    
    def __init__(self, **options):
        """
        Initialize the security smell detector.
        
        The detector compiles regex patterns for efficient matching and
        sets up detection rules for various security anti-patterns.
        """
        super().__init__(**options)
        
        # Compile regex patterns for efficiency
        self.hardcoded_credential_patterns = [
            re.compile(r'(?i)(password|pwd|secret|key|token|api_key|auth)\s*[=:]\s*["\'][^"\']{3,}["\']'),
            re.compile(r'(?i)aws_secret_access_key\s*[=:]\s*["\'][^"\']+["\']'),
            re.compile(r'(?i)private_key\s*[=:]\s*["\'][^"\']+["\']'),
            re.compile(r'(?i)db_password\s*[=:]\s*["\'][^"\']+["\']'),
        ]
        
        self.weak_crypto_patterns = [
            re.compile(r'(?i)md5|sha1'),
            re.compile(r'(?i)random\.random|random\.randint'),
            re.compile(r'(?i)ssl.*verify.*false|ssl.*check_hostname.*false'),
        ]
        
        # Dangerous function calls to detect
        self.dangerous_functions = {
            'eval', 'exec', 'compile', '__import__',
            'input',  # In Python 2, input() was dangerous
            'pickle.loads', 'pickle.load',
            'marshal.loads', 'marshal.load',
            'subprocess.call', 'os.system', 'os.popen',
            'tempfile.mktemp',  # Deprecated in favor of mkstemp
        }
        
        # SQL injection prone patterns
        self.sql_injection_patterns = [
            re.compile(r'(?i)execute\s*\(\s*["\'][^"\']*%[sd][^"\']*["\']'),
            re.compile(r'(?i)execute\s*\(\s*f["\'][^"\']*{[^}]+}[^"\']*["\']'),
            re.compile(r'(?i)(select|insert|update|delete).*\+.*["\']'),        ]
    
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Find security smells in the codebase."""
        issues = []
        
        # Group symbols by file for batch processing
        files_symbols = {}
        for symbol in graph.symbols.values():
            if symbol.location and symbol.location.file:
                file_path = symbol.location.file
                if file_path not in files_symbols:
                    files_symbols[file_path] = []
                files_symbols[file_path].append(symbol)
        
        # Analyze each file
        for file_path, symbols in files_symbols.items():
            # Use content from the shared repository
            content = self.get_file_content(graph, file_path)
            if content is None:
                # Skip analysis if content not available - no fallback logic
                logger.debug("Skipping security analysis for %s - no file content available", file_path)
                continue
            
            # Perform security analysis
            file_issues = self._analyze_file_security(content, symbols, file_path)
            issues.extend(file_issues)
        
        return issues
    
    def _analyze_file_security(self, content: str, symbols: List[Symbol], file_path: Path) -> List[Issue]:
        """Analyze security issues for a single file."""
        issues = []
        
        # Check for hardcoded credentials
        issues.extend(self._check_hardcoded_credentials(content, symbols, file_path))
        
        # Check for dangerous function usage
        issues.extend(self._check_dangerous_functions(symbols))
        
        # Check for weak cryptography
        issues.extend(self._check_weak_crypto(content, symbols, file_path))
        
        # Check for SQL injection patterns
        issues.extend(self._check_sql_injection(content, symbols, file_path))
        
        # Check for insecure random usage
        issues.extend(self._check_insecure_random(symbols))
        
        return issues
    
    def _check_hardcoded_credentials(self, content: str, symbols: List[Symbol], file_path: Path) -> List[Issue]:
        """Check for hardcoded credentials in the code."""
        issues = []
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in self.hardcoded_credential_patterns:
                if pattern.search(line):
                    # Find a symbol close to this line for location context
                    symbol = self._find_symbol_near_line(symbols, line_num)
                    
                    issues.append(self.create_issue(
                        issue_id="hardcoded-credential",
                        message=f"Potential hardcoded credential found at line {line_num}. "
                               f"Consider using environment variables or secure credential storage.",
                        severity="error",
                        symbol=symbol,
                        location=symbol.location if symbol else None,
                        metadata={
                            "line_number": line_num,
                            "file": str(file_path),
                            "pattern_type": "hardcoded_credential"
                        }
                    ))
        
        return issues
    
    def _check_dangerous_functions(self, symbols: List[Symbol]) -> List[Issue]:
        """Check for usage of dangerous functions."""
        issues = []
        
        for symbol in symbols:
            # Look for function calls in the AST
            for node in ast.walk(symbol.ast_node):
                if isinstance(node, ast.Call):
                    func_name = self._get_function_name(node)
                    if func_name in self.dangerous_functions:
                        severity = "error" if func_name in {'eval', 'exec', 'os.system'} else "warn"
                        
                        issues.append(self.create_issue(
                            issue_id="dangerous-function",
                            message=f"Usage of potentially dangerous function '{func_name}'. "
                                   f"Consider safer alternatives.",
                            severity=severity,
                            symbol=symbol,
                            metadata={
                                "function_name": func_name,
                                "danger_level": "high" if severity == "error" else "medium"
                            }
                        ))
        
        return issues
    
    def _check_weak_crypto(self, content: str, symbols: List[Symbol], file_path: Path) -> List[Issue]:
        """Check for weak cryptographic practices."""
        issues = []
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in self.weak_crypto_patterns:
                if pattern.search(line):
                    symbol = self._find_symbol_near_line(symbols, line_num)
                    
                    severity = "error" if "md5" in line.lower() or "sha1" in line.lower() else "warn"
                    
                    issues.append(self.create_issue(
                        issue_id="weak-crypto",
                        message=f"Weak cryptographic practice detected at line {line_num}. "
                               f"Consider using stronger alternatives (SHA-256, secrets module, etc.).",
                        severity=severity,
                        symbol=symbol,
                        location=symbol.location if symbol else None,
                        metadata={
                            "line_number": line_num,
                            "file": str(file_path),
                            "pattern_type": "weak_crypto"
                        }
                    ))
        
        return issues
    
    def _check_sql_injection(self, content: str, symbols: List[Symbol], file_path: Path) -> List[Issue]:
        """Check for potential SQL injection vulnerabilities."""
        issues = []
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in self.sql_injection_patterns:
                if pattern.search(line):
                    symbol = self._find_symbol_near_line(symbols, line_num)
                    
                    issues.append(self.create_issue(
                        issue_id="sql-injection",
                        message=f"Potential SQL injection vulnerability at line {line_num}. "
                               f"Use parameterized queries instead of string formatting.",
                        severity="error",
                        symbol=symbol,
                        location=symbol.location if symbol else None,
                        metadata={
                            "line_number": line_num,
                            "file": str(file_path),
                            "vulnerability_type": "sql_injection"
                        }
                    ))
        
        return issues
    
    def _check_insecure_random(self, symbols: List[Symbol]) -> List[Issue]:
        """Check for insecure random number generation."""
        issues = []
        
        for symbol in symbols:
            for node in ast.walk(symbol.ast_node):
                if isinstance(node, ast.Call):
                    func_name = self._get_function_name(node)
                    
                    # Check for insecure random usage in security contexts
                    if func_name in {'random.random', 'random.randint', 'random.choice'}:
                        # Look for security-related variable names in context
                        security_keywords = {'password', 'secret', 'key', 'token', 'nonce', 'salt'}
                        
                        # Check if this is in a security context
                        if self._is_security_context(symbol, security_keywords):
                            issues.append(self.create_issue(
                                issue_id="insecure-random",
                                message=f"Insecure random number generation in security context. "
                                       f"Use 'secrets' module for cryptographically secure randomness.",
                                severity="error",
                                symbol=symbol,
                                metadata={
                                    "function_name": func_name,
                                    "recommendation": "Use secrets.randbelow(), secrets.choice(), or secrets.token_bytes()"
                                }
                            ))
        
        return issues
    
    def _get_function_name(self, call_node: ast.Call) -> str:
        """Extract function name from a call node."""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            # Handle module.function calls
            parts = []
            node = call_node.func
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return '.'.join(reversed(parts))
        return "unknown"
    
    def _find_symbol_near_line(self, symbols: List[Symbol], line_num: int) -> Symbol:
        """Find a symbol that's closest to the given line number."""
        if not symbols:
            return None
        
        # Find the symbol with the closest line number
        closest_symbol = min(
            symbols,
            key=lambda s: abs(s.location.line - line_num) if s.location else float('inf')
        )
        
        return closest_symbol
    
    def _is_security_context(self, symbol: Symbol, security_keywords: Set[str]) -> bool:
        """Check if a symbol is in a security-related context."""
        # Check function name
        func_name = symbol.fqname.lower()
        if any(keyword in func_name for keyword in security_keywords):
            return True
        
        # Check docstring
        if symbol.docstring:
            docstring_lower = symbol.docstring.lower()
            if any(keyword in docstring_lower for keyword in security_keywords):
                return True
        
        # Check variable names in the function
        for node in ast.walk(symbol.ast_node):
            if isinstance(node, ast.Name):
                var_name = node.id.lower()
                if any(keyword in var_name for keyword in security_keywords):
                    return True
        
        return False
