"""
Agent-related Celery Tasks

Async tasks for agent processing, execution, and performance tracking.
"""

from app.celery_app import celery_app
from app.database import db, connect_to_mongo
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


@celery_app.task(bind=True, name="app.tasks.agent_tasks.process_agent_request")
def process_agent_request(self, agent_name: str, input_data: dict, session_id: str = None):
    """
    Process an agent request asynchronously.

    This offloads heavy AI processing to background workers.

    Args:
        agent_name: Name of the agent to execute
        input_data: Input data for the agent
        session_id: Optional session ID for context

    Returns:
        dict: Agent execution result
    """
    try:
        logger.info(f"[CELERY] Processing agent request: {agent_name}, task_id={self.request.id}")

        # Connect to database
        run_async(connect_to_mongo())

        async def execute_agent():
            # TODO: Import and execute agent
            # from app.services.agent_service import agent_service
            # result = await agent_service.execute_agent(
            #     agent_name=agent_name,
            #     input_data=input_data,
            #     session_id=session_id
            # )

            # For now, return a placeholder
            result = {
                "status": "success",
                "agent": agent_name,
                "output": "Agent execution placeholder",
                "executed_at": datetime.utcnow().isoformat()
            }

            # Store execution log
            await db.agent_executions.insert_one({
                "agent_name": agent_name,
                "input_data": input_data,
                "session_id": session_id,
                "result": result,
                "executed_at": datetime.utcnow(),
                "task_id": self.request.id
            })

            return result

        result = run_async(execute_agent())
        logger.info(f"[CELERY] Agent {agent_name} executed successfully")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error executing agent {agent_name}: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.agent_tasks.update_agent_performance_stats")
def update_agent_performance_stats(self):
    """
    Update agent performance statistics.

    Calculates success rates, average processing times, error rates, etc.
    Called by Airflow DAG daily.

    Returns:
        dict: Performance statistics
    """
    try:
        logger.info(f"[CELERY] Updating agent performance stats, task_id={self.request.id}")

        run_async(connect_to_mongo())

        async def calculate_stats():
            # Get executions from last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)

            executions = await db.agent_executions.find({
                "executed_at": {"$gte": yesterday}
            }).to_list(None)

            # Calculate stats per agent
            agent_stats = {}

            for execution in executions:
                agent_name = execution.get("agent_name")

                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {
                        "total_executions": 0,
                        "successful": 0,
                        "failed": 0,
                        "total_time": 0,
                        "errors": []
                    }

                agent_stats[agent_name]["total_executions"] += 1

                result = execution.get("result", {})
                if result.get("status") == "success":
                    agent_stats[agent_name]["successful"] += 1
                else:
                    agent_stats[agent_name]["failed"] += 1
                    if "error" in result:
                        agent_stats[agent_name]["errors"].append(result["error"])

            # Calculate rates
            for agent_name, stats in agent_stats.items():
                total = stats["total_executions"]
                stats["success_rate"] = (stats["successful"] / total * 100) if total > 0 else 0
                stats["error_rate"] = (stats["failed"] / total * 100) if total > 0 else 0

            # Store in database
            await db.agent_performance_stats.insert_one({
                "date": datetime.utcnow().date().isoformat(),
                "stats": agent_stats,
                "created_at": datetime.utcnow()
            })

            return {
                "status": "success",
                "agents_analyzed": len(agent_stats),
                "total_executions": sum(s["total_executions"] for s in agent_stats.values()),
                "stats": agent_stats
            }

        result = run_async(calculate_stats())
        logger.info(f"[CELERY] Agent performance stats updated: {result['agents_analyzed']} agents")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error updating agent stats: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.agent_tasks.cleanup_old_agent_logs")
def cleanup_old_agent_logs(self, days_to_keep: int = 90):
    """
    Clean up old agent execution logs.

    Args:
        days_to_keep: Number of days of logs to retain

    Returns:
        dict: Cleanup results
    """
    try:
        logger.info(f"[CELERY] Cleaning up agent logs older than {days_to_keep} days")

        run_async(connect_to_mongo())

        async def cleanup():
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            result = await db.agent_executions.delete_many({
                "executed_at": {"$lt": cutoff_date}
            })

            return {
                "status": "success",
                "deleted_count": result.deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }

        result = run_async(cleanup())
        logger.info(f"[CELERY] Deleted {result['deleted_count']} old agent logs")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error cleaning up agent logs: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=2)
