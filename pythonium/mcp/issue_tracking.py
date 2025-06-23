from .services.issue_tracking import IssueTracker

class IssueClassification:
    UNCLASSIFIED = "unclassified"
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"

class IssueStatus:
    PENDING = "pending"
    WORK_IN_PROGRESS = "work_in_progress"
    COMPLETED = "completed"
