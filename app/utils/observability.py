"""
Observability utilities for the AI Form Assistant Application
Provides logging, monitoring, and metrics collection capabilities
"""
import functools
import time
import logging
from typing import Callable, Any
import asyncio
import inspect


class ObservabilityMixin:
    """
    A mixin class that provides basic observability features like logging to classes.
    """
    
    @property
    def logger(self):
        """Get a logger instance for the class."""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger

    def log_info(self, message: str):
        """Log an info message."""
        self.logger.info(message)

    def log_error(self, error: Exception, context: str = ""):
        """Log an error with context."""
        if context:
            self.logger.error(f"Error in {context}: {str(error)}")
        else:
            self.logger.error(f"Error: {str(error)}")

    def log_warning(self, message: str):
        """Log a warning message."""
        self.logger.warning(message)

    def log_debug(self, message: str):
        """Log a debug message."""
        self.logger.debug(message)


def monitor(func: Callable) -> Callable:
    """
    A decorator to monitor function execution time and basic metrics.
    Works with both sync and async functions.
    """
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logging.info(f"{func_name} executed successfully in {execution_time:.4f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logging.error(f"{func_name} failed after {execution_time:.4f}s: {str(e)}")
                raise
        
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logging.info(f"{func_name} executed successfully in {execution_time:.4f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logging.error(f"{func_name} failed after {execution_time:.4f}s: {str(e)}")
                raise
        
        return sync_wrapper


def monitor_async(func: Callable) -> Callable:
    """
    A decorator to monitor async function execution time and basic metrics.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logging.info(f"{func_name} executed successfully in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logging.error(f"{func_name} failed after {execution_time:.4f}s: {str(e)}")
            raise
    
    return wrapper


# Alternative async decorator that can handle both sync and async functions
def monitor_general(func: Callable) -> Callable:
    """
    A decorator that monitors both sync and async functions.
    """
    if inspect.iscoroutinefunction(func):
        return monitor_async(func)
    else:
        return monitor(func)