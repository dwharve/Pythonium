"""
Stub Implementation Detector

This detector identifies stub, mock, fake, simulated, and fallback implementations
in Python code. These are typically temporary or testing-related implementations
that may need to be replaced with actual implementations in production code.

The detector looks for:
- Functions/methods with names containing 'stub', 'mock', 'fake', 'dummy', 'simulate', 'fallback'
- Functions/methods that only raise NotImplementedError
- Functions/methods with minimal implementations (pass, return None, etc.)
- Classes or functions decorated with testing-related decorators
- Functions that return hardcoded values without logic
- TODO/FIXME comments indicating temporary implementations

Example:
    ```python
    # These would be detected:
    def stub_user_service():
        return None
    
    def mock_payment_processor():
        return {"status": "success"}
    
    def get_data_fake():
        return []
    
    class DummyEmailService:
        def send(self, email):
            pass  # TODO: implement actual email sending
    
    def fallback_algorithm():
        raise NotImplementedError("Use optimized version when available")
    ```
"""

import ast
import re
from typing import List, Set, Dict, Optional
from pathlib import Path

from ..models import CodeGraph, Issue, Symbol, Location
from . import BaseDetector


class StubImplementationDetector(BaseDetector):
    """
    Detects stub, mock, fake, simulated, and fallback implementations.
    
    This detector identifies code that appears to be temporary, testing-related,
    or placeholder implementations that may need to be replaced with actual
    production code.
    
    The detector analyzes:
    - Function and method names for stub/mock/fake patterns
    - Function bodies for minimal or placeholder implementations
    - Comments indicating temporary implementations
    - Decorators suggesting testing or stubbing
    - Return patterns that suggest hardcoded or fake data
    """
    
    id = "stub_implementation"
    name = "Stub Implementation Detector"
    description = "Identifies stub, mock, fake, simulated, and fallback implementations"
    
    # Enhanced metadata for MCP server
    category = "Code Quality & Maintainability"
    usage_tips = "Use before production releases to identify temporary implementations that need completion"
    related_detectors = ["dead_code", "deprecated_api"]
    typical_severity = "warn"
    detailed_description = ("Locates temporary, mock, stub, or fallback implementations that may need to be "
                           "replaced with actual production code. Helps ensure code completeness before deployment.")
    
    def __init__(
        self,
        check_naming_patterns: bool = True,
        check_minimal_implementations: bool = True,
        check_not_implemented: bool = True,
        check_todo_comments: bool = True,
        check_hardcoded_returns: bool = True,
        stub_keywords: Optional[List[str]] = None,
        **options
    ):
        """
        Initialize the stub implementation detector.
        
        Args:
            check_naming_patterns: Check for stub-like names
            check_minimal_implementations: Check for minimal function bodies
            check_not_implemented: Check for NotImplementedError raises
            check_todo_comments: Check for TODO/FIXME comments
            check_hardcoded_returns: Check for hardcoded return values
            stub_keywords: Custom keywords to look for in names
            **options: Additional options passed to BaseDetector
        """
        super().__init__(**options)
        self.check_naming_patterns = check_naming_patterns
        self.check_minimal_implementations = check_minimal_implementations
        self.check_not_implemented = check_not_implemented
        self.check_todo_comments = check_todo_comments
        self.check_hardcoded_returns = check_hardcoded_returns
        
        # Default stub-related keywords
        self.stub_keywords = stub_keywords or [
            'stub', 'mock', 'fake', 'dummy', 'simulate', 'simulation',
            'fallback', 'placeholder', 'temp', 'temporary', 'test_double',
            'noop', 'no_op', 'sample', 'example', 'demo'
        ]
        
        # Testing-related decorators that often indicate stubs/mocks
        self.testing_decorators = {
            'mock', 'patch', 'stub', 'fake', 'pytest.fixture',
            'unittest.mock', 'Mock', 'MagicMock'
        }
    
    def _analyze(self, graph: CodeGraph) -> List[Issue]:
        """Analyze the code graph for stub implementations."""
        issues = []
        
        # Get all functions and methods
        functions = [s for s in graph.symbols.values() 
                    if isinstance(s.ast_node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        
        # Get all classes for additional context
        classes = [s for s in graph.symbols.values() 
                  if isinstance(s.ast_node, ast.ClassDef)]
        
        for func in functions:
            issues.extend(self._analyze_function(func, graph))
        
        for cls in classes:
            issues.extend(self._analyze_class(cls, graph))
        
        return issues
    
    def _analyze_function(self, func: Symbol, graph: CodeGraph) -> List[Issue]:
        """Analyze a single function for stub patterns."""
        issues = []
        func_node = func.ast_node
        
        if self.check_naming_patterns:
            issues.extend(self._check_naming_patterns(func))
        
        if self.check_minimal_implementations:
            issues.extend(self._check_minimal_implementation(func))
        
        if self.check_not_implemented:
            issues.extend(self._check_not_implemented_error(func))
        
        if self.check_todo_comments:
            issues.extend(self._check_todo_comments(func, graph))
        
        if self.check_hardcoded_returns:
            issues.extend(self._check_hardcoded_returns(func))
        
        # Check for testing decorators
        issues.extend(self._check_testing_decorators(func))
        
        return issues
    
    def _analyze_class(self, cls: Symbol, graph: CodeGraph) -> List[Issue]:
        """Analyze a class for stub patterns."""
        issues = []
        
        if self.check_naming_patterns:
            issues.extend(self._check_class_naming_patterns(cls))
        
        return issues
    
    def _check_naming_patterns(self, func: Symbol) -> List[Issue]:
        """Check if function name suggests it's a stub/mock/fake."""
        issues = []
        func_name = func.name.lower()
        
        for keyword in self.stub_keywords:
            if keyword in func_name:
                issues.append(
                    self.create_issue(
                        issue_id="stub_naming",
                        message=f"Function name '{func.name}' suggests stub/mock implementation (contains '{keyword}')",
                        severity="warn",
                        symbol=func,
                        metadata={
                            "stub_keyword": keyword,
                            "function_name": func.name,
                            "suggestion": f"Consider implementing actual logic or renaming if this is intentional"
                        }
                    )
                )
                break  # Only report once per function
        
        return issues
    
    def _check_class_naming_patterns(self, cls: Symbol) -> List[Issue]:
        """Check if class name suggests it's a stub/mock/fake."""
        issues = []
        cls_name = cls.name.lower()
        
        for keyword in self.stub_keywords:
            if keyword in cls_name:
                issues.append(
                    self.create_issue(
                        issue_id="stub_class_naming",
                        message=f"Class name '{cls.name}' suggests stub/mock implementation (contains '{keyword}')",
                        severity="warn",
                        symbol=cls,
                        metadata={
                            "stub_keyword": keyword,
                            "class_name": cls.name,
                            "suggestion": "Consider implementing actual logic or renaming if this is intentional"
                        }
                    )
                )
                break  # Only report once per class
        
        return issues
    
    def _check_minimal_implementation(self, func: Symbol) -> List[Issue]:
        """Check for minimal implementations (pass, return None, etc.)."""
        issues = []
        func_node = func.ast_node
        
        # Skip if function has no body
        if not hasattr(func_node, 'body') or not func_node.body:
            return issues
        
        # Check for single-statement bodies that suggest stubs
        if len(func_node.body) == 1:
            stmt = func_node.body[0]
            
            # Check for 'pass' statement
            if isinstance(stmt, ast.Pass):
                issues.append(
                    self.create_issue(
                        issue_id="minimal_pass_implementation",
                        message=f"Function '{func.name}' has minimal implementation (only 'pass')",
                        severity="info",
                        symbol=func,
                        metadata={
                            "implementation_type": "pass",
                            "suggestion": "Consider implementing actual logic"
                        }
                    )
                )
            
            # Check for 'return None' or bare 'return'
            elif isinstance(stmt, ast.Return):
                if stmt.value is None or (isinstance(stmt.value, ast.Constant) and stmt.value.value is None):
                    issues.append(
                        self.create_issue(
                            issue_id="minimal_return_none",
                            message=f"Function '{func.name}' has minimal implementation (only returns None)",
                            severity="info",
                            symbol=func,
                            metadata={
                                "implementation_type": "return_none",
                                "suggestion": "Consider implementing actual return logic"
                            }
                        )
                    )
        
        return issues
    
    def _check_not_implemented_error(self, func: Symbol) -> List[Issue]:
        """Check for NotImplementedError raises."""
        issues = []
        
        class NotImplementedVisitor(ast.NodeVisitor):
            def __init__(self):
                self.found_not_implemented = False
                self.error_message = None
            
            def visit_Raise(self, node):
                if isinstance(node.exc, ast.Call):
                    if isinstance(node.exc.func, ast.Name) and node.exc.func.id == 'NotImplementedError':
                        self.found_not_implemented = True
                        # Try to extract error message
                        if node.exc.args:
                            if isinstance(node.exc.args[0], ast.Constant):
                                self.error_message = node.exc.args[0].value
                elif isinstance(node.exc, ast.Name) and node.exc.id == 'NotImplementedError':
                    self.found_not_implemented = True
                
                self.generic_visit(node)
        
        visitor = NotImplementedVisitor()
        visitor.visit(func.ast_node)
        
        if visitor.found_not_implemented:
            message = f"Function '{func.name}' raises NotImplementedError"
            if visitor.error_message:
                message += f": {visitor.error_message}"
            
            issues.append(
                self.create_issue(
                    issue_id="not_implemented_error",
                    message=message,
                    severity="warn",
                    symbol=func,
                    metadata={
                        "error_message": visitor.error_message,
                        "suggestion": "Implement the actual functionality"
                    }
                )
            )
        
        return issues
    
    def _check_todo_comments(self, func: Symbol, graph: CodeGraph) -> List[Issue]:
        """Check for TODO/FIXME comments in function."""
        issues = []
        
        # Get source code for the function
        try:
            source_path = func.location.file
            if source_path.exists():
                # Use centralized reading with encoding fallback
                try:
                    with open(source_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    with open(source_path, 'r', encoding='latin-1') as f:
                        lines = f.readlines()
                
                # Check lines around the function
                start_line = max(0, func.location.line - 1)
                end_line = min(len(lines), (func.location.end_line or func.location.line) + 5)
                
                todo_patterns = [
                    r'#\s*TODO:?\s*(.+)',
                    r'#\s*FIXME:?\s*(.+)',
                    r'#\s*HACK:?\s*(.+)',
                    r'#\s*TEMP:?\s*(.+)',
                    r'#\s*PLACEHOLDER:?\s*(.+)'
                ]
                
                for line_idx in range(start_line, end_line):
                    if line_idx < len(lines):
                        line = lines[line_idx]
                        for pattern in todo_patterns:
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                comment_type = pattern.split(':')[0].split('\\s*')[1]
                                comment_text = match.group(1).strip()
                                
                                issues.append(
                                    self.create_issue(
                                        issue_id="todo_comment",
                                        message=f"Function '{func.name}' has {comment_type} comment indicating incomplete implementation: {comment_text}",
                                        severity="info",
                                        symbol=func,
                                        metadata={
                                            "comment_type": comment_type,
                                            "comment_text": comment_text,
                                            "line_number": line_idx + 1,
                                            "suggestion": "Complete the implementation or remove the comment"
                                        }
                                    )
                                )
                                break  # Only one TODO per line
        except (IOError, UnicodeDecodeError):
            pass  # Skip if we can't read the file
        
        return issues
    
    def _check_hardcoded_returns(self, func: Symbol) -> List[Issue]:
        """Check for hardcoded return values that suggest fake implementations."""
        issues = []
        
        class HardcodedReturnVisitor(ast.NodeVisitor):
            def __init__(self):
                self.hardcoded_returns = []
            
            def visit_Return(self, node):
                if node.value:
                    # Check for simple hardcoded values
                    if isinstance(node.value, ast.Constant):
                        value = node.value.value
                        if isinstance(value, (str, int, float, bool)) and value != 0:
                            self.hardcoded_returns.append(("constant", str(value)))
                    
                    # Check for empty containers
                    elif isinstance(node.value, (ast.List, ast.Dict, ast.Set, ast.Tuple)):
                        if isinstance(node.value, ast.List) and not node.value.elts:
                            self.hardcoded_returns.append(("empty_list", "[]"))
                        elif isinstance(node.value, ast.Dict) and not node.value.keys:
                            self.hardcoded_returns.append(("empty_dict", "{}"))
                        elif isinstance(node.value, ast.Set) and not node.value.elts:
                            self.hardcoded_returns.append(("empty_set", "set()"))
                        elif isinstance(node.value, ast.Tuple) and not node.value.elts:
                            self.hardcoded_returns.append(("empty_tuple", "()"))
                
                self.generic_visit(node)
        
        visitor = HardcodedReturnVisitor()
        visitor.visit(func.ast_node)
        
        # Only report if function has minimal logic but returns hardcoded values
        if visitor.hardcoded_returns and len(func.ast_node.body) <= 2:
            for return_type, value in visitor.hardcoded_returns:
                issues.append(
                    self.create_issue(
                        issue_id="hardcoded_return",
                        message=f"Function '{func.name}' returns hardcoded value: {value}",
                        severity="info",
                        symbol=func,
                        metadata={
                            "return_type": return_type,
                            "return_value": value,
                            "suggestion": "Consider implementing dynamic logic or using configuration"
                        }
                    )
                )
        
        return issues
    
    def _check_testing_decorators(self, func: Symbol) -> List[Issue]:
        """Check for testing-related decorators that suggest stub implementations."""
        issues = []
        func_node = func.ast_node
        
        if not hasattr(func_node, 'decorator_list'):
            return issues
        
        for decorator in func_node.decorator_list:
            decorator_name = ""
            
            # Handle simple decorator names
            if isinstance(decorator, ast.Name):
                decorator_name = decorator.id
            # Handle attribute decorators (e.g., @pytest.fixture)
            elif isinstance(decorator, ast.Attribute):
                if isinstance(decorator.value, ast.Name):
                    decorator_name = f"{decorator.value.id}.{decorator.attr}"
            # Handle decorator calls (e.g., @mock.patch('module'))
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorator_name = decorator.func.id
                elif isinstance(decorator.func, ast.Attribute):
                    if isinstance(decorator.func.value, ast.Name):
                        decorator_name = f"{decorator.func.value.id}.{decorator.func.attr}"
            
            # Check if decorator suggests testing/mocking
            for test_decorator in self.testing_decorators:
                if test_decorator in decorator_name.lower():
                    issues.append(
                        self.create_issue(
                            issue_id="testing_decorator",
                            message=f"Function '{func.name}' has testing-related decorator: @{decorator_name}",
                            severity="info",
                            symbol=func,
                            metadata={
                                "decorator_name": decorator_name,
                                "suggestion": "Verify if this is test code or if production implementation is needed"
                            }
                        )
                    )
                    break
        
        return issues
