"""
Output filtering and optimization system.

This module provides functionality to filter and optimize analysis output
by applying confidence thresholds, severity filtering, and noise reduction
techniques to improve the signal-to-noise ratio of results.

Features:
- Confidence-based filtering for suggestions and recommendations
- Severity-based filtering (info/warn/error)
- Noise reduction for low-value issues
- Output limiting and prioritization
"""

import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

from .models import Issue, Symbol

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """Configuration for output filtering."""
    min_confidence: float = 0.2  # Minimum confidence for suggestions (0.0-1.0)
    min_severity: str = "info"   # Minimum severity level ("info", "warn", "error") 
    max_issues_per_detector: Optional[int] = 50  # Limit issues per detector
    max_total_issues: Optional[int] = 200  # Limit total issues
    
    # Noise reduction settings
    enable_noise_reduction: bool = True
    max_low_confidence_issues: int = 10  # Max issues with confidence < 0.5
    deduplicate_similar_messages: bool = True
    
    # Issue type filtering
    excluded_issue_types: Set[str] = field(default_factory=set)
    excluded_detectors: Set[str] = field(default_factory=set)
    
    # Priority boosting
    priority_detectors: List[str] = field(default_factory=lambda: [
        'security_smell', 'dead_code', 'exact_clone'
    ])
    priority_severities: List[str] = field(default_factory=lambda: [
        'error', 'warn', 'info'
    ])


@dataclass 
class FilterStats:
    """Statistics about filtering operations."""
    original_count: int = 0
    filtered_count: int = 0
    filtered_by_confidence: int = 0
    filtered_by_severity: int = 0
    filtered_by_detector_limit: int = 0
    filtered_by_total_limit: int = 0
    filtered_by_noise_reduction: int = 0
    
    @property
    def reduction_percentage(self) -> float:
        """Calculate percentage reduction."""
        if self.original_count == 0:
            return 0.0
        return round(100 * (self.original_count - self.filtered_count) / self.original_count, 1)


class OutputFilter:
    """
    Filter and optimize analysis output for better user experience.
    
    This class applies various filtering techniques to reduce noise,
    prioritize important issues, and limit output to manageable sizes
    while preserving the most valuable insights.
    """
    
    def __init__(self, config: FilterConfig = None):
        """
        Initialize the output filter.
        
        Args:
            config: Filter configuration
        """
        self.config = config or FilterConfig()
        self.stats = FilterStats()
    
    def filter_issues(self, issues: List[Issue]) -> Tuple[List[Issue], FilterStats]:
        """
        Filter and optimize a list of issues.
        
        Args:
            issues: List of issues to filter
            
        Returns:
            Tuple of (filtered_issues, filter_stats)
        """
        self.stats = FilterStats(original_count=len(issues))
        
        if not issues:
            return issues, self.stats
        
        # Apply filtering stages
        filtered = issues
        
        # 1. Filter by excluded detectors and issue types
        filtered = self._filter_excluded(filtered)
        
        # 2. Filter by confidence threshold
        filtered = self._filter_by_confidence(filtered)
        
        # 3. Filter by severity
        filtered = self._filter_by_severity(filtered)
        
        # 4. Apply noise reduction
        if self.config.enable_noise_reduction:
            filtered = self._reduce_noise(filtered)
        
        # 5. Apply detector limits
        filtered = self._apply_detector_limits(filtered)
        
        # 6. Apply total limit with prioritization
        filtered = self._apply_total_limit(filtered)
        
        self.stats.filtered_count = len(filtered)
        
        return filtered, self.stats
    
    def _filter_excluded(self, issues: List[Issue]) -> List[Issue]:
        """Filter out excluded detectors and issue types."""
        filtered = []
        
        for issue in issues:
            if issue.detector_id in self.config.excluded_detectors:
                continue
            if issue.id in self.config.excluded_issue_types:
                continue
            filtered.append(issue)
        
        return filtered
    
    def _filter_by_confidence(self, issues: List[Issue]) -> List[Issue]:
        """Filter issues by confidence threshold."""
        filtered = []
        
        for issue in issues:
            confidence = issue.metadata.get('confidence', 1.0)  # Default to high confidence
            
            if confidence >= self.config.min_confidence:
                filtered.append(issue)
            else:
                self.stats.filtered_by_confidence += 1
        
        return filtered
    
    def _filter_by_severity(self, issues: List[Issue]) -> List[Issue]:
        """Filter issues by minimum severity level."""
        severity_order = ['info', 'warn', 'error']
        min_level = severity_order.index(self.config.min_severity)
        
        filtered = []
        
        for issue in issues:
            try:
                issue_level = severity_order.index(issue.severity)
                if issue_level >= min_level:
                    filtered.append(issue)
                else:
                    self.stats.filtered_by_severity += 1
            except ValueError:
                # Unknown severity, include by default
                filtered.append(issue)
        
        return filtered
    
    def _reduce_noise(self, issues: List[Issue]) -> List[Issue]:
        """Apply noise reduction techniques."""
        filtered = list(issues)
        original_count = len(filtered)
        
        # 1. Limit low-confidence issues
        if self.config.max_low_confidence_issues > 0:
            low_confidence = []
            high_confidence = []
            
            for issue in filtered:
                confidence = issue.metadata.get('confidence', 1.0)
                if confidence < 0.5:
                    low_confidence.append(issue)
                else:
                    high_confidence.append(issue)
            
            # Keep only top low-confidence issues
            if len(low_confidence) > self.config.max_low_confidence_issues:
                low_confidence.sort(key=lambda x: x.metadata.get('confidence', 0.0), reverse=True)
                low_confidence = low_confidence[:self.config.max_low_confidence_issues]
            
            filtered = high_confidence + low_confidence
        
        # 2. Deduplicate similar messages
        if self.config.deduplicate_similar_messages:
            filtered = self._deduplicate_messages(filtered)
        
        # 3. Filter out very low-value issues
        filtered = self._filter_low_value(filtered)
        
        self.stats.filtered_by_noise_reduction += original_count - len(filtered)
        return filtered
    
    def _deduplicate_messages(self, issues: List[Issue]) -> List[Issue]:
        """Remove issues with very similar messages."""
        # Group by normalized message
        message_groups = {}
        
        for issue in issues:
            # Normalize message by removing specific names/numbers
            normalized = self._normalize_message(issue.message)
            if normalized not in message_groups:
                message_groups[normalized] = []
            message_groups[normalized].append(issue)
        
        # Keep only the best issue from each group
        filtered = []
        for group in message_groups.values():
            if len(group) == 1:
                filtered.extend(group)
            else:
                # Keep the highest priority issue
                best_issue = max(group, key=self._get_issue_priority)
                filtered.append(best_issue)
        
        return filtered
    
    def _normalize_message(self, message: str) -> str:
        """Normalize a message for similarity comparison."""
        import re
        
        # Remove specific names, numbers, and paths
        normalized = re.sub(r"'[^']*'", "'*'", message)  # Replace quoted strings
        normalized = re.sub(r"\b\d+\b", "N", normalized)  # Replace numbers
        normalized = re.sub(r"\b[A-Z][a-zA-Z0-9_]*\b", "SYMBOL", normalized)  # Replace symbols
        
        return normalized.lower().strip()
    
    def _filter_low_value(self, issues: List[Issue]) -> List[Issue]:
        """Filter out very low-value issues."""
        filtered = []
        
        for issue in issues:
            # Skip issues with very low confidence alternative implementations
            if issue.id == 'alternative-implementation':
                confidence = issue.metadata.get('confidence', 0.0)
                if confidence < 0.1:
                    continue
            
            # Skip trivial complexity warnings for very small functions
            if 'complexity' in issue.id:
                lines = issue.metadata.get('lines', 0)
                if lines < 5:  # Very small functions
                    continue
            
            filtered.append(issue)
        
        return filtered
    
    def _apply_detector_limits(self, issues: List[Issue]) -> List[Issue]:
        """Apply per-detector issue limits."""
        if not self.config.max_issues_per_detector:
            return issues
        
        detector_counts = Counter(issue.detector_id for issue in issues)
        detector_issues = {}
        
        # Group issues by detector
        for issue in issues:
            detector_id = issue.detector_id
            if detector_id not in detector_issues:
                detector_issues[detector_id] = []
            detector_issues[detector_id].append(issue)
        
        # Apply limits per detector
        filtered = []
        for detector_id, detector_issue_list in detector_issues.items():
            if len(detector_issue_list) <= self.config.max_issues_per_detector:
                filtered.extend(detector_issue_list)
            else:
                # Prioritize and limit
                prioritized = sorted(detector_issue_list, key=self._get_issue_priority, reverse=True)
                limited = prioritized[:self.config.max_issues_per_detector]
                filtered.extend(limited)
                
                self.stats.filtered_by_detector_limit += len(detector_issue_list) - len(limited)
        
        return filtered
    
    def _apply_total_limit(self, issues: List[Issue]) -> List[Issue]:
        """Apply total issue limit with prioritization."""
        if not self.config.max_total_issues or len(issues) <= self.config.max_total_issues:
            return issues
        
        # Sort by priority
        prioritized = sorted(issues, key=self._get_issue_priority, reverse=True)
        
        # Take top issues
        filtered = prioritized[:self.config.max_total_issues]
        self.stats.filtered_by_total_limit = len(issues) - len(filtered)
        
        return filtered
    
    def _get_issue_priority(self, issue: Issue) -> Tuple[int, int, float, int]:
        """Get priority score for an issue (higher is better)."""
        # 1. Detector priority (0 = highest priority)
        detector_priority = 999
        if issue.detector_id in self.config.priority_detectors:
            detector_priority = self.config.priority_detectors.index(issue.detector_id)
        
        # 2. Severity priority (0 = highest)
        severity_priority = 999
        if issue.severity in self.config.priority_severities:
            severity_priority = self.config.priority_severities.index(issue.severity)
        
        # 3. Confidence (higher is better)
        confidence = issue.metadata.get('confidence', 1.0)
        
        # 4. Issue ID priority (prefer certain types)
        id_priority = 0
        priority_ids = ['security-risk', 'unused-symbol', 'exact-clone', 'complexity-high']
        for i, priority_id in enumerate(priority_ids):
            if priority_id in issue.id:
                id_priority = len(priority_ids) - i
                break
        
        # Return tuple for sorting (negate priorities to make higher values better)
        return (-detector_priority, -severity_priority, confidence, id_priority)


def create_production_filter_config() -> FilterConfig:
    """Create a filter configuration optimized for production use."""
    return FilterConfig(
        min_confidence=0.3,  # Filter out very low confidence suggestions
        min_severity="info",  # Keep all severities 
        max_issues_per_detector=30,  # Reasonable limit per detector
        max_total_issues=150,  # Keep output manageable
        enable_noise_reduction=True,
        max_low_confidence_issues=15,
        deduplicate_similar_messages=True,
        excluded_issue_types={
            'trivial-complexity',  # Skip very minor complexity issues
        },
    )


def create_strict_filter_config() -> FilterConfig:
    """Create a strict filter configuration for high-signal output."""
    return FilterConfig(
        min_confidence=0.5,  # Only medium+ confidence
        min_severity="warn",  # Only warnings and errors
        max_issues_per_detector=20,
        max_total_issues=100,
        enable_noise_reduction=True,
        max_low_confidence_issues=5,
        deduplicate_similar_messages=True,
        excluded_issue_types={
            'trivial-complexity',
            'minor-style',
            'low-priority',
        },
    )
