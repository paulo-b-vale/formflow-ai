"""
Maintenance-related Celery Tasks

Async tasks for cleanup, optimization, and system maintenance.
"""

from app.celery_app import celery_app
from app.database import db, connect_to_mongo
from app.sessions.session_manager import RedisManager
from datetime import datetime, timedelta
from bson import ObjectId
import logging
import asyncio

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in Celery tasks"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.tasks.maintenance_tasks.cleanup_expired_sessions")
def cleanup_expired_sessions(self):
    """
    Clean up expired sessions from Redis.

    Called by Celery Beat daily.

    Returns:
        dict: Cleanup results
    """
    try:
        logger.info(f"[CELERY] Cleaning up expired sessions, task_id={self.request.id}")

        async def cleanup():
            redis_manager = RedisManager()
            redis = await redis_manager.get_redis()

            # Get all session keys
            session_keys = []
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor, match="session:*", count=100)
                session_keys.extend(keys)
                if cursor == 0:
                    break

            deleted_count = 0
            archived_count = 0

            for key in session_keys:
                # Check TTL
                ttl = await redis.ttl(key)

                # If expired or expiring soon (< 1 hour)
                if ttl <= 3600:
                    # Get session data before deletion
                    session_data = await redis.get(key)

                    if session_data and ttl <= 0:
                        # Archive to MongoDB if fully expired
                        try:
                            import json
                            session_dict = json.loads(session_data)
                            session_dict["archived_at"] = datetime.utcnow()
                            session_dict["original_key"] = key.decode() if isinstance(key, bytes) else key

                            await db.archived_sessions.insert_one(session_dict)
                            archived_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to archive session {key}: {e}")

                    # Delete from Redis if expired
                    if ttl <= 0:
                        await redis.delete(key)
                        deleted_count += 1

            await redis_manager.close_redis()

            return {
                "status": "success",
                "total_sessions_checked": len(session_keys),
                "deleted": deleted_count,
                "archived": archived_count
            }

        result = run_async(cleanup())
        logger.info(f"[CELERY] Cleaned up {result['deleted']} sessions, archived {result['archived']}")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error cleaning up sessions: {e}")
        raise self.retry(exc=e, countdown=120, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.maintenance_tasks.cleanup_incomplete_forms")
def cleanup_incomplete_forms(self, days_old: int = 30):
    """
    Delete incomplete form submissions older than specified days.

    Args:
        days_old: Delete forms older than this many days

    Returns:
        dict: Cleanup results
    """
    try:
        logger.info(f"[CELERY] Cleaning up incomplete forms older than {days_old} days")

        run_async(connect_to_mongo())

        async def cleanup():
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Find incomplete forms
            result = await db.form_responses.delete_many({
                "status": {"$in": ["draft", "partial", "incomplete"]},
                "created_at": {"$lt": cutoff_date}
            })

            return {
                "status": "success",
                "deleted": result.deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }

        result = run_async(cleanup())
        logger.info(f"[CELERY] Deleted {result['deleted']} incomplete forms")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error cleaning up forms: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.maintenance_tasks.archive_old_conversations")
def archive_old_conversations(self, days_old: int = 90):
    """
    Archive conversation logs older than specified days to cold storage.

    Args:
        days_old: Archive conversations older than this many days

    Returns:
        dict: Archive results
    """
    try:
        logger.info(f"[CELERY] Archiving conversations older than {days_old} days")

        run_async(connect_to_mongo())

        async def archive():
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Find old conversations
            conversations = await db.conversations.find({
                "created_at": {"$lt": cutoff_date}
            }).to_list(None)

            archived_count = 0

            for conversation in conversations:
                # Move to archive collection
                conversation["archived_at"] = datetime.utcnow()
                await db.archived_conversations.insert_one(conversation)

                # Delete from main collection
                await db.conversations.delete_one({"_id": conversation["_id"]})
                archived_count += 1

            # TODO: Upload to S3 cold storage
            # from app.services.storage_service import upload_to_s3
            # await upload_to_s3(conversations, bucket="cold-storage")

            return {
                "status": "success",
                "archived": archived_count,
                "cutoff_date": cutoff_date.isoformat()
            }

        result = run_async(archive())
        logger.info(f"[CELERY] Archived {result['archived']} conversations")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error archiving conversations: {e}")
        raise self.retry(exc=e, countdown=120, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.maintenance_tasks.optimize_database_indexes")
def optimize_database_indexes(self):
    """
    Optimize database indexes for performance.

    Returns:
        dict: Optimization results
    """
    try:
        logger.info(f"[CELERY] Optimizing database indexes")

        run_async(connect_to_mongo())

        async def optimize():
            # Rebuild indexes
            from app.utils.db_indexes import create_all_indexes
            await create_all_indexes(db)

            # Get index stats
            collections = await db.list_collection_names()
            index_count = 0

            for collection_name in collections:
                collection = db[collection_name]
                indexes = await collection.list_indexes().to_list(None)
                index_count += len(indexes)

            return {
                "status": "success",
                "collections_optimized": len(collections),
                "total_indexes": index_count
            }

        result = run_async(optimize())
        logger.info(f"[CELERY] Optimized {result['total_indexes']} indexes across {result['collections_optimized']} collections")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error optimizing indexes: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.maintenance_tasks.health_check")
def health_check(self):
    """
    Perform system health check.

    Returns:
        dict: Health check results
    """
    try:
        logger.info(f"[CELERY] Performing system health check")

        async def check_health():
            health_status = {
                "timestamp": datetime.utcnow().isoformat(),
                "mongodb": "unknown",
                "redis": "unknown"
            }

            # Check MongoDB
            try:
                run_async(connect_to_mongo())
                await db.command("ping")
                health_status["mongodb"] = "healthy"
            except Exception as e:
                health_status["mongodb"] = f"unhealthy: {str(e)}"

            # Check Redis
            try:
                redis_manager = RedisManager()
                redis = await redis_manager.get_redis()
                await redis.ping()
                health_status["redis"] = "healthy"
                await redis_manager.close_redis()
            except Exception as e:
                health_status["redis"] = f"unhealthy: {str(e)}"

            return health_status

        result = run_async(check_health())
        logger.info(f"[CELERY] Health check complete: {result}")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error in health check: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
