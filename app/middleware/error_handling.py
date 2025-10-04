"""
Comprehensive error handling middleware for the FastAPI application.

This module provides centralized error handling, logging, and response formatting
for all types of exceptions that can occur in the application.
"""

import logging
import traceback
from typing import Union
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from pymongo.errors import PyMongoError
from bson.errors import InvalidId
from redis.exceptions import RedisError
from app.core.exceptions import (
    FormAssistantBaseException,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and handle all unhandled exceptions.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self.handle_exception(request, exc)

    async def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """
        Handle different types of exceptions and return appropriate responses.
        """
        # Log the exception with request context
        logger.error(
            f"Exception occurred on {request.method} {request.url}: {str(exc)}",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc(),
            }
        )

        # Handle different exception types
        if isinstance(exc, HTTPException):
            return await self._handle_http_exception(exc)

        elif isinstance(exc, RequestValidationError):
            return await self._handle_validation_error(exc)

        elif isinstance(exc, FormAssistantBaseException):
            return await self._handle_custom_exception(exc)

        elif isinstance(exc, PyMongoError):
            return await self._handle_database_error(exc)

        elif isinstance(exc, InvalidId):
            return await self._handle_invalid_id_error(exc)

        elif isinstance(exc, RedisError):
            return await self._handle_redis_error(exc)

        elif isinstance(exc, ValueError):
            return await self._handle_value_error(exc)

        elif isinstance(exc, KeyError):
            return await self._handle_key_error(exc)

        else:
            return await self._handle_generic_error(exc)

    async def _handle_http_exception(self, exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "message": exc.detail,
                    "status_code": exc.status_code,
                }
            }
        )

    async def _handle_validation_error(self, exc: RequestValidationError) -> JSONResponse:
        """Handle Pydantic validation errors"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "validation_error",
                    "message": "Input validation failed",
                    "details": errors,
                }
            }
        )

    async def _handle_custom_exception(self, exc: FormAssistantBaseException) -> JSONResponse:
        """Handle custom application exceptions"""
        status_code = 500

        if isinstance(exc, ValidationError):
            status_code = 400
        elif isinstance(exc, NotFoundError):
            status_code = 404
        elif isinstance(exc, AuthenticationError):
            status_code = 401
        elif isinstance(exc, AuthorizationError):
            status_code = 403

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__.lower(),
                    "message": str(exc),
                    "code": getattr(exc, "error_code", None),
                }
            }
        )

    async def _handle_database_error(self, exc: PyMongoError) -> JSONResponse:
        """Handle MongoDB/PyMongo errors"""
        logger.error(f"Database error: {str(exc)}")

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "database_error",
                    "message": "A database error occurred. Please try again later.",
                }
            }
        )

    async def _handle_invalid_id_error(self, exc: InvalidId) -> JSONResponse:
        """Handle BSON InvalidId errors"""
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "invalid_id",
                    "message": "Invalid ID format provided",
                }
            }
        )

    async def _handle_redis_error(self, exc: RedisError) -> JSONResponse:
        """Handle Redis connection/operation errors"""
        logger.error(f"Redis error: {str(exc)}")

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "cache_error",
                    "message": "A caching error occurred. Please try again later.",
                }
            }
        )

    async def _handle_value_error(self, exc: ValueError) -> JSONResponse:
        """Handle ValueError exceptions"""
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "value_error",
                    "message": str(exc),
                }
            }
        )

    async def _handle_key_error(self, exc: KeyError) -> JSONResponse:
        """Handle KeyError exceptions"""
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "key_error",
                    "message": f"Missing required key: {str(exc)}",
                }
            }
        )

    async def _handle_generic_error(self, exc: Exception) -> JSONResponse:
        """Handle all other unhandled exceptions"""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again later.",
                }
            }
        )


# Exception handler functions for specific use with FastAPI
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Global HTTP exception handler"""
    middleware = ErrorHandlingMiddleware(None)
    return await middleware._handle_http_exception(exc)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Global validation exception handler"""
    middleware = ErrorHandlingMiddleware(None)
    return await middleware._handle_validation_error(exc)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global generic exception handler"""
    middleware = ErrorHandlingMiddleware(None)
    return await middleware.handle_exception(request, exc)