"""
Incremental analysis support for the Pythonium Crawler.

This module provides Git integration for incremental analysis,
allowing the crawler to analyze only changed files for faster CI execution.
"""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GitChange:
    """Represents a change in Git."""
    file_path: Path
    status: str  # A (added), M (modified), D (deleted), R (renamed)
    old_path: Optional[Path] = None  # For renames


class GitAnalyzer:
    """
    Git integration for incremental analysis.
    
    Provides methods to detect changed files since a specific commit,
    branch, or time period for optimized CI analysis.
    """
    
    def __init__(self, repo_path: Path):
        """
        Initialize Git analyzer.
        
        Args:
            repo_path: Path to the Git repository root
        """
        self.repo_path = repo_path
        self._validate_git_repo()
    
    def _validate_git_repo(self):
        """Validate that the path is a Git repository."""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a Git repository: {self.repo_path}")
    
    def _run_git_command(self, args: List[str]) -> str:
        """
        Run a Git command and return output.
        
        Args:
            args: Git command arguments
            
        Returns:
            Command output
            
        Raises:
            subprocess.CalledProcessError: If Git command fails
        """
        cmd = ["git"] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error("Git command failed: %s", " ".join(cmd))
            logger.error("Error: %s", e.stderr)
            raise
    
    def get_changed_files_since_commit(self, base_commit: str) -> List[GitChange]:
        """
        Get files changed since a specific commit.
        
        Args:
            base_commit: Base commit to compare against (e.g., "main", "HEAD~1")
            
        Returns:
            List of changed files
        """
        try:
            # Get list of changed files with status
            output = self._run_git_command([
                "diff", "--name-status", f"{base_commit}...HEAD"
            ])
            
            changes = []
            for line in output.splitlines():
                if not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) < 2:
                    continue
                
                status = parts[0]
                file_path = Path(parts[1])
                
                # Handle renames
                old_path = None
                if status.startswith('R') and len(parts) >= 3:
                    old_path = file_path
                    file_path = Path(parts[2])
                
                changes.append(GitChange(
                    file_path=file_path,
                    status=status[0],  # Take first character for status
                    old_path=old_path
                ))
            
            return changes
            
        except subprocess.CalledProcessError:
            logger.warning("Failed to get changed files, analyzing all files")
            return []
    
    def get_changed_files_since_branch(self, branch: str = "main") -> List[GitChange]:
        """
        Get files changed since branching from a base branch.
        
        Args:
            branch: Base branch name (default: "main")
            
        Returns:
            List of changed files
        """
        try:
            # Find merge base with the branch
            merge_base = self._run_git_command([
                "merge-base", "HEAD", branch
            ])
            
            return self.get_changed_files_since_commit(merge_base)
            
        except subprocess.CalledProcessError:
            logger.warning("Failed to find merge base with %s", branch)
            return []
    
    def get_uncommitted_changes(self) -> List[GitChange]:
        """
        Get uncommitted changes (staged and unstaged).
        
        Returns:
            List of uncommitted changes
        """
        try:
            changes = []
            
            # Get staged changes
            staged_output = self._run_git_command([
                "diff", "--cached", "--name-status"
            ])
            
            for line in staged_output.splitlines():
                if not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    status = parts[0]
                    file_path = Path(parts[1])
                    
                    changes.append(GitChange(
                        file_path=file_path,
                        status=status[0]
                    ))
            
            # Get unstaged changes
            unstaged_output = self._run_git_command([
                "diff", "--name-status"
            ])
            
            for line in unstaged_output.splitlines():
                if not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    status = parts[0]
                    file_path = Path(parts[1])
                    
                    # Avoid duplicates from staged changes
                    if not any(c.file_path == file_path for c in changes):
                        changes.append(GitChange(
                            file_path=file_path,
                            status=status[0]
                        ))
            
            return changes
            
        except subprocess.CalledProcessError:
            logger.warning("Failed to get uncommitted changes")
            return []
    
    def get_python_files_changed(self, base_commit: Optional[str] = None, branch: Optional[str] = None) -> List[Path]:
        """
        Get Python files that have changed.
        
        Args:
            base_commit: Base commit to compare against
            branch: Base branch to compare against
            
        Returns:
            List of changed Python files that exist
        """
        changes = []
        
        if base_commit:
            changes = self.get_changed_files_since_commit(base_commit)
        elif branch:
            changes = self.get_changed_files_since_branch(branch)
        else:
            changes = self.get_uncommitted_changes()
        
        python_files = []
        for change in changes:
            # Skip deleted files
            if change.status == 'D':
                continue
            
            # Only include Python files
            if change.file_path.suffix == '.py':
                full_path = self.repo_path / change.file_path
                if full_path.exists():
                    python_files.append(full_path)
        
        return python_files
    
    def get_affected_modules(self, changed_files: List[Path]) -> Set[str]:
        """
        Get module names affected by the changed files.
        
        Args:
            changed_files: List of changed Python files
            
        Returns:
            Set of affected module names
        """
        modules = set()
        
        for file_path in changed_files:
            try:
                # Convert file path to module name
                relative_path = file_path.relative_to(self.repo_path)
                
                # Remove .py extension
                module_path = relative_path.with_suffix('')
                
                # Convert path separators to dots
                module_name = str(module_path).replace('/', '.').replace('\\', '.')
                
                # Handle __init__.py files
                if module_name.endswith('.__init__'):
                    module_name = module_name[:-9]  # Remove .__init__
                
                modules.add(module_name)
                
            except ValueError:
                # File is outside repo, skip
                continue
        
        return modules
    
    def should_analyze_incrementally(self, max_changed_files: int = 50) -> bool:
        """
        Determine if incremental analysis should be used.
        
        Args:
            max_changed_files: Maximum number of changed files for incremental analysis
            
        Returns:
            True if incremental analysis is recommended
        """
        try:
            # Check if there are uncommitted changes
            uncommitted = self.get_uncommitted_changes()
            if uncommitted:
                return len(uncommitted) <= max_changed_files
            
            # Check changes since main branch
            changed_since_main = self.get_changed_files_since_branch("main")
            return len(changed_since_main) <= max_changed_files
            
        except Exception:
            # If Git operations fail, use full analysis
            return False


class IncrementalAnalysisConfig:
    """Configuration for incremental analysis."""
    
    def __init__(
        self,
        enabled: bool = True,
        base_branch: str = "main",
        max_changed_files: int = 50,
        include_dependencies: bool = True,
        force_full_on_config_change: bool = True
    ):
        """
        Initialize incremental analysis configuration.
        
        Args:
            enabled: Whether incremental analysis is enabled
            base_branch: Base branch for comparison
            max_changed_files: Max files before falling back to full analysis
            include_dependencies: Whether to include files that depend on changed files
            force_full_on_config_change: Force full analysis if config files changed
        """
        self.enabled = enabled
        self.base_branch = base_branch
        self.max_changed_files = max_changed_files
        self.include_dependencies = include_dependencies
        self.force_full_on_config_change = force_full_on_config_change
    
    def should_force_full_analysis(self, changed_files: List[Path]) -> bool:
        """
        Check if full analysis should be forced based on changed files.
        
        Args:
            changed_files: List of changed files
            
        Returns:
            True if full analysis should be forced
        """
        if not self.force_full_on_config_change:
            return False
        
        config_files = {
            '.pythonium.yml',
            '.pythonium.yaml', 
            'pyproject.toml',
            'setup.py',
            'setup.cfg'
        }
        
        for file_path in changed_files:
            if file_path.name in config_files:
                return True
        
        return False
