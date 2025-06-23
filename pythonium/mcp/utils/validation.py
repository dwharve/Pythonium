"""
Validation utilities for Pythonium MCP server.

Provides comprehensive validation for tool arguments, configurations,
and data structures with detailed error reporting.
"""

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Type


class ValidationError(Exception):
    """
    Validation error with detailed context.
    """
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Any = None,
        expected_type: Optional[Type] = None,
        validation_rule: Optional[str] = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Value that failed validation
            expected_type: Expected type for the value
            validation_rule: Name of the validation rule that failed
        """
        self.message = message
        self.field = field
        self.value = value
        self.expected_type = expected_type
        self.validation_rule = validation_rule
        
        # Build comprehensive error message
        error_parts = [message]
        if field:
            error_parts.append(f"Field: {field}")
        if value is not None:
            error_parts.append(f"Value: {repr(value)}")
        if expected_type:
            error_parts.append(f"Expected: {expected_type.__name__}")
        if validation_rule:
            error_parts.append(f"Rule: {validation_rule}")
        
        super().__init__(" | ".join(error_parts))


class ValidationRule:
    """
    Represents a single validation rule that can be applied to a value.
    """
    
    def __init__(
        self,
        name: str,
        validator: Callable[[Any], bool],
        error_message: str,
        expected_type: Optional[Type] = None
    ):
        """
        Initialize validation rule.
        
        Args:
            name: Name of the validation rule
            validator: Function that returns True if value is valid
            error_message: Error message if validation fails
            expected_type: Expected type for the value
        """
        self.name = name
        self.validator = validator
        self.error_message = error_message
        self.expected_type = expected_type
    
    def validate(self, value: Any, field: Optional[str] = None) -> None:
        """
        Validate a value against this rule.
        
        Args:
            value: Value to validate
            field: Field name for error reporting
            
        Raises:
            ValidationError: If validation fails
        """
        if not self.validator(value):
            raise ValidationError(
                message=self.error_message,
                field=field,
                value=value,
                expected_type=self.expected_type,
                validation_rule=self.name
            )


class Validator:
    """
    Comprehensive validator with built-in rules and custom validation support.
    """
    
    def __init__(self):
        """Initialize validator with standard rules."""
        self._rules = self._create_standard_rules()
    
    def _create_standard_rules(self) -> Dict[str, ValidationRule]:
        """Create standard validation rules."""
        return {
            "required": ValidationRule(
                name="required",
                validator=lambda x: x is not None and x != "",
                error_message="Value is required"
            ),
            "string": ValidationRule(
                name="string",
                validator=lambda x: isinstance(x, str),
                error_message="Value must be a string",
                expected_type=str
            ),
            "integer": ValidationRule(
                name="integer",
                validator=lambda x: isinstance(x, int) and not isinstance(x, bool),
                error_message="Value must be an integer",
                expected_type=int
            ),
            "boolean": ValidationRule(
                name="boolean",
                validator=lambda x: isinstance(x, bool),
                error_message="Value must be a boolean",
                expected_type=bool
            ),
            "list": ValidationRule(
                name="list",
                validator=lambda x: isinstance(x, list),
                error_message="Value must be a list",
                expected_type=list
            ),
            "dict": ValidationRule(
                name="dict",
                validator=lambda x: isinstance(x, dict),
                error_message="Value must be a dictionary",
                expected_type=dict
            ),
            "path_exists": ValidationRule(
                name="path_exists",
                validator=lambda x: isinstance(x, (str, Path)) and Path(x).exists(),
                error_message="Path must exist"
            ),
            "python_file": ValidationRule(
                name="python_file",
                validator=lambda x: isinstance(x, (str, Path)) and str(x).endswith('.py'),
                error_message="Must be a Python file (.py extension)"
            ),
            "non_empty_string": ValidationRule(
                name="non_empty_string",
                validator=lambda x: isinstance(x, str) and len(x.strip()) > 0,
                error_message="String must not be empty or whitespace",
                expected_type=str
            ),
            "positive_integer": ValidationRule(
                name="positive_integer",
                validator=lambda x: isinstance(x, int) and not isinstance(x, bool) and x > 0,
                error_message="Value must be a positive integer",
                expected_type=int
            ),
            "severity_level": ValidationRule(
                name="severity_level",
                validator=lambda x: x in ["info", "warn", "error"],
                error_message="Severity must be one of: info, warn, error"
            ),
            "classification": ValidationRule(
                name="classification",
                validator=lambda x: x in ["unclassified", "true_positive", "false_positive"],
                error_message="Classification must be one of: unclassified, true_positive, false_positive"
            ),
            "status": ValidationRule(
                name="status",
                validator=lambda x: x in ["pending", "work_in_progress", "completed"],
                error_message="Status must be one of: pending, work_in_progress, completed"
            )
        }
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self._rules[rule.name] = rule
    
    def validate_field(
        self, 
        value: Any, 
        field_name: str, 
        rules: List[str]
    ) -> None:
        """
        Validate a field against a list of rules.
        
        Args:
            value: Value to validate
            field_name: Name of the field
            rules: List of rule names to apply
            
        Raises:
            ValidationError: If any validation rule fails
        """
        for rule_name in rules:
            if rule_name not in self._rules:
                raise ValueError(f"Unknown validation rule: {rule_name}")
            
            self._rules[rule_name].validate(value, field_name)
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, List[str]]) -> None:
        """
        Validate a dictionary against a schema.
        
        Args:
            data: Data to validate
            schema: Schema mapping field names to validation rules
            
        Raises:
            ValidationError: If any field fails validation
        """
        for field_name, rules in schema.items():
            value = data.get(field_name)
            self.validate_field(value, field_name, rules)
    
    def validate_tool_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """
        Validate tool arguments based on predefined schemas.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments to validate
            
        Raises:
            ValidationError: If validation fails
        """
        schema = self._get_tool_schema(tool_name)
        if schema:
            self.validate_schema(arguments, schema)
    
    def _get_tool_schema(self, tool_name: str) -> Optional[Dict[str, List[str]]]:
        """Get validation schema for a specific tool."""
        schemas = {
            "analyze_code": {
                "path": ["required", "string", "path_exists"],
                "detectors": ["list"],
                "config": ["dict"]
            },
            "analyze_inline_code": {
                "code": ["required", "non_empty_string"],
                "filename": ["string"],
                "detectors": ["list"],
                "config": ["dict"]
            },
            "execute_code": {
                "code": ["required", "non_empty_string"],
                "timeout": ["positive_integer"],
                "capture_output": ["boolean"]
            },
            "mark_issue": {
                "issue_hash": ["required", "non_empty_string"],
                "classification": ["classification"],
                "status": ["status"],
                "notes": ["string"],
                "assigned_to": ["string"]
            },
            "get_detector_info": {
                "detector_id": ["required", "non_empty_string"]
            },
            "get_configuration_schema": {
                "section": ["string"]
            }
        }
        return schemas.get(tool_name)


class SchemaValidator:
    """
    Schema validator for complex data structures.
    """
    
    def __init__(self):
        """Initialize schema validator."""
        self.validator = Validator()
    
    def validate_detector_config(self, config: Dict[str, Any]) -> None:
        """
        Validate detector configuration.
        
        Args:
            config: Detector configuration to validate
            
        Raises:
            ValidationError: If configuration is invalid
        """
        schema = {
            "enabled": ["boolean"],
            "severity": ["severity_level"],
            "config": ["dict"]
        }
        self.validator.validate_schema(config, schema)
    
    def validate_analysis_config(self, config: Dict[str, Any]) -> None:
        """
        Validate analysis configuration.
        
        Args:
            config: Analysis configuration to validate
            
        Raises:
            ValidationError: If configuration is invalid
        """
        # Validate top-level structure
        if "analysis" in config:
            analysis_config = config["analysis"]
            if not isinstance(analysis_config, dict):
                raise ValidationError("analysis config must be a dictionary", "analysis")
            
            # Validate analysis settings
            if "track_issues" in analysis_config:
                self.validator.validate_field(
                    analysis_config["track_issues"], 
                    "analysis.track_issues", 
                    ["boolean"]
                )
        
        # Validate performance settings
        if "performance" in config:
            perf_config = config["performance"]
            if not isinstance(perf_config, dict):
                raise ValidationError("performance config must be a dictionary", "performance")
            
            for field, rules in {
                "cache_enabled": ["boolean"],
                "parallel": ["boolean"],
                "max_workers": ["positive_integer"]
            }.items():
                if field in perf_config:
                    self.validator.validate_field(
                        perf_config[field], 
                        f"performance.{field}", 
                        rules
                    )
    
    def validate_issue_data(self, issue_data: Dict[str, Any]) -> None:
        """
        Validate issue data structure.
        
        Args:
            issue_data: Issue data to validate
            
        Raises:
            ValidationError: If issue data is invalid
        """
        required_fields = {
            "id": ["required", "non_empty_string"],
            "detector": ["required", "non_empty_string"],
            "severity": ["required", "severity_level"],
            "message": ["required", "non_empty_string"],
            "file_path": ["required", "string"],
            "line": ["required", "positive_integer"]
        }
        
        self.validator.validate_schema(issue_data, required_fields)
