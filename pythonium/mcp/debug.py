"""
Enhanced debug logging functions for MCP server operations.
"""

import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

# Set up logger for debug operations
logger = logging.getLogger("pythonium.mcp")

class OperationProfiler:
    """Profiles MCP operations with detailed timing and checkpoints."""
    
    def __init__(self):
        self.operations = []
        self.current_operation = None
    
    def start_operation(self, name: str, **kwargs) -> None:
        """Start profiling an operation."""
        operation = {
            "name": name,
            "start_time": time.time(),
            "status": "running",
            "checkpoints": [],
            "metadata": kwargs
        }
        self.operations.append(operation)
        self.current_operation = operation
        logger.info(f"🚀 Starting operation: {name} - {kwargs}")
    
    def checkpoint(self, checkpoint_name: str, **kwargs) -> None:
        """Add a checkpoint to the current operation."""
        if not self.current_operation:
            return
        
        checkpoint = {
            "name": checkpoint_name,
            "time": time.time(),
            "elapsed": time.time() - self.current_operation["start_time"],
            "metadata": kwargs
        }
        self.current_operation["checkpoints"].append(checkpoint)
        
        elapsed_str = f"{checkpoint['elapsed']:.2f}s"
        logger.info(f"📍 Checkpoint: {checkpoint_name} at {elapsed_str} - {kwargs}")
    
    def end_operation(self, success: bool = True, **kwargs) -> None:
        """End the current operation."""
        if not self.current_operation:
            return
        
        self.current_operation["end_time"] = time.time()
        self.current_operation["duration"] = (
            self.current_operation["end_time"] - self.current_operation["start_time"]
        )
        self.current_operation["status"] = "success" if success else "failed"
        self.current_operation["result_metadata"] = kwargs
        
        status_icon = "✅" if success else "❌"
        duration_str = f"{self.current_operation['duration']:.2f}s"
        logger.info(f"{status_icon} Completed operation: {self.current_operation['name']} in {duration_str} - Status: {self.current_operation['status']}")
        
        self.current_operation = None
    
    def get_report(self) -> str:
        """Generate a human-readable profiling report."""
        if not self.operations:
            return "No operations have been profiled yet."
        
        lines = ["MCP Server Profiling Report", "=" * 30, ""]
        
        for op in self.operations[-10:]:  # Show last 10 operations
            duration = op.get("duration", "N/A")
            duration_str = f"{duration:.2f}s" if isinstance(duration, (int, float)) else str(duration)
            
            lines.append(f"Operation: {op['name']}")
            lines.append(f"  Status: {op['status']}")
            lines.append(f"  Duration: {duration_str}")
            
            if op.get("checkpoints"):
                lines.append("  Checkpoints:")
                for checkpoint in op["checkpoints"]:
                    elapsed_str = f"{checkpoint['elapsed']:.2f}s"
                    meta_str = f" - {checkpoint['metadata']}" if checkpoint.get('metadata') else ""
                    lines.append(f"    {checkpoint['name']}: {elapsed_str}{meta_str}")
            
            lines.append("")
        
        return "\n".join(lines)

# Global profiler instance
profiler = OperationProfiler()

def profile_operation(name: str):
    """Decorator to automatically profile an operation."""
    def decorator(func):
        if hasattr(func, '__call__'):
            # For async functions
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
                async def async_wrapper(*args, **kwargs):
                    profiler.start_operation(name, args_count=len(args), kwargs=list(kwargs.keys()))
                    try:
                        result = await func(*args, **kwargs)
                        profiler.end_operation(success=True)
                        return result
                    except Exception as e:
                        profiler.end_operation(success=False, error=str(e))
                        raise
                return async_wrapper
            else:
                # For sync functions
                def sync_wrapper(*args, **kwargs):
                    profiler.start_operation(name, args_count=len(args), kwargs=list(kwargs.keys()))
                    try:
                        result = func(*args, **kwargs)
                        profiler.end_operation(success=True)
                        return result
                    except Exception as e:
                        profiler.end_operation(success=False, error=str(e))
                        raise
                return sync_wrapper
        return func
    return decorator

def setup_debug_logging() -> None:
    """Set up enhanced debug logging for the MCP server."""
    # Create debug log file in the project directory
    log_file = Path.cwd() / "pythonium_mcp_debug.log"
    
    # Configure the logger
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler for detailed logs
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler for important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Debug logging enabled - Log file: {log_file}")
    print(f"Debug logging enabled - Log file: {log_file}")

def log_file_discovery(path: Path, files: List[Path]) -> None:
    """Log file discovery details."""
    if path.is_dir():
        logger.info(f"📁 Discovered {len(files)} Python files in directory: {path}")
        if len(files) <= 10:
            for file in files:
                logger.debug(f"  📄 {file}")
        else:
            logger.info(f"  📄 First 5 files: {[str(f) for f in files[:5]]}")
            logger.info(f"  📄 ... and {len(files) - 5} more files")
    else:
        logger.info(f"📄 Analyzing single file: {path}")

def log_analyzer_creation(config: Dict[str, Any], use_cache: bool, use_parallel: bool) -> None:
    """Log analyzer creation details."""
    detector_count = len(config.get('detectors', {})) if config.get('detectors') else 'all'
    logger.info(f"🔧 Creating analyzer - Detectors: {detector_count}, Cache: {use_cache}, Parallel: {use_parallel}")
    
    if config.get('detectors'):
        enabled_detectors = [d for d, settings in config['detectors'].items() if settings.get('enabled', True)]
        logger.debug(f"🎯 Enabled detectors: {enabled_detectors}")

def log_analysis_start(files: List[Path]) -> None:
    """Log analysis start details."""
    logger.info(f"🚀 Starting analysis of {len(files)} file(s)")
    if len(files) > 50:
        logger.warning(f"⚠️  Large analysis scope: {len(files)} files. This may take several minutes.")
    elif len(files) > 20:
        logger.info(f"📊 Medium analysis scope: {len(files)} files. Expected duration: 30-60 seconds.")
    else:
        logger.info(f"⚡ Small analysis scope: {len(files)} files. Expected duration: <30 seconds.")
