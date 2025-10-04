# app/main.py
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
from app.cache import cache
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    app.state.db = db

    # Create database indexes for performance
    await create_all_indexes(db)

    # Initialize Redis cache
    await cache.connect()
    app.state.cache = cache

    app.state.redis_manager = RedisManager()
    await app.state.redis_manager.get_redis()
    app.state.session_manager = SessionManager(app.state.redis_manager)
    await app.state.session_manager.start_cleanup_task()

    await initialize_all_services()
    
    yield
    # Shutdown
    await close_mongo_connection()
    await app.state.session_manager.stop_cleanup_task()
    await app.state.redis_manager.close_redis()
    await cache.disconnect()


app = FastAPI(lifespan=lifespan)

# Add error handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Form Assistant API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "AI Form Assistant API is running"}