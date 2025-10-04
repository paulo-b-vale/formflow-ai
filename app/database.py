# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
import redis.asyncio as redis
import logging
import os
from app.config.settings import settings
from app.storage.s3_storage import S3Storage

# Set up a logger for database operations
logger = logging.getLogger(__name__)

class DatabaseConnections:
    """A singleton-like class to manage database and cache connections."""
    mongo_client: AsyncIOMotorClient = None
    mongo_db: AsyncIOMotorDatabase = None
    gridfs_bucket: AsyncIOMotorGridFSBucket = None
    redis_pool: redis.ConnectionPool = None
    s3_storage: S3Storage = None

# Create a single instance to be used by the application
db_connections = DatabaseConnections()

# For backward compatibility with existing imports
class DatabaseWrapper:
    def __getattr__(self, name):
        if db_connections.mongo_db is None:
            raise RuntimeError("Database connection has not been initialized.")
        return getattr(db_connections.mongo_db, name)

db = DatabaseWrapper()

async def connect_to_mongo():
    """Wrapper function to connect to databases."""
    await connect_to_databases()

async def close_mongo_connection():
    """Wrapper function to close database connections."""
    await close_database_connections()

async def connect_to_databases():
    """Establishes connections to MongoDB, Redis, and S3 on application startup."""
    logger.info("Initializing database connections...")
    try:
        # Allow runtime override via environment variable for tests
        db_name = os.getenv("DATABASE_NAME", settings.DATABASE_NAME)
        db_connections.mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
        db_connections.mongo_db = db_connections.mongo_client[db_name]
        # Initialize GridFS bucket
        db_connections.gridfs_bucket = AsyncIOMotorGridFSBucket(db_connections.mongo_db)
        logger.info(f"Successfully connected to MongoDB database: '{db_name}' with GridFS support")
    except Exception as e:
        logger.critical(f"Failed to connect to MongoDB: {e}")

    try:
        db_connections.redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
        # Test Redis connection
        r = redis.Redis(connection_pool=db_connections.redis_pool)
        await r.ping()
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        logger.critical(f"Failed to connect to Redis: {e}")

    try:
        # Only initialize S3 if not running tests or if S3 is properly configured
        if os.getenv("TESTING", "").lower() != "true":
            db_connections.s3_storage = S3Storage()
            logger.info("Successfully connected to S3 storage.")
        else:
            logger.info("Running in test mode, skipping S3 initialization.")
    except Exception as e:
        # --- THIS IS THE FIX ---
        # Log the error but don't crash the application
        logger.error(f"Failed to connect to S3 storage: {e}. File uploads will be stored locally.")
        # In non-test mode, we can now continue without S3.
        # This is useful for local development without valid S3 credentials.
        db_connections.s3_storage = None


async def close_database_connections():
    """Closes connections on application shutdown."""
    logger.info("Closing database connections...")
    if db_connections.mongo_client:
        db_connections.mongo_client.close()
        logger.info("MongoDB connection closed.")
    if db_connections.redis_pool:
        await db_connections.redis_pool.disconnect()
        logger.info("Redis connection pool disconnected.")
    # S3 doesn't need explicit disconnection

async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency function to get the MongoDB database instance.
    Ensures that a connection is available.
    """
    if db_connections.mongo_db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_connections.mongo_db

async def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:
    """
    Dependency function to get the GridFS bucket instance.
    Ensures that a connection is available.
    """
    if db_connections.gridfs_bucket is None:
        raise RuntimeError("GridFS bucket has not been initialized.")
    return db_connections.gridfs_bucket

async def get_redis() -> redis.Redis:
    """
    Dependency function to get a Redis client instance from the pool.
    Ensures that a connection is available.
    """
    if db_connections.redis_pool is None:
        raise RuntimeError("Redis connection has not been initialized.")
    return redis.Redis(connection_pool=db_connections.redis_pool)

async def get_s3_storage() -> S3Storage:
    """
    Dependency function to get the S3 storage instance.
    Ensures that S3 storage is available.
    """
    if db_connections.s3_storage is None:
        # This will now be handled gracefully by the FileService
        raise RuntimeError("S3 storage has not been initialized.")
    return db_connections.s3_storage