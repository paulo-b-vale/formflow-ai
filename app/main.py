# app/main.py
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.database import db, close_mongo_connection, connect_to_mongo
from app.routers import (
    user_router,
    auth_router,
    forms_router,
    admin_router,
    file_router,
    enhanced_conversation_router,
    analytics_router,
    openwebui_adapter,
    agent_router,
)
from app.sessions.session_manager import RedisManager, SessionManager
from app.services.service_initializer import initialize_all_services
from app.utils.db_indexes import create_all_indexes
from app.middleware import (
    ErrorHandlingMiddleware,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.core.logging_config import setup_logging, get_logger
from app.cache import cache
from contextlib import asynccontextmanager

# Initialize structured logging
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_format=os.getenv("ENVIRONMENT") == "production"
)
logger = get_logger("main")

# Track startup time for health checks
startup_time: datetime = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_time
    startup_time = datetime.utcnow()
    
    logger.info("Starting FlowForm AI API...")
    
    # Startup
    await connect_to_mongo()
    app.state.db = db
    logger.info("✓ MongoDB connected")

    # Create database indexes for performance
    await create_all_indexes(db)
    logger.info("✓ Database indexes created")

    # Initialize Redis cache
    await cache.connect()
    app.state.cache = cache
    logger.info("✓ Redis cache connected")

    app.state.redis_manager = RedisManager()
    await app.state.redis_manager.get_redis()
    app.state.session_manager = SessionManager(app.state.redis_manager)
    await app.state.session_manager.start_cleanup_task()
    logger.info("✓ Session manager initialized")

    await initialize_all_services()
    logger.info("✓ All services initialized")
    
    logger.info("🚀 FlowForm AI API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FlowForm AI API...")
    await close_mongo_connection()
    await app.state.session_manager.stop_cleanup_task()
    await app.state.redis_manager.close_redis()
    await cache.disconnect()
    logger.info("👋 FlowForm AI API shutdown complete")


app = FastAPI(
    title="FlowForm AI API",
    description="AI-powered form assistant with conversational interface",
    version="1.0.0",
    lifespan=lifespan
)

# Add request logging middleware (must be first)
app.add_middleware(RequestLoggingMiddleware)

# Add error handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include all routers with the correct prefixes
app.include_router(user_router.router, prefix="/users", tags=["users"])
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(forms_router.router, prefix="/forms-management", tags=["forms"])
app.include_router(admin_router.router, prefix="/forms-management", tags=["admin"])
app.include_router(file_router.router, prefix="/files", tags=["files"])
app.include_router(
    enhanced_conversation_router.router,
    prefix="/enhanced_conversation",
    tags=["enhanced_conversation"],
)
app.include_router(
    analytics_router.router, prefix="/analytics", tags=["analytics"]
)
app.include_router(
    openwebui_adapter.router, prefix="/api/v1", tags=["openwebui"]
)
app.include_router(
    agent_router.router, prefix="/agents", tags=["agents"]
)


@app.get("/", tags=["health"])
def read_root():
    """Root endpoint with basic API info."""
    return {
        "name": "FlowForm AI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["health"])
def health_check():
    """
    Basic health check endpoint.
    Returns 200 if the API is running.
    """
    return {
        "status": "healthy",
        "service": "flowform-ai-api",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/ready", tags=["health"])
async def readiness_check():
    """
    Readiness check endpoint.
    Verifies that all dependencies are available.
    """
    checks = {
        "database": False,
        "cache": False,
    }
    
    # Check MongoDB
    try:
        await db.client.admin.command("ping")
        checks["database"] = True
    except Exception:
        pass
    
    # Check Redis
    try:
        if cache._redis:
            await cache._redis.ping()
            checks["cache"] = True
    except Exception:
        pass
    
    all_healthy = all(checks.values())
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds() if startup_time else 0,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/metrics", tags=["health"])
async def metrics():
    """
    Basic metrics endpoint.
    Can be extended for Prometheus integration.
    """
    return {
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds() if startup_time else 0,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0"
    }