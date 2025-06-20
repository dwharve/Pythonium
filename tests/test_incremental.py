"""
Tests for the incremental analysis module.
"""

import unittest
from pathlib import Path
import tempfile
import os
import shutil
import subprocess
from unittest.mock import patch, MagicMock, call

from pythonium.incremental import GitAnalyzer, GitChange


class TestGitAnalyzer(unittest.TestCase):
    """Test cases for the GitAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for the test repository
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir)
        
        # Initialize Git repository for testing
        self._init_git_repo()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _init_git_repo(self):
        """Initialize a Git repository for testing."""
        # Initialize repository
        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True)
        
        # Configure Git for test environment
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_dir, capture_output=True)
        
        # Create initial file and commit
        test_file = self.repo_path / "test.py"
        test_file.write_text('print("Hello, World!")')
        
        subprocess.run(["git", "add", "test.py"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.temp_dir, capture_output=True)
    
    def test_init_valid_repo(self):
        """Test initializing GitAnalyzer with a valid repository."""
        analyzer = GitAnalyzer(self.repo_path)
        self.assertEqual(analyzer.repo_path, self.repo_path)
    
    def test_init_invalid_repo(self):
        """Test initializing GitAnalyzer with an invalid repository."""
        invalid_path = Path(tempfile.mkdtemp())
        with self.assertRaises(ValueError):
            GitAnalyzer(invalid_path)
        
        shutil.rmtree(invalid_path, ignore_errors=True)
    
    def test_run_git_command(self):
        """Test running Git command."""
        analyzer = GitAnalyzer(self.repo_path)
        result = analyzer._run_git_command(["status"])
        self.assertIn("On branch", result)
    
    def test_run_git_command_error(self):
        """Test running Git command with error."""
        analyzer = GitAnalyzer(self.repo_path)
        with self.assertRaises(subprocess.CalledProcessError):
            analyzer._run_git_command(["non-existent-command"])
    
    def test_get_changed_files_since_commit(self):
        """Test getting changed files since a commit."""
        # Create a new file and modify existing file
        new_file = self.repo_path / "new_file.py"
        new_file.write_text('print("New file")')
        
        test_file = self.repo_path / "test.py"
        test_file.write_text('print("Modified file")')
        
        # Add and commit the changes
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Changes for testing"], cwd=self.temp_dir, capture_output=True)
        
        # Create an analyzer
        analyzer = GitAnalyzer(self.repo_path)
        
        # Test getting changes since the initial commit
        changes = analyzer.get_changed_files_since_commit("HEAD~1")
        
        # Verify changes were detected
        self.assertEqual(len(changes), 2)
        
        # Check for modified file
        modified_changes = [c for c in changes if c.file_path == Path("test.py") and c.status == "M"]
        self.assertEqual(len(modified_changes), 1)
        
        # Check for new file
        new_changes = [c for c in changes if c.file_path == Path("new_file.py") and c.status == "A"]
        self.assertEqual(len(new_changes), 1)
    
    def test_get_changed_files_with_rename(self):
        """Test getting changed files with renamed files."""
        # Create a file to rename
        rename_file = self.repo_path / "rename_file.py"
        rename_file.write_text('print("File to rename")')
        
        # Add and commit the file
        subprocess.run(["git", "add", "rename_file.py"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add file to rename"], cwd=self.temp_dir, capture_output=True)
        
        # Rename the file
        renamed_file = self.repo_path / "renamed.py"
        subprocess.run(["git", "mv", "rename_file.py", "renamed.py"], cwd=self.temp_dir, capture_output=True)
        
        # Commit the rename
        subprocess.run(["git", "commit", "-m", "Rename file"], cwd=self.temp_dir, capture_output=True)
        
        # Create an analyzer
        analyzer = GitAnalyzer(self.repo_path)
        
        # Test getting changes since before the rename
        changes = analyzer.get_changed_files_since_commit("HEAD~1")
        
        # Verify changes were detected
        self.assertEqual(len(changes), 1)
        
        # Find renamed file
        rename_changes = [c for c in changes if c.status == "R"]
        self.assertTrue(len(rename_changes) > 0)
        
        # Check renamed file properties
        if len(rename_changes) > 0:
            self.assertEqual(rename_changes[0].file_path, Path("renamed.py"))
    
    @patch('subprocess.run')
    def test_get_changed_files_since_branch(self, mock_run):
        """Test getting changed files since branch."""
        # Setup mock responses
        merge_base_result = MagicMock()
        merge_base_result.stdout = "abcd1234\n"
        merge_base_result.stderr = ""
        
        diff_result = MagicMock()
        diff_result.stdout = "M\tmodified_file.py\nA\tnew_file.py\n"
        diff_result.stderr = ""
        
        def mock_run_side_effect(cmd, **kwargs):
            if "merge-base" in cmd:
                return merge_base_result
            elif "diff" in cmd:
                return diff_result
            return MagicMock()
        
        mock_run.side_effect = mock_run_side_effect
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        
        # Create analyzer
        analyzer = GitAnalyzer(self.repo_path)
        
        # Call the method
        changes = analyzer.get_changed_files_since_branch("main")
        
        # Verify changes
        self.assertEqual(len(changes), 2)
        
        # Check calls
        mock_run.assert_has_calls([
            call(['git', 'merge-base', 'HEAD', 'main'], 
                 cwd=self.repo_path, capture_output=True, text=True, check=True),
            call(['git', 'diff', '--name-status', 'abcd1234...HEAD'], 
                 cwd=self.repo_path, capture_output=True, text=True, check=True)
        ], any_order=False)
    
    @patch('subprocess.run')
    def test_get_uncommitted_changes(self, mock_run):
        """Test getting uncommitted changes."""
        # Setup mock responses
        staged_result = MagicMock()
        staged_result.stdout = "A\tstaged_file.py\n"
        staged_result.stderr = ""
        
        unstaged_result = MagicMock()
        unstaged_result.stdout = "M\tunstaged_file.py\n"
        unstaged_result.stderr = ""
        
        def mock_run_side_effect(cmd, **kwargs):
            if "--cached" in cmd:
                return staged_result
            else:
                return unstaged_result
        
        mock_run.side_effect = mock_run_side_effect
        
        # Create analyzer
        analyzer = GitAnalyzer(self.repo_path)
        
        # Call the method
        changes = analyzer.get_uncommitted_changes()
        
        # Verify changes
        self.assertEqual(len(changes), 2)
        
        # Check for staged file
        staged_changes = [c for c in changes if c.file_path == Path("staged_file.py")]
        self.assertEqual(len(staged_changes), 1)
        
        # Check for unstaged file
        unstaged_changes = [c for c in changes if c.file_path == Path("unstaged_file.py")]
        self.assertEqual(len(unstaged_changes), 1)
    
    @patch('subprocess.run')
    def test_get_python_files_changed(self, mock_run):
        """Test getting Python files that have changed."""
        # Setup mock responses
        diff_result = MagicMock()
        diff_result.stdout = "M\tfile.py\nA\tanother.py\nD\tdeleted.py\nM\tnot_python.txt\n"
        diff_result.stderr = ""
        mock_run.return_value = diff_result
        
        # Create temporary Python files
        py_file1 = self.repo_path / "file.py"
        py_file1.write_text('print("Test file")')
        
        py_file2 = self.repo_path / "another.py"
        py_file2.write_text('print("Another file")')
        
        # Create analyzer
        analyzer = GitAnalyzer(self.repo_path)
        
        # Call the method
        python_files = analyzer.get_python_files_changed(base_commit="HEAD~1")
        
        # Verify only existing Python files are included
        self.assertEqual(len(python_files), 2)
        self.assertIn(self.repo_path / "file.py", python_files)
        self.assertIn(self.repo_path / "another.py", python_files)
    
    def test_get_affected_modules(self):
        """Test getting affected modules."""
        # Create analyzer
        analyzer = GitAnalyzer(self.repo_path)
        
        # Create file paths
        file1 = self.repo_path / "module" / "submodule" / "file.py"
        file2 = self.repo_path / "package" / "__init__.py"
        file3 = Path("/absolute/path/outside/repo.py")  # Outside repo
        
        # Create directories
        (self.repo_path / "module" / "submodule").mkdir(parents=True, exist_ok=True)
        (self.repo_path / "package").mkdir(parents=True, exist_ok=True)
        
        # Create files
        file1.write_text('print("Test file")')
        file2.write_text('print("Init file")')
        
        # Call the method
        modules = analyzer.get_affected_modules([file1, file2, file3])
        
        # Verify modules are correctly converted
        self.assertEqual(len(modules), 2)
        self.assertIn("module.submodule.file", modules)
        self.assertIn("package", modules)
    
    @patch('pythonium.incremental.GitAnalyzer.get_uncommitted_changes')
    @patch('pythonium.incremental.GitAnalyzer.get_changed_files_since_branch')
    def test_should_analyze_incrementally(self, mock_branch_changes, mock_uncommitted):
        """Test determining if incremental analysis should be used."""
        # Create analyzer
        analyzer = GitAnalyzer(self.repo_path)
        
        # Case 1: Small number of uncommitted changes
        mock_uncommitted.return_value = [GitChange(file_path=Path("file1.py"), status="M")]
        self.assertTrue(analyzer.should_analyze_incrementally(max_changed_files=5))
        
        # Case 2: Large number of uncommitted changes
        mock_uncommitted.return_value = [GitChange(file_path=Path(f"file{i}.py"), status="M") for i in range(10)]
        self.assertFalse(analyzer.should_analyze_incrementally(max_changed_files=5))
        
        # Case 3: Small number of branch changes
        mock_uncommitted.return_value = []
        mock_branch_changes.return_value = [GitChange(file_path=Path("file1.py"), status="M")]
        self.assertTrue(analyzer.should_analyze_incrementally(max_changed_files=5))
        
        # Case 4: Large number of branch changes
        mock_branch_changes.return_value = [GitChange(file_path=Path(f"file{i}.py"), status="M") for i in range(10)]
        self.assertFalse(analyzer.should_analyze_incrementally(max_changed_files=5))


class TestIncrementalAnalysisFunctions(unittest.TestCase):
    """Test cases for the incremental analysis functions."""
    
    def test_git_change_dataclass(self):
        """Test GitChange dataclass."""
        # Basic GitChange
        change = GitChange(file_path=Path("test.py"), status="M")
        self.assertEqual(change.file_path, Path("test.py"))
        self.assertEqual(change.status, "M")
        self.assertIsNone(change.old_path)
        
        # GitChange with old path (rename)
        change = GitChange(file_path=Path("new.py"), status="R", old_path=Path("old.py"))
        self.assertEqual(change.file_path, Path("new.py"))
        self.assertEqual(change.status, "R")
        self.assertEqual(change.old_path, Path("old.py"))
        
    def test_incremental_analysis_config(self):
        """Test IncrementalAnalysisConfig class."""
        from pythonium.incremental import IncrementalAnalysisConfig
        
        # Test default configuration
        config = IncrementalAnalysisConfig()
        self.assertTrue(config.enabled)
        self.assertEqual(config.base_branch, "main")
        self.assertEqual(config.max_changed_files, 50)
        self.assertTrue(config.include_dependencies)
        self.assertTrue(config.force_full_on_config_change)
        
        # Test custom configuration
        config = IncrementalAnalysisConfig(
            enabled=False,
            base_branch="develop",
            max_changed_files=10,
            include_dependencies=False,
            force_full_on_config_change=False
        )
        self.assertFalse(config.enabled)
        self.assertEqual(config.base_branch, "develop")
        self.assertEqual(config.max_changed_files, 10)
        self.assertFalse(config.include_dependencies)
        self.assertFalse(config.force_full_on_config_change)
    
    def test_should_force_full_analysis(self):
        """Test checking if full analysis should be forced."""
        from pythonium.incremental import IncrementalAnalysisConfig
        
        # Create configuration
        config = IncrementalAnalysisConfig()
        
        # Test with config file change
        changed_files = [
            Path("src/module.py"),
            Path(".pythonium.yml")
        ]
        self.assertTrue(config.should_force_full_analysis(changed_files))
        
        # Test with pyproject.toml change
        changed_files = [
            Path("src/module.py"),
            Path("pyproject.toml")
        ]
        self.assertTrue(config.should_force_full_analysis(changed_files))
        
        # Test with no config file changes
        changed_files = [
            Path("src/module.py"),
            Path("README.md")
        ]
        self.assertFalse(config.should_force_full_analysis(changed_files))
        
        # Test with force_full_on_config_change disabled
        config.force_full_on_config_change = False
        changed_files = [
            Path("src/module.py"),
            Path(".pythonium.yml")
        ]
        self.assertFalse(config.should_force_full_analysis(changed_files))


if __name__ == "__main__":
    unittest.main()
