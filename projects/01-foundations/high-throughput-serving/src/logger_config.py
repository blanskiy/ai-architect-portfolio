#!/usr/bin/env python3
"""
Production-grade logging configuration.

Features:
- Structured JSON logging
- Request correlation IDs
- Multiple log levels
- Performance tracking
- Error tracking with context
"""

import logging
import sys
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger
from typing import Optional
import traceback


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields.
    
    Adds:
    - ISO timestamp
    - Service name
    - Environment
    - Extra context fields
    """
    
    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to log record."""
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        if not log_record.get('timestamp'):
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        
        # Add log level
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        
        # Add service info
        log_record['service'] = 'resnet-serving'
        log_record['environment'] = 'development'  # Change for production
        
        # Add source location
        log_record['source'] = {
            'file': record.filename,
            'line': record.lineno,
            'function': record.funcName
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': ''.join(traceback.format_exception(*record.exc_info))
            }


class RequestContextFilter(logging.Filter):
    """
    Logging filter that adds request context to all logs.
    
    Adds request_id to all log messages within a request context.
    """
    
    def filter(self, record):
        """Add request context if available."""
        # This will be set by middleware
        record.request_id = getattr(record, 'request_id', 'no-request-id')
        return True


def setup_logging(
    log_level: str = "INFO",
    json_logs: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup production-grade logging.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Use JSON format (True) or plain text (False)
        log_file: Optional file path to write logs
        
    Returns:
        Configured logger instance
    """
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Add request context filter
    console_handler.addFilter(RequestContextFilter())
    
    if json_logs:
        # JSON formatter for production
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Simple formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.addFilter(RequestContextFilter())
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Performance tracking helper
class PerformanceLogger:
    """Helper class for tracking operation performance."""
    
    def __init__(self, logger: logging.Logger, operation: str):
        """
        Initialize performance logger.
        
        Args:
            logger: Logger instance
            operation: Name of operation being tracked
        """
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        """Start timing."""
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log results."""
        import time
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.info(
                f"{self.operation} completed",
                extra={
                    'operation': self.operation,
                    'duration_ms': round(duration_ms, 2),
                    'status': 'success'
                }
            )
        else:
            self.logger.error(
                f"{self.operation} failed",
                extra={
                    'operation': self.operation,
                    'duration_ms': round(duration_ms, 2),
                    'status': 'failed',
                    'error_type': exc_type.__name__,
                    'error_message': str(exc_val)
                },
                exc_info=True
            )
        
        return False  # Don't suppress exceptions


# Example usage
if __name__ == "__main__":
    # Setup logging
    logger = setup_logging(log_level="INFO", json_logs=True)
    
    # Get module logger
    module_logger = get_logger(__name__)
    
    # Example logs
    module_logger.info("Application started")
    
    module_logger.info(
        "Processing request",
        extra={
            'request_id': 'abc123',
            'user_id': 'user456',
            'endpoint': '/predict'
        }
    )
    
    # Performance tracking
    with PerformanceLogger(module_logger, "model_inference"):
        import time
        time.sleep(0.1)  # Simulate work
    
    module_logger.warning(
        "High latency detected",
        extra={
            'latency_ms': 5000,
            'threshold_ms': 2000
        }
    )
    
    # Error logging
    try:
        raise ValueError("Test error")
    except Exception as e:
        module_logger.error(
            "Error processing request",
            extra={'request_id': 'xyz789'},
            exc_info=True
        )
