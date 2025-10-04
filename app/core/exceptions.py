# app/core/exceptions.py

class FormAssistantBaseException(Exception):
    """Base exception for the AI Form Assistant application."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

    def __str__(self):
        return self.message


class NotFoundError(FormAssistantBaseException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: str = None):
        if identifier:
            message = f"{resource} with identifier '{identifier}' not found"
        else:
            message = f"{resource} not found"
        super().__init__(message, error_code="RESOURCE_NOT_FOUND")


class ValidationError(FormAssistantBaseException):
    """Raised when input data fails validation."""

    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(message, error_code="VALIDATION_ERROR")
        if field:
            self.details["field"] = field
        if value is not None:
            self.details["value"] = str(value)


class AuthorizationError(FormAssistantBaseException):
    """Raised when a user attempts an action without sufficient permissions."""

    def __init__(self, action: str = None, resource: str = None):
        if action and resource:
            message = f"Insufficient permissions to {action} {resource}"
        else:
            message = "Insufficient permissions for this action"
        super().__init__(message, error_code="AUTHORIZATION_ERROR")


class AuthenticationError(FormAssistantBaseException):
    """Raised for authentication failures (e.g., invalid credentials, bad token)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTHENTICATION_ERROR")


class SessionError(FormAssistantBaseException):
    """Raised for session-related errors."""

    def __init__(self, message: str = "Session error occurred"):
        super().__init__(message, error_code="SESSION_ERROR")


class DatabaseError(FormAssistantBaseException):
    """Raised for database-related errors."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, error_code="DATABASE_ERROR")


class ExternalServiceError(FormAssistantBaseException):
    """Raised for external service errors (LLM, S3, etc.)."""

    def __init__(self, service: str, message: str = None):
        if not message:
            message = f"External service '{service}' error"
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR")
        self.details["service"] = service


class RateLimitError(FormAssistantBaseException):
    """Raised when rate limits are exceeded."""

    def __init__(self, resource: str = None, retry_after: int = None):
        message = f"Rate limit exceeded for {resource}" if resource else "Rate limit exceeded"
        super().__init__(message, error_code="RATE_LIMIT_ERROR")
        if retry_after:
            self.details["retry_after"] = retry_after


# Legacy compatibility - keeping old names for backward compatibility
BaseAppException = FormAssistantBaseException
PermissionError = AuthorizationError