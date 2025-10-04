#!/usr/bin/env python3
"""
Script to add database indexes for improved performance.
Run this script to optimize database queries for the form system.
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_performance_indexes():
    """Add database indexes to improve query performance."""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    try:
        logger.info("Adding performance indexes...")

        # Indexes for contexts collection
        logger.info("Adding indexes for contexts collection...")
        await db.contexts.create_index("created_by")
        await db.contexts.create_index("assigned_users")
        await db.contexts.create_index("assigned_professionals")
        await db.contexts.create_index([("created_by", 1), ("assigned_users", 1)])

        # Indexes for form_templates collection
        logger.info("Adding indexes for form_templates collection...")
        await db.form_templates.create_index("context_id")
        await db.form_templates.create_index("status")
        await db.form_templates.create_index([("context_id", 1), ("status", 1)])
        await db.form_templates.create_index("title")
        await db.form_templates.create_index("tags")

        # Indexes for conversation_logs collection
        logger.info("Adding indexes for conversation_logs collection...")
        await db.conversation_logs.create_index("session_id")
        await db.conversation_logs.create_index("created_at")
        await db.conversation_logs.create_index([("session_id", 1), ("created_at", 1)])

        # Indexes for form_responses collection
        logger.info("Adding indexes for form_responses collection...")
        await db.form_responses.create_index("user_id")
        await db.form_responses.create_index("form_template_id")
        await db.form_responses.create_index("created_at")
        await db.form_responses.create_index([("user_id", 1), ("created_at", -1)])
        await db.form_responses.create_index([("form_template_id", 1), ("created_at", -1)])

        # Indexes for users collection
        logger.info("Adding indexes for users collection...")
        await db.users.create_index("email", unique=True)
        await db.users.create_index("username", unique=True)

        # Compound indexes for common queries
        logger.info("Adding compound indexes...")
        await db.contexts.create_index([
            ("created_by", 1),
            ("assigned_users", 1),
            ("assigned_professionals", 1)
        ])

        await db.form_templates.create_index([
            ("context_id", 1),
            ("status", 1),
            ("created_at", -1)
        ])

        logger.info("✅ All performance indexes added successfully!")

        # List all indexes for verification
        logger.info("Current indexes:")
        for collection_name in ["contexts", "form_templates", "conversation_logs", "form_responses", "users"]:
            indexes = await db[collection_name].list_indexes().to_list(None)
            logger.info(f"{collection_name}: {len(indexes)} indexes")
            for idx in indexes:
                logger.info(f"  - {idx.get('name', 'unnamed')}: {idx.get('key', {})}")

    except Exception as e:
        logger.error(f"Error adding indexes: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(add_performance_indexes())