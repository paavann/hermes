class JobError(Exception):
    """Base exception for worker job failures."""


class BudgetExhaustedError(JobError):
    """Raised when a stage reaches the configured LLM call budget."""


class SchemaCheckError(JobError):
    """Raised when the database schema does not match the running code."""
