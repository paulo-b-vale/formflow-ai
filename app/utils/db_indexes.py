"""
Database indexing utilities for performance optimization.

This module provides functions to create and manage database indexes
for commonly queried fields across all collections.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT

logger = logging.getLogger(__name__)


async def create_all_indexes(db: AsyncIOMotorDatabase):
    """
    Create all necessary indexes for optimal query performance.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    logger.info("Creating database indexes for performance optimization...")

    try:
        # User collection indexes
        await create_user_indexes(db)

        # Form templates collection indexes
        await create_form_template_indexes(db)

        # Form responses collection indexes
        await create_form_response_indexes(db)

        # Contexts collection indexes
        await create_context_indexes(db)

        # Conversation logs collection indexes
        await create_conversation_log_indexes(db)

        # Files collection indexes
        await create_file_indexes(db)

        logger.info("✅ All database indexes created successfully")

    except Exception as e:
        logger.error(f"❌ Error creating database indexes: {str(e)}")
        raise


async def create_user_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for users collection"""
    logger.info("Creating indexes for users collection...")

    indexes = [
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("role", ASCENDING)]),
        IndexModel([("is_active", ASCENDING)]),
    ]

    await db.users.create_indexes(indexes)
    logger.info("✅ User indexes created")


async def create_form_template_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for form_templates collection"""
    logger.info("Creating indexes for form_templates collection...")

    indexes = [
        IndexModel([("context_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("title", TEXT)]),
        IndexModel([("tags", ASCENDING)]),
        IndexModel([("context_id", ASCENDING), ("status", ASCENDING)]),  # Compound index
    ]

    await db.form_templates.create_indexes(indexes)
    logger.info("✅ Form template indexes created")


async def create_form_response_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for form_responses collection"""
    logger.info("Creating indexes for form_responses collection...")

    indexes = [
        IndexModel([("form_template_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("submitted_at", DESCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("user_id", ASCENDING), ("submitted_at", DESCENDING)]),  # Compound index
        IndexModel([("form_template_id", ASCENDING), ("status", ASCENDING)]),  # Compound index
    ]

    await db.form_responses.create_indexes(indexes)
    logger.info("✅ Form response indexes created")


async def create_context_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for contexts collection"""
    logger.info("Creating indexes for contexts collection...")

    indexes = [
        IndexModel([("created_by", ASCENDING)]),
        IndexModel([("assigned_users", ASCENDING)]),
        IndexModel([("assigned_professionals", ASCENDING)]),
        IndexModel([("context_type", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("title", TEXT)]),
    ]

    await db.contexts.create_indexes(indexes)
    logger.info("✅ Context indexes created")


async def create_conversation_log_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for conversation_logs collection"""
    logger.info("Creating indexes for conversation_logs collection...")

    indexes = [
        IndexModel([("session_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING)]),
        IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),  # Compound index
        IndexModel([("session_id", ASCENDING), ("timestamp", DESCENDING)]),  # Compound index
    ]

    await db.conversation_logs.create_indexes(indexes)
    logger.info("✅ Conversation log indexes created")


async def create_file_indexes(db: AsyncIOMotorDatabase):
    """Create indexes for files collection"""
    logger.info("Creating indexes for files collection...")

    indexes = [
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("file_type", ASCENDING)]),
        IndexModel([("upload_date", DESCENDING)]),
        IndexModel([("filename", TEXT)]),
        IndexModel([("user_id", ASCENDING), ("upload_date", DESCENDING)]),  # Compound index
    ]

    await db.files.create_indexes(indexes)
    logger.info("✅ File indexes created")


async def drop_all_indexes(db: AsyncIOMotorDatabase):
    """
    Drop all custom indexes (keeping only _id indexes).
    Use with caution - for development/testing only.
    """
    logger.warning("Dropping all custom indexes...")

    collections = ["users", "form_templates", "form_responses", "contexts", "conversation_logs", "files"]

    for collection_name in collections:
        try:
            collection = getattr(db, collection_name)
            indexes = await collection.list_indexes().to_list(length=None)

            for index in indexes:
                if index["name"] != "_id_":  # Don't drop the default _id index
                    await collection.drop_index(index["name"])
                    logger.info(f"Dropped index {index['name']} from {collection_name}")

        except Exception as e:
            logger.warning(f"Could not drop indexes from {collection_name}: {str(e)}")

    logger.info("✅ All custom indexes dropped")


async def list_all_indexes(db: AsyncIOMotorDatabase):
    """List all indexes across all collections"""
    logger.info("Listing all database indexes...")

    collections = ["users", "form_templates", "form_responses", "contexts", "conversation_logs", "files"]

    for collection_name in collections:
        try:
            collection = getattr(db, collection_name)
            indexes = await collection.list_indexes().to_list(length=None)

            logger.info(f"\n{collection_name} collection indexes:")
            for index in indexes:
                logger.info(f"  - {index['name']}: {index.get('key', {})}")

        except Exception as e:
            logger.warning(f"Could not list indexes for {collection_name}: {str(e)}")