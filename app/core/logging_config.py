"""
Centralized logging configuration for production-ready structured logging.
Provides JSON formatting for production and human-readable formatting for development.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any
import os


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON.
    Ideal for production environments where logs are ingested by log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Human-readable colored formatter for development.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build message
        message = f"{color}{timestamp} | {record.levelname:8} | {record.name} | {record.getMessage()}{self.RESET}"
        
        # Add extra context if present
        extras = []
        if hasattr(record, "request_id"):
            extras.append(f"req_id={record.request_id}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration={record.duration_ms}ms")
        if hasattr(record, "status_code"):
            extras.append(f"status={record.status_code}")
            
        if extras:
            message += f" [{', '.join(extras)}]"
            
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
            
        return message


def setup_logging(
    level: str = "INFO",
    json_format: bool = None,
    app_name: str = "flowform"
) -> logging.Logger:
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON format. If None, auto-detect based on environment.
        app_name: Name of the application logger
        
    Returns:
        Configured root logger
    """
    # Auto-detect format based on environment
    if json_format is None:
        json_format = os.getenv("ENVIRONMENT", "development") == "production"
    
    # Get or create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    # Set formatter based on environment
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ColoredFormatter())
    
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    # Also configure uvicorn loggers for consistency
    for uvicorn_logger in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        uv_logger = logging.getLogger(uvicorn_logger)
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"flowform.{name}")


# Convenience function for adding context to log records
class LogContext:
    """Context manager for adding extra fields to log records."""
    
    def __init__(self, logger: logging.Logger, **kwargs: Any):
        self.logger = logger
        self.extra = kwargs
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass
        
    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra={**self.extra, **kwargs})
        
    def error(self, msg: str, **kwargs):
        self.logger.error(msg, extra={**self.extra, **kwargs})
        
    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, extra={**self.extra, **kwargs})
        
    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, extra={**self.extra, **kwargs})
