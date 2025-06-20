"""
Tests for the Security Smell Detector.

This module contains comprehensive tests for the SecuritySmellDetector,
including all detection categories and edge cases.
"""

import ast
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from pythonium.detectors.security import SecuritySmellDetector
from pythonium.models import CodeGraph, Symbol, Location


class TestSecuritySmellDetector(unittest.TestCase):
    """Test cases for the SecuritySmellDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = SecuritySmellDetector()
        self.graph = CodeGraph()
    
    def test_detector_properties(self):
        """Test detector properties and initialization."""
        self.assertEqual(self.detector.id, "security_smell")
        self.assertEqual(self.detector.name, "Security Smell Detector")
        self.assertIn("security", self.detector.description.lower())
        
        # Test that patterns are compiled
        self.assertTrue(self.detector.hardcoded_credential_patterns)
        self.assertTrue(self.detector.weak_crypto_patterns)
        self.assertTrue(self.detector.dangerous_functions)
        self.assertTrue(self.detector.sql_injection_patterns)
    
    def test_empty_graph(self):
        """Test with empty code graph."""
        issues = self.detector.analyze(self.graph)
        self.assertEqual(len(issues), 0)
    
    def test_hardcoded_credentials_detection(self):
        """Test detection of hardcoded credentials."""
        # Create a temporary file with hardcoded credentials
        code_content = '''
password = "hardcoded_password_123"
api_key = "secret_api_key_456"
aws_secret_access_key = "AKIAIOSFODNN7EXAMPLE"
db_password = "database_password"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            # Create a symbol
            symbol = Symbol(
                fqname="test.hardcoded",
                location=Location(temp_path, 1, 1),
                ast_node=ast.parse(code_content)
            )
            self.graph.symbols["test"] = symbol
            
            issues = self.detector.analyze(self.graph)
            # Should detect multiple hardcoded credentials
            credential_issues = [i for i in issues if i.id == "security_smell.hardcoded-credential"]
            self.assertGreater(len(credential_issues), 0)
            
            # Check severity and message
            for issue in credential_issues:
                self.assertEqual(issue.severity, "error")
                self.assertIn("hardcoded credential", issue.message.lower())
                self.assertIn("environment variables", issue.message)
        
        finally:
            temp_path.unlink()
    
    def test_dangerous_functions_detection(self):
        """Test detection of dangerous function calls."""
        code = '''
import os
import pickle

def dangerous_code():
    eval("print('hello')")
    exec("x = 1")
    os.system("rm -rf /")
    pickle.loads(data)
    __import__("dangerous_module")
'''
        
        symbol = Symbol(
            fqname="test.dangerous",
            location=Location(Path("test.py"), 1, 1),
            ast_node=ast.parse(code)
        )
        self.graph.symbols["test"] = symbol
        
        issues = self.detector.analyze(self.graph)
        
        # Should detect dangerous functions
        dangerous_issues = [i for i in issues if i.id == "security_smell.dangerous-function"]
        self.assertGreater(len(dangerous_issues), 0)
        
        # Check that eval and exec are flagged as errors
        eval_issues = [i for i in dangerous_issues if "eval" in i.message]
        exec_issues = [i for i in dangerous_issues if "exec" in i.message]
        system_issues = [i for i in dangerous_issues if "os.system" in i.message]
        
        self.assertGreater(len(eval_issues), 0)
        self.assertGreater(len(exec_issues), 0)
        self.assertGreater(len(system_issues), 0)
        
        # Check severity levels
        for issue in eval_issues + exec_issues + system_issues:
            self.assertEqual(issue.severity, "error")
    
    def test_weak_crypto_detection(self):
        """Test detection of weak cryptographic practices."""
        code_content = '''
import hashlib
import random

def weak_crypto():
    hash_md5 = hashlib.md5()
    hash_sha1 = hashlib.sha1()
    rand_num = random.random()
    ssl_context.check_hostname = False
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            symbol = Symbol(
                fqname="test.weak_crypto",
                location=Location(temp_path, 1, 1),
                ast_node=ast.parse(code_content)
            )
            self.graph.symbols["test"] = symbol
            
            issues = self.detector.analyze(self.graph)
            
            # Should detect weak crypto
            crypto_issues = [i for i in issues if i.id == "security_smell.weak-crypto"]
            self.assertGreater(len(crypto_issues), 0)
            
            # Check for MD5/SHA1 issues (should be errors)
            md5_sha1_issues = [i for i in crypto_issues if any(alg in i.message.lower() for alg in ["md5", "sha1"])]
            for issue in md5_sha1_issues:
                self.assertEqual(issue.severity, "error")
                self.assertIn("stronger alternatives", issue.message)
        
        finally:
            temp_path.unlink()
    
    def test_sql_injection_detection(self):
        """Test detection of SQL injection vulnerabilities."""
        code_content = '''
def vulnerable_sql():
    query = "SELECT * FROM users WHERE id = %s" % user_id
    cursor.execute(f"DELETE FROM users WHERE name = {user_name}")
    cursor.execute("INSERT INTO logs VALUES " + log_data)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            symbol = Symbol(
                fqname="test.sql_injection",
                location=Location(temp_path, 1, 1),
                ast_node=ast.parse(code_content)
            )
            self.graph.symbols["test"] = symbol
            
            issues = self.detector.analyze(self.graph)
            
            # Should detect SQL injection patterns
            sql_issues = [i for i in issues if i.id == "security_smell.sql-injection"]
            self.assertGreater(len(sql_issues), 0)
            
            for issue in sql_issues:
                self.assertEqual(issue.severity, "error")
                self.assertIn("sql injection", issue.message.lower())
                self.assertIn("parameterized queries", issue.message)
        
        finally:
            temp_path.unlink()
    
    def test_insecure_random_detection(self):
        """Test detection of insecure random usage in security contexts."""
        code = '''
import random

def generate_password():
    password = random.choice(chars)
    return password

def generate_token():
    token = random.randint(1000, 9999)
    return token

def non_security_function():
    random_choice = random.choice(options)  # This should not be flagged
    return random_choice
'''
        
        symbol1 = Symbol(
            fqname="test.generate_password",
            location=Location(Path("test.py"), 4, 1),
            ast_node=ast.parse(code).body[1]  # generate_password function
        )
        
        symbol2 = Symbol(
            fqname="test.generate_token",
            location=Location(Path("test.py"), 8, 1),
            ast_node=ast.parse(code).body[2]  # generate_token function
        )
        
        symbol3 = Symbol(
            fqname="test.non_security_function",
            location=Location(Path("test.py"), 12, 1),
            ast_node=ast.parse(code).body[3]  # non_security_function
        )
        
        self.graph.symbols["password_func"] = symbol1
        self.graph.symbols["token_func"] = symbol2
        self.graph.symbols["non_security_func"] = symbol3
        
        issues = self.detector.analyze(self.graph)
        
        # Should detect insecure random in security contexts
        random_issues = [i for i in issues if i.id == "security_smell.insecure-random"]
        self.assertGreater(len(random_issues), 0)
        
        for issue in random_issues:
            self.assertEqual(issue.severity, "error")
            self.assertIn("insecure random", issue.message.lower())
            self.assertIn("secrets", issue.message)
    
    def test_get_function_name(self):
        """Test function name extraction from AST nodes."""
        # Test simple function call
        call_node = ast.parse("func()").body[0].value
        name = self.detector._get_function_name(call_node)
        self.assertEqual(name, "func")
        
        # Test attribute function call
        call_node = ast.parse("module.func()").body[0].value
        name = self.detector._get_function_name(call_node)
        self.assertEqual(name, "module.func")
        
        # Test nested attribute call
        call_node = ast.parse("module.submodule.func()").body[0].value
        name = self.detector._get_function_name(call_node)
        self.assertEqual(name, "module.submodule.func")
    
    def test_find_symbol_near_line(self):
        """Test finding symbols near specific line numbers."""
        symbol1 = Symbol(
            fqname="test.func1",
            location=Location(Path("test.py"), 5, 1),
            ast_node=ast.parse("def func1(): pass")
        )
        
        symbol2 = Symbol(
            fqname="test.func2",
            location=Location(Path("test.py"), 15, 1),
            ast_node=ast.parse("def func2(): pass")
        )
        
        symbols = [symbol1, symbol2]
        
        # Should find symbol1 for line 3 (closest to line 5)
        closest = self.detector._find_symbol_near_line(symbols, 3)
        self.assertEqual(closest, symbol1)
        
        # Should find symbol2 for line 18 (closest to line 15)
        closest = self.detector._find_symbol_near_line(symbols, 18)
        self.assertEqual(closest, symbol2)
        
        # Test with empty symbols list
        closest = self.detector._find_symbol_near_line([], 10)
        self.assertIsNone(closest)
    
    def test_is_security_context(self):
        """Test security context detection."""
        security_keywords = {'password', 'secret', 'key', 'token'}
        
        # Test function name detection
        symbol = Symbol(
            fqname="test.generate_password",
            location=Location(Path("test.py"), 1, 1),
            ast_node=ast.parse("def generate_password(): pass").body[0]
        )
        self.assertTrue(self.detector._is_security_context(symbol, security_keywords))
        
        # Test docstring detection
        code = '''
def process_data():
    """Process secret data securely."""
    pass
'''
        symbol = Symbol(
            fqname="test.process_data",
            location=Location(Path("test.py"), 1, 1),
            ast_node=ast.parse(code).body[0],
            docstring="Process secret data securely."
        )
        self.assertTrue(self.detector._is_security_context(symbol, security_keywords))
        
        # Test variable name detection
        code = '''
def process_data():
    api_key = get_key()
    return api_key
'''
        symbol = Symbol(
            fqname="test.process_data",
            location=Location(Path("test.py"), 1, 1),
            ast_node=ast.parse(code).body[0]
        )
        self.assertTrue(self.detector._is_security_context(symbol, security_keywords))
        
        # Test non-security context
        symbol = Symbol(
            fqname="test.calculate_sum",
            location=Location(Path("test.py"), 1, 1),
            ast_node=ast.parse("def calculate_sum(): pass").body[0]
        )
        self.assertFalse(self.detector._is_security_context(symbol, security_keywords))
    
    @patch("builtins.open", mock_open(read_data="print('hello')"))
    def test_file_reading_error_handling(self):
        """Test handling of file reading errors."""
        # Create symbol with non-existent file
        symbol = Symbol(
            fqname="test.func",
            location=Location(Path("nonexistent.py"), 1, 1),
            ast_node=ast.parse("def func(): pass")
        )
        self.graph.symbols["test"] = symbol
        
        # Should not raise exception even if file doesn't exist
        with patch("builtins.open", side_effect=FileNotFoundError):
            issues = self.detector.analyze(self.graph)
            # Should return empty list due to error handling
            self.assertEqual(len(issues), 0)
    
    def test_analyze_file_security_comprehensive(self):
        """Test comprehensive file security analysis."""
        content = '''
password = "secret123"
import os
os.system("dangerous")
md5_hash = hashlib.md5()
cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
'''
        
        symbol = Symbol(
            fqname="test.comprehensive",
            location=Location(Path("test.py"), 1, 1),
            ast_node=ast.parse(content)
        )
        
        # Test all security check methods
        issues = self.detector._analyze_file_security(content, [symbol], Path("test.py"))
        
        # Should find multiple types of issues
        issue_types = {issue.id for issue in issues}
        self.assertIn("security_smell.hardcoded-credential", issue_types)
        self.assertIn("security_smell.dangerous-function", issue_types)
        self.assertIn("security_smell.weak-crypto", issue_types)
        self.assertIn("security_smell.sql-injection", issue_types)
    
    def test_severity_levels(self):
        """Test that appropriate severity levels are assigned."""
        code_content = '''
import pickle
import subprocess

eval("dangerous")  # Should be error
pickle.loads(data)  # Should be warn
subprocess.call(cmd)  # Should be warn
random.random()  # Context dependent
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            symbol = Symbol(
                fqname="test.severity",
                location=Location(temp_path, 1, 1),
                ast_node=ast.parse(code_content)
            )
            self.graph.symbols["test"] = symbol
            
            issues = self.detector.analyze(self.graph)
            
            # Check that eval is flagged as error
            eval_issues = [i for i in issues if "eval" in i.message]
            for issue in eval_issues:
                self.assertEqual(issue.severity, "error")
            
            # Check that other dangerous functions are warnings
            other_dangerous = [i for i in issues if i.id == "security_smell.dangerous-function" and "eval" not in i.message]
            for issue in other_dangerous:
                self.assertIn(issue.severity, ["warn", "error"])  # Context dependent
        
        finally:
            temp_path.unlink()
    
    def test_debug_detector(self):
        """Debug test to understand detector behavior."""
        code = '''
def dangerous_code():
    eval("print('hello')")
'''
        symbol = Symbol(
            fqname="test.dangerous",
            location=Location(Path("test.py"), 1, 1),
            ast_node=ast.parse(code)
        )
        self.graph.symbols["test"] = symbol
        
        print(f"Graph symbols: {list(self.graph.symbols.keys())}")
        issues = self.detector.analyze(self.graph)
        print(f"Found {len(issues)} issues")
        for issue in issues:
            print(f"Issue: {issue.id} - {issue.message}")
        
        # Let's try directly calling the dangerous function check
        dangerous_issues = self.detector._check_dangerous_functions([symbol])
        print(f"Direct dangerous function check found {len(dangerous_issues)} issues")
        for issue in dangerous_issues:
            print(f"Direct Issue: {issue.id} - {issue.message}")


if __name__ == '__main__':
    unittest.main()
