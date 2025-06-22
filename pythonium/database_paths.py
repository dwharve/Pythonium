"""
Centralized database path resolution for Pythonium MCP server.

This module provides consistent database path determination across all components
to eliminate the inconsistencies where different parts of the system would create
separate databases for the same logical project.
"""

from pathlib import Path
from typing import Optional

from .cli import find_project_root


class DatabasePathResolver:
    """Centralized database path resolution for consistency across components."""
    
    @staticmethod
    def resolve_project_root(context_path: Optional[Path] = None, fallback_to_cwd: bool = True) -> Path:
        """
        Resolve project root using consistent logic across all components.
        
        Args:
            context_path: Path to use as context for finding project root (file or directory)
            fallback_to_cwd: Whether to fallback to current working directory if no project root found
            
        Returns:
            Path to the project root directory
            
        Raises:
            ValueError: If no project root can be determined and fallback_to_cwd is False
        """
        if context_path is None:
            context_path = Path.cwd()
        
        try:
            return find_project_root(context_path)
        except Exception as e:
            if fallback_to_cwd:
                return Path.cwd()
            raise ValueError(f"Could not determine project root from {context_path}: {e}")
    
    @staticmethod
    def get_issues_db_path(project_root: Optional[Path] = None) -> Path:
        """
        Get standardized issues database path.
        
        Args:
            project_root: Project root directory. If None, will be resolved from current context.
            
        Returns:
            Path to the issues database file
        """
        if project_root is None:
            project_root = DatabasePathResolver.resolve_project_root()
        
        db_path = project_root / ".pythonium" / "issues.db"
        # Ensure the directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path
    
    @staticmethod 
    def get_cache_db_path(project_root: Optional[Path] = None) -> Path:
        """
        Get standardized cache database path.
        
        Args:
            project_root: Project root directory. If None, will be resolved from current context.
            
        Returns:
            Path to the cache database file
        """
        if project_root is None:
            project_root = DatabasePathResolver.resolve_project_root()
        
        db_path = project_root / ".pythonium" / "cache.db"
        # Ensure the directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path
    
    @staticmethod
    def get_pythonium_dir(project_root: Optional[Path] = None) -> Path:
        """
        Get the .pythonium directory for a project.
        
        Args:
            project_root: Project root directory. If None, will be resolved from current context.
            
        Returns:
            Path to the .pythonium directory
        """
        if project_root is None:
            project_root = DatabasePathResolver.resolve_project_root()
        
        pythonium_dir = project_root / ".pythonium"
        pythonium_dir.mkdir(parents=True, exist_ok=True)
        return pythonium_dir
    
    @staticmethod
    def clean_legacy_databases(project_root: Optional[Path] = None) -> None:
        """
        Clean up any legacy/fragmented database files.
        
        This is a utility function to help with migration from the old inconsistent
        database path system to the new centralized one.
        
        Args:
            project_root: Project root directory. If None, will be resolved from current context.
        """
        import tempfile
        import shutil
        
        if project_root is None:
            project_root = DatabasePathResolver.resolve_project_root()
        
        # Clean up temp directories that might have .pythonium folders
        temp_dir = Path(tempfile.gettempdir())
        for temp_subdir in temp_dir.glob("pythonium_*"):
            if temp_subdir.is_dir():
                pythonium_temp = temp_subdir / ".pythonium"
                if pythonium_temp.exists():
                    try:
                        shutil.rmtree(pythonium_temp)
                    except Exception:
                        pass  # Ignore cleanup errors
        
        # Clean up user home directory .pythonium if it exists and isn't the project root
        home_pythonium = Path.home() / ".pythonium"
        if home_pythonium.exists() and home_pythonium.parent != project_root:
            try:
                shutil.rmtree(home_pythonium)
            except Exception:
                pass  # Ignore cleanup errors
