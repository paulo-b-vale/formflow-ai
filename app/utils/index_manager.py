# app/utils/index_manager.py
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import IndexModel

logger = logging.getLogger(__name__)

async def create_indexes(db: AsyncIOMotorDatabase):
    """Creates necessary indexes for collections on application startup."""
    logger.info("Applying database indexes...")
    try:
        await db.users.create_index("email", unique=True)
        await db.contexts.create_index("assigned_users")
        await db.form_templates.create_index("context_id")
        await db.form_responses.create_index("form_template_id")
        
        # --- NEW INDEX FOR CONVERSATION LOGS ---
        await db.conversation_logs.create_indexes([
            IndexModel("session_id"),
            IndexModel("form_response_id")
        ])

        logger.info("Database indexes applied successfully (or already exist).")
    except Exception as e:
        logger.error(f"An error occurred while creating indexes: {e}")