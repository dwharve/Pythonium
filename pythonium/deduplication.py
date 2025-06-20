"""
Issue deduplication system.

This module provides functionality to deduplicate similar issues
reported by multiple detectors, ensuring that users don't see
redundant reports for the same underlying problem.

The deduplication system handles:
- Multiple detectors reporting the same "unused" issues
- Similar issues with different confidence levels
- Overlapping reports from different analysis approaches
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from .models import Issue, Symbol, Location

logger = logging.getLogger(__name__)


@dataclass
class IssueGroup:
    """A group of related/duplicate issues."""
    primary_issue: Issue
    duplicate_issues: List[Issue]
    reason: str
    
    @property
    def total_count(self) -> int:
        """Total number of issues in this group."""
        return 1 + len(self.duplicate_issues)


class DeduplicationEngine:
    """
    Engine for deduplicating similar issues.
    
    This class identifies and consolidates duplicate or highly similar
    issues that may be reported by multiple detectors, improving the
    clarity and usefulness of analysis results.
    """
    
    def __init__(self):
        """Initialize the deduplication engine."""
        # Issue types that should be deduplicated
        self._dedup_patterns = {
            # "Defined but never used" patterns
            'unused_symbol': [
                'unused-symbol',
                'dead-code',
                'unreferenced-symbol',
                'never-used',
            ],
            
            # Code complexity patterns  
            'complexity': [
                'complexity-high',
                'complex-function',
                'cognitive-complexity',
                'cyclomatic-complexity',
            ],
            
            # Code duplication patterns
            'duplication': [
                'exact-clone',
                'near-clone',
                'duplicate-code',
                'similar-code',
            ],
            
            # Security patterns
            'security': [
                'security-risk',
                'security-smell',
                'potential-vulnerability',
                'unsafe-code',
            ]
        }
        
        # Preferred detectors for each issue type (highest priority first)
        self._detector_priority = {
            'unused_symbol': ['dead_code', 'unused_import', 'static_analysis'],
            'complexity': ['complexity_hotspot', 'cognitive_complexity', 'cyclomatic'],
            'duplication': ['exact_clone', 'near_clone', 'duplicate_effort'],
            'security': ['security_smell', 'security_analysis', 'vulnerability'],
        }
    
    def deduplicate_issues(self, issues: List[Issue]) -> Tuple[List[Issue], List[IssueGroup]]:
        """
        Deduplicate a list of issues.
        
        Args:
            issues: List of issues to deduplicate
            
        Returns:
            Tuple of (deduplicated_issues, duplicate_groups)
        """
        # Group issues by symbol and location for deduplication
        symbol_groups = self._group_by_symbol(issues)
        location_groups = self._group_by_location(issues)
        
        deduplicated = []
        duplicate_groups = []
        processed_issues = set()
        
        # Process symbol-based groups first (higher confidence)
        for symbol_fqname, symbol_issues in symbol_groups.items():
            if len(symbol_issues) <= 1:
                continue
            
            group = self._find_duplicates_in_group(symbol_issues, 'symbol')
            if group and group.total_count > 1:
                duplicate_groups.append(group)
                deduplicated.append(group.primary_issue)
                processed_issues.update(id(issue) for issue in symbol_issues)
        
        # Process location-based groups for remaining issues
        for location_key, location_issues in location_groups.items():
            # Skip already processed issues
            remaining_issues = [
                issue for issue in location_issues 
                if id(issue) not in processed_issues
            ]
            
            if len(remaining_issues) <= 1:
                continue
            
            group = self._find_duplicates_in_group(remaining_issues, 'location')
            if group and group.total_count > 1:
                duplicate_groups.append(group)
                deduplicated.append(group.primary_issue)
                processed_issues.update(id(issue) for issue in remaining_issues)
        
        # Add non-duplicate issues
        for issue in issues:
            if id(issue) not in processed_issues:
                deduplicated.append(issue)
        
        return deduplicated, duplicate_groups
    
    def _group_by_symbol(self, issues: List[Issue]) -> Dict[str, List[Issue]]:
        """Group issues by their associated symbol."""
        groups = defaultdict(list)
        for issue in issues:
            if issue.symbol:
                groups[issue.symbol.fqname].append(issue)
        return groups
    
    def _group_by_location(self, issues: List[Issue]) -> Dict[Tuple, List[Issue]]:
        """Group issues by their location."""
        groups = defaultdict(list)
        for issue in issues:
            if issue.location:
                key = (str(issue.location.file), issue.location.line)
                groups[key].append(issue)
        return groups
    
    def _find_duplicates_in_group(self, issues: List[Issue], group_type: str) -> Optional[IssueGroup]:
        """Find duplicates within a group of issues."""
        if len(issues) <= 1:
            return None
        
        # Categorize issues by type
        issue_categories = self._categorize_issues(issues)
        
        # Look for issues in the same category
        for category, category_issues in issue_categories.items():
            if len(category_issues) > 1:
                primary = self._select_primary_issue(category_issues, category)
                duplicates = [issue for issue in category_issues if issue != primary]
                
                reason = f"Multiple detectors reported {category} for same {group_type}"
                return IssueGroup(
                    primary_issue=primary,
                    duplicate_issues=duplicates,
                    reason=reason
                )
        
        return None
    
    def _categorize_issues(self, issues: List[Issue]) -> Dict[str, List[Issue]]:
        """Categorize issues by their type."""
        categories = defaultdict(list)
        
        for issue in issues:
            issue_category = self._get_issue_category(issue.id)
            categories[issue_category].append(issue)
        
        return categories
    
    def _get_issue_category(self, issue_id: str) -> str:
        """Get the category for an issue ID."""
        for category, patterns in self._dedup_patterns.items():
            for pattern in patterns:
                if pattern in issue_id:
                    return category
        return 'other'
    
    def _select_primary_issue(self, issues: List[Issue], category: str) -> Issue:
        """Select the primary issue from a group of duplicates."""
        # Get detector priorities for this category
        priorities = self._detector_priority.get(category, [])
        
        # Sort by detector priority first, then by other criteria
        def priority_key(issue: Issue) -> Tuple[int, str, str]:
            detector_id = issue.detector_id or 'unknown'
            
            # Lower number = higher priority
            detector_priority = len(priorities)
            if detector_id in priorities:
                detector_priority = priorities.index(detector_id)
            
            # Prefer error > warn > info
            severity_priority = {'error': 0, 'warn': 1, 'info': 2}.get(issue.severity, 3)
            
            return (detector_priority, severity_priority, detector_id)
        
        sorted_issues = sorted(issues, key=priority_key)
        return sorted_issues[0]
    
    def get_deduplication_stats(self, original_count: int, deduplicated_count: int, groups: List[IssueGroup]) -> Dict[str, int]:
        """Get statistics about deduplication results."""
        total_duplicates = sum(group.total_count - 1 for group in groups)
        
        return {
            'original_count': original_count,
            'deduplicated_count': deduplicated_count,
            'duplicate_groups': len(groups),
            'total_duplicates_removed': total_duplicates,
            'reduction_percentage': round(100 * total_duplicates / original_count, 1) if original_count > 0 else 0
        }


def deduplicate_issues(issues: List[Issue]) -> Tuple[List[Issue], List[IssueGroup]]:
    """
    Convenience function to deduplicate issues.
    
    Args:
        issues: List of issues to deduplicate
        
    Returns:
        Tuple of (deduplicated_issues, duplicate_groups)
    """
    engine = DeduplicationEngine()
    return engine.deduplicate_issues(issues)
