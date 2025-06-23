"""
Error handling for Pythonium MCP server.

Provides comprehensive error handling with context tracking,
severity classification, and detailed error reporting.
"""

import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Type, Callable

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from .debug import error_log, warning_log, info_log


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    FILE_SYSTEM = "file_system"
    CONFIGURATION = "configuration"
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    NETWORK = "network"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    INTERNAL = "internal"
    USER_INPUT = "user_input"


class ErrorContext:
    """
    Context information for error handling.
    """
    
    def __init__(
        self,
        tool_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
        user_friendly_message: Optional[str] = None
    ):
        """
        Initialize error context.
        
        Args:
            tool_name: Name of the tool being executed
            arguments: Tool arguments
            user_context: Additional user context
            operation: Specific operation being performed
            original_error: The original exception that occurred
            user_friendly_message: User-friendly error message
        """
        self.tool_name = tool_name
        self.arguments = arguments or {}
        self.user_context = user_context or {}
        self.operation = operation
        self.original_error = original_error
        self.user_friendly_message = user_friendly_message
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "user_context": self.user_context,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat()
        }


class ErrorInfo:
    """
    Detailed error information with classification and context.
    """
    
    def __init__(
        self,
        exception: Exception,
        severity: ErrorSeverity,
        category: ErrorCategory,
        context: Optional[ErrorContext] = None,
        user_message: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        recovery_actions: Optional[List[str]] = None
    ):
        """
        Initialize error information.
        
        Args:
            exception: Original exception
            severity: Error severity level
            category: Error category
            context: Error context
            user_message: User-friendly error message
            suggestions: Suggestions for fixing the error
            recovery_actions: Possible recovery actions
        """
        self.exception = exception
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext()
        self.user_message = user_message or str(exception)
        self.suggestions = suggestions or []
        self.recovery_actions = recovery_actions or []
        self.technical_message = str(exception)
        self.exception_type = type(exception).__name__
        self.traceback = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error info to dictionary."""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "exception_type": self.exception_type,
            "user_message": self.user_message,
            "technical_message": self.technical_message,
            "suggestions": self.suggestions,
            "recovery_actions": self.recovery_actions,
            "context": self.context.to_dict(),
            "traceback": self.traceback
        }


class ErrorHandler:
    """
    Comprehensive error handler with intelligent error classification and response generation.
    """
    
    def __init__(self):
        """Initialize error handler."""
        self._error_classifiers = self._create_error_classifiers()
        self._response_generators = self._create_response_generators()
    
    def _create_error_classifiers(self) -> Dict[Type[Exception], Callable[[Exception, ErrorContext], ErrorInfo]]:
        """Create error classifiers for different exception types."""
        return {
            ValueError: self._classify_value_error,
            TypeError: self._classify_type_error,
            FileNotFoundError: self._classify_file_not_found_error,
            PermissionError: self._classify_permission_error,
            TimeoutError: self._classify_timeout_error,
            ImportError: self._classify_import_error,
            AttributeError: self._classify_attribute_error,
            KeyError: self._classify_key_error,
            RuntimeError: self._classify_runtime_error,
            Exception: self._classify_generic_error  # Fallback
        }
    
    def _create_response_generators(self) -> Dict[ErrorCategory, Callable[[ErrorInfo], List[types.TextContent]]]:
        """Create response generators for different error categories."""
        return {
            ErrorCategory.VALIDATION: self._generate_validation_response,
            ErrorCategory.FILE_SYSTEM: self._generate_file_system_response,
            ErrorCategory.CONFIGURATION: self._generate_configuration_response,
            ErrorCategory.ANALYSIS: self._generate_analysis_response,
            ErrorCategory.EXECUTION: self._generate_execution_response,
            ErrorCategory.PERMISSION: self._generate_permission_response,
            ErrorCategory.TIMEOUT: self._generate_timeout_response,
            ErrorCategory.USER_INPUT: self._generate_user_input_response,
            ErrorCategory.INTERNAL: self._generate_internal_response
        }
    
    def handle_error(
        self, 
        exception: Exception, 
        context: Optional[ErrorContext] = None
    ) -> List[types.TextContent]:
        """
        Handle an error and generate appropriate response.
        
        Args:
            exception: Exception to handle
            context: Error context
            
        Returns:
            List of text content for MCP response
        """
        if not MCP_AVAILABLE:
            # Fallback if MCP types not available
            return [{"type": "text", "text": f"Error: {str(exception)}"}]
        
        # Classify the error
        error_info = self._classify_error(exception, context)
        
        # Log the error appropriately
        self._log_error(error_info)
        
        # Generate response
        response = self._generate_response(error_info)
        
        return response
    
    def _classify_error(self, exception: Exception, context: Optional[ErrorContext]) -> ErrorInfo:
        """Classify an error and return detailed error information."""
        if context is None:
            context = ErrorContext()
        
        # Find the appropriate classifier
        for exception_type, classifier in self._error_classifiers.items():
            if isinstance(exception, exception_type):
                return classifier(exception, context)
        
        # Fallback to generic classification
        return self._classify_generic_error(exception, context)
    
    def _classify_value_error(self, exception: ValueError, context: ErrorContext) -> ErrorInfo:
        """Classify ValueError exceptions."""
        message = str(exception).lower()
        
        if "required" in message or "missing" in message:
            return ErrorInfo(
                exception=exception,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.VALIDATION,
                context=context,
                user_message=f"Missing required parameter: {str(exception)}",
                suggestions=[
                    "Check that all required parameters are provided",
                    "Verify parameter names are spelled correctly",
                    "Ensure parameter values are not empty"
                ]
            )
        elif "path" in message or "file" in message:
            return ErrorInfo(
                exception=exception,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.FILE_SYSTEM,
                context=context,
                user_message=f"File or path error: {str(exception)}",
                suggestions=[
                    "Check that the file or directory exists",
                    "Verify the path is correct and accessible",
                    "Ensure you have read permissions"
                ]
            )
        else:
            return ErrorInfo(
                exception=exception,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.USER_INPUT,
                context=context,
                user_message=f"Invalid input: {str(exception)}",
                suggestions=[
                    "Check the format of your input parameters",
                    "Refer to the tool documentation for expected values"
                ]
            )
    
    def _classify_type_error(self, exception: TypeError, context: ErrorContext) -> ErrorInfo:
        """Classify TypeError exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            context=context,
            user_message=f"Type mismatch: {str(exception)}",
            suggestions=[
                "Check that parameter types match expected types",
                "Convert values to the correct type if needed",
                "Refer to tool documentation for parameter types"
            ]
        )
    
    def _classify_file_not_found_error(self, exception: FileNotFoundError, context: ErrorContext) -> ErrorInfo:
        """Classify FileNotFoundError exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.FILE_SYSTEM,
            context=context,
            user_message=f"File not found: {str(exception)}",
            suggestions=[
                "Verify the file path is correct",
                "Check that the file exists at the specified location",
                "Ensure the file hasn't been moved or deleted"
            ],
            recovery_actions=[
                "Create the missing file",
                "Update the path to point to the correct location",
                "Use a different file that exists"
            ]
        )
    
    def _classify_permission_error(self, exception: PermissionError, context: ErrorContext) -> ErrorInfo:
        """Classify PermissionError exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.PERMISSION,
            context=context,
            user_message=f"Permission denied: {str(exception)}",
            suggestions=[
                "Check file and directory permissions",
                "Run with appropriate user privileges",
                "Ensure the file is not locked by another process"
            ],
            recovery_actions=[
                "Change file permissions",
                "Run as administrator/root",
                "Close other applications using the file"
            ]
        )
    
    def _classify_timeout_error(self, exception: TimeoutError, context: ErrorContext) -> ErrorInfo:
        """Classify TimeoutError exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.TIMEOUT,
            context=context,
            user_message=f"Operation timed out: {str(exception)}",
            suggestions=[
                "Try with a smaller dataset or specific files",
                "Increase timeout if possible",
                "Check system performance and available resources"
            ],
            recovery_actions=[
                "Retry with smaller scope",
                "Use more specific analysis parameters",
                "Break large operations into smaller parts"
            ]
        )
    
    def _classify_import_error(self, exception: ImportError, context: ErrorContext) -> ErrorInfo:
        """Classify ImportError exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIGURATION,
            context=context,
            user_message=f"Missing dependency: {str(exception)}",
            suggestions=[
                "Install missing Python packages",
                "Check virtual environment activation",
                "Verify package versions are compatible"
            ],
            recovery_actions=[
                "Run 'pip install' for missing packages",
                "Check requirements.txt",
                "Update package versions"
            ]
        )
    
    def _classify_attribute_error(self, exception: AttributeError, context: ErrorContext) -> ErrorInfo:
        """Classify AttributeError exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.INTERNAL,
            context=context,
            user_message=f"Internal error: {str(exception)}",
            suggestions=[
                "This appears to be an internal error",
                "Try with different parameters",
                "Report this issue if it persists"
            ]
        )
    
    def _classify_key_error(self, exception: KeyError, context: ErrorContext) -> ErrorInfo:
        """Classify KeyError exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.CONFIGURATION,
            context=context,
            user_message=f"Missing configuration key: {str(exception)}",
            suggestions=[
                "Check configuration file completeness",
                "Verify all required settings are present",
                "Use default configuration if available"
            ]
        )
    
    def _classify_runtime_error(self, exception: RuntimeError, context: ErrorContext) -> ErrorInfo:
        """Classify RuntimeError exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXECUTION,
            context=context,
            user_message=f"Execution error: {str(exception)}",
            suggestions=[
                "Check input parameters and data",
                "Verify system resources are available",
                "Try with simpler or different inputs"
            ]
        )
    
    def _classify_generic_error(self, exception: Exception, context: ErrorContext) -> ErrorInfo:
        """Classify generic exceptions."""
        return ErrorInfo(
            exception=exception,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.INTERNAL,
            context=context,
            user_message=f"Unexpected error: {str(exception)}",
            suggestions=[
                "This is an unexpected error",
                "Please report this issue with context",
                "Try again with different parameters"
            ]
        )
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error based on severity."""
        log_message = f"[{error_info.category.value}] {error_info.user_message}"
        
        if error_info.context.tool_name:
            log_message = f"Tool '{error_info.context.tool_name}': {log_message}"
        
        if error_info.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            error_log(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            warning_log(log_message)
        else:
            info_log(log_message)
    
    def _generate_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate appropriate response for the error."""
        generator = self._response_generators.get(
            error_info.category, 
            self._generate_generic_response
        )
        return generator(error_info)
    
    def _generate_validation_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for validation errors."""
        content_lines = [
            f"**Validation Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        if error_info.context.tool_name:
            content_lines.extend([
                f"",
                f"**Tool:** `{error_info.context.tool_name}`"
            ])
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_file_system_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for file system errors."""
        content_lines = [
            f"**File System Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        if error_info.recovery_actions:
            content_lines.extend([f"", f"**Recovery Actions:"])
            for action in error_info.recovery_actions:
                content_lines.append(f"• {action}")
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_configuration_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for configuration errors."""
        content_lines = [
            f"**Configuration Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        if error_info.recovery_actions:
            content_lines.extend([f"", f"**Recovery Actions:**"])
            for action in error_info.recovery_actions:
                content_lines.append(f"• {action}")
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_analysis_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for analysis errors."""
        content_lines = [
            f"**Analysis Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_execution_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for execution errors."""
        content_lines = [
            f"**Execution Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_permission_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for permission errors."""
        content_lines = [
            f"**Permission Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        if error_info.recovery_actions:
            content_lines.extend([f"", f"**Recovery Actions:**"])
            for action in error_info.recovery_actions:
                content_lines.append(f"• {action}")
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_timeout_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for timeout errors."""
        content_lines = [
            f"⏱️ **Timeout Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        if error_info.recovery_actions:
            content_lines.extend([f"", f"**Recovery Actions:**"])
            for action in error_info.recovery_actions:
                content_lines.append(f"• {action}")
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_user_input_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for user input errors."""
        content_lines = [
            f"**Input Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_internal_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate response for internal errors."""
        content_lines = [
            f"**Internal Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        content_lines.extend([
            f"",
            f"**Debug Information:**",
            f"• Error Type: `{error_info.exception_type}`",
            f"• Severity: `{error_info.severity.value}`",
            f"• Category: `{error_info.category.value}`"
        ])
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
    
    def _generate_generic_response(self, error_info: ErrorInfo) -> List[types.TextContent]:
        """Generate generic response for unknown error categories."""
        content_lines = [
            f"**Unexpected Error**",
            f"",
            f"**Issue:** {error_info.user_message}",
            f"",
            f"**Suggestions:**"
        ]
        
        for suggestion in error_info.suggestions:
            content_lines.append(f"• {suggestion}")
        
        return [types.TextContent(type="text", text="\n".join(content_lines))]
