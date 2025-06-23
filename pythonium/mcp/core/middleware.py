"""
Middleware system for Pythonium MCP server.

Provides middleware infrastructure for cross-cutting concerns like
logging, profiling, validation, and error handling.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List

try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from ..utils.debug import info_log, warning_log, error_log
from ..utils import Validator, ErrorHandler, PerformanceMonitor, ErrorContext, ErrorSeverity


class Middleware(ABC):
    """
    Abstract base class for middleware components.
    
    Middleware can intercept and modify tool calls before and after execution
    to implement cross-cutting concerns like logging, validation, caching, etc.
    """
    
    @abstractmethod
    async def process(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        next_handler: Callable[[str, Dict[str, Any]], Awaitable[List[types.TextContent]]]
    ) -> List[types.TextContent]:
        """
        Process a tool call through this middleware.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Arguments for the tool
            next_handler: Next handler in the chain (either next middleware or final tool)
            
        Returns:
            Tool execution results
        """
        pass


class LoggingMiddleware(Middleware):
    """Middleware for logging tool calls and their results."""
    
    async def process(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        next_handler: Callable[[str, Dict[str, Any]], Awaitable[List[types.TextContent]]]
    ) -> List[types.TextContent]:
        """Log tool call and execution."""
        info_log(f"[Middleware] Starting tool '{tool_name}'")
        
        try:
            result = await next_handler(tool_name, arguments)
            info_log(f"[Middleware] Tool '{tool_name}' completed successfully")
            return result
        except Exception as e:
            error_log(f"[Middleware] Tool '{tool_name}' failed: {str(e)}")
            raise


class ValidationMiddleware(Middleware):
    """Middleware for validating tool arguments using comprehensive validation."""
    
    def __init__(self):
        """Initialize validation middleware."""
        self.validator = Validator()
    
    async def process(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        next_handler: Callable[[str, Dict[str, Any]], Awaitable[List[types.TextContent]]]
    ) -> List[types.TextContent]:
        """Validate arguments using comprehensive validation."""
        try:
            # Use validator to validate arguments
            self.validator.validate_tool_arguments(tool_name, arguments)
            info_log(f"[Validation] Arguments for '{tool_name}' validated successfully")
        except Exception as e:
            error_log(f"[Validation] Validation failed for '{tool_name}': {str(e)}")
            return [types.TextContent(
                type="text",
                text=f"Validation error for tool '{tool_name}': {str(e)}"
            )]
        
        return await next_handler(tool_name, arguments)


class ErrorHandlingMiddleware(Middleware):
    """Middleware for consistent error handling and formatting with context."""
    
    def __init__(self):
        """Initialize error handling middleware."""
        self.error_handler = ErrorHandler()
    
    async def process(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        next_handler: Callable[[str, Dict[str, Any]], Awaitable[List[types.TextContent]]]
    ) -> List[types.TextContent]:
        """Provide comprehensive error handling with context and classification."""
        try:
            return await next_handler(tool_name, arguments)
        except Exception as e:
            # Create error context
            context = ErrorContext(
                tool_name=tool_name,
                arguments=arguments,
                original_error=e,
                user_friendly_message=f"Error executing tool '{tool_name}'"
            )
            
            # Handle error through error handler
            error_response = self.error_handler.handle_error(e, context)
            
            # Log based on severity
            if error_response.severity == ErrorSeverity.HIGH:
                error_log(f"[ErrorHandling] HIGH severity: {error_response.user_message}")
            elif error_response.severity == ErrorSeverity.MEDIUM:
                warning_log(f"[ErrorHandling] MEDIUM severity: {error_response.user_message}")
            else:
                info_log(f"[ErrorHandling] LOW severity: {error_response.user_message}")
            
            return [types.TextContent(type="text", text=error_response.user_message)]


class PerformanceMiddleware(Middleware):
    """Middleware for monitoring tool performance and collecting metrics."""
    
    def __init__(self):
        """Initialize performance monitoring middleware."""
        self.monitor = PerformanceMonitor()
    
    async def process(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        next_handler: Callable[[str, Dict[str, Any]], Awaitable[List[types.TextContent]]]
    ) -> List[types.TextContent]:
        """Monitor performance of tool execution."""
        # Start timing
        import time
        start_time = time.time()
        
        try:
            result = await next_handler(tool_name, arguments)
            
            # Record timing
            execution_time = time.time() - start_time
            info_log(f"Tool {tool_name} executed in {execution_time:.3f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            error_log(f"Tool {tool_name} failed after {execution_time:.3f}s: {e}")
            raise


class MiddlewareChain:
    """
    Chain of middleware components for processing tool calls.
    
    Implements the chain of responsibility pattern for middleware processing,
    allowing multiple middleware components to process tool calls in sequence.
    """
    
    def __init__(self):
        """Initialize an empty middleware chain."""
        self._middleware: List[Middleware] = []
    
    def add(self, middleware: Middleware) -> 'MiddlewareChain':
        """
        Add middleware to the chain.
        
        Args:
            middleware: Middleware component to add
            
        Returns:
            Self for method chaining
        """
        self._middleware.append(middleware)
        info_log(f"Added middleware: {middleware.__class__.__name__}")
        return self
    
    def remove(self, middleware_class: type) -> bool:
        """
        Remove middleware of a specific type from the chain.
        
        Args:
            middleware_class: Class of middleware to remove
            
        Returns:
            True if middleware was removed, False if not found
        """
        for i, middleware in enumerate(self._middleware):
            if isinstance(middleware, middleware_class):
                removed = self._middleware.pop(i)
                info_log(f"Removed middleware: {removed.__class__.__name__}")
                return True
        return False
    
    def clear(self) -> None:
        """Clear all middleware from the chain."""
        self._middleware.clear()
        info_log("Middleware chain cleared")
    
    async def process(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        final_handler: Callable[[str, Dict[str, Any]], Awaitable[List[types.TextContent]]]
    ) -> List[types.TextContent]:
        """
        Process a tool call through the middleware chain.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Arguments for the tool
            final_handler: Final handler to execute the tool
            
        Returns:
            Tool execution results
        """
        if not self._middleware:
            # No middleware, call final handler directly
            return await final_handler(tool_name, arguments)
        
        # Create the chain by building from the final handler
        current_handler = final_handler
        
        for middleware in reversed(self._middleware):
            # Capture the current handler in a closure
            def create_handler(mw: Middleware, next_h: Callable):
                async def handler(name: str, args: Dict[str, Any]) -> List[types.TextContent]:
                    return await mw.process(name, args, next_h)
                return handler
            
            current_handler = create_handler(middleware, current_handler)
        
        # Execute the chain
        return await current_handler(tool_name, arguments)
    
    def get_middleware_info(self) -> List[Dict[str, Any]]:
        """
        Get information about the middleware in the chain.
        
        Returns:
            List of middleware information dictionaries
        """
        return [
            {
                "class": middleware.__class__.__name__,
                "module": middleware.__class__.__module__,
                "index": i
            }
            for i, middleware in enumerate(self._middleware)
        ]
