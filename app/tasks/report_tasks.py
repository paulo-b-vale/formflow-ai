"""
Report-related Celery Tasks

Async tasks for generating analytics, reports, and aggregations.
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


@celery_app.task(bind=True, name="app.tasks.report_tasks.generate_daily_analytics")
def generate_daily_analytics(self):
    """
    Generate daily analytics report.

    Aggregates form submissions, user engagement, and agent performance.
    Called by Celery Beat and Airflow DAG daily.

    Returns:
        dict: Daily analytics data
    """
    try:
        logger.info(f"[CELERY] Generating daily analytics, task_id={self.request.id}")

        run_async(connect_to_mongo())

        async def generate_analytics():
            yesterday = datetime.utcnow() - timedelta(days=1)
            today = datetime.utcnow()

            # Aggregate form submissions
            submissions = await db.form_responses.find({
                "submitted_at": {"$gte": yesterday, "$lt": today}
            }).to_list(None)

            total_submissions = len(submissions)

            # Calculate completion rate
            completed = len([s for s in submissions if s.get("status") == "completed"])
            completion_rate = (completed / total_submissions * 100) if total_submissions > 0 else 0

            # Get unique users
            unique_users = len(set(str(s.get("respondent_id")) for s in submissions if s.get("respondent_id")))

            # Calculate average fields per form
            total_fields = sum(len(s.get("responses", {})) for s in submissions)
            avg_fields = (total_fields / total_submissions) if total_submissions > 0 else 0

            # Get agent stats
            agent_executions = await db.agent_executions.find({
                "executed_at": {"$gte": yesterday, "$lt": today}
            }).to_list(None)

            total_agent_calls = len(agent_executions)

            analytics = {
                "date": yesterday.date().isoformat(),
                "form_submissions": {
                    "total": total_submissions,
                    "completed": completed,
                    "completion_rate": round(completion_rate, 2)
                },
                "user_engagement": {
                    "unique_users": unique_users,
                    "avg_fields_per_form": round(avg_fields, 2)
                },
                "agent_performance": {
                    "total_calls": total_agent_calls
                },
                "created_at": datetime.utcnow()
            }

            # Store analytics
            await db.daily_analytics.insert_one(analytics)

            logger.info(f"[CELERY] Daily analytics generated: {total_submissions} submissions")

            return analytics

        result = run_async(generate_analytics())

        return {
            "status": "success",
            "analytics": result
        }

    except Exception as e:
        logger.exception(f"[CELERY] Error generating daily analytics: {e}")
        raise self.retry(exc=e, countdown=120, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.report_tasks.aggregate_form_submissions")
def aggregate_form_submissions(self, start_date: str = None, end_date: str = None):
    """
    Aggregate form submissions for a date range.

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        dict: Aggregated submission data
    """
    try:
        logger.info(f"[CELERY] Aggregating form submissions")

        run_async(connect_to_mongo())

        async def aggregate():
            # Default to last 24 hours if no dates provided
            if not start_date:
                start = datetime.utcnow() - timedelta(days=1)
            else:
                start = datetime.fromisoformat(start_date)

            if not end_date:
                end = datetime.utcnow()
            else:
                end = datetime.fromisoformat(end_date)

            submissions = await db.form_responses.find({
                "submitted_at": {"$gte": start, "$lt": end}
            }).to_list(None)

            # Group by form template
            by_template = {}
            for submission in submissions:
                template_id = str(submission.get("form_template_id", "unknown"))
                if template_id not in by_template:
                    by_template[template_id] = {
                        "count": 0,
                        "completed": 0,
                        "partial": 0
                    }

                by_template[template_id]["count"] += 1
                status = submission.get("status", "unknown")
                if status == "completed":
                    by_template[template_id]["completed"] += 1
                elif status == "partial":
                    by_template[template_id]["partial"] += 1

            return {
                "status": "success",
                "period": {
                    "start": start.isoformat(),
                    "end": end.isoformat()
                },
                "total_submissions": len(submissions),
                "by_template": by_template
            }

        result = run_async(aggregate())
        logger.info(f"[CELERY] Aggregated {result['total_submissions']} submissions")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error aggregating submissions: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.report_tasks.calculate_user_engagement")
def calculate_user_engagement(self):
    """
    Calculate user engagement metrics.

    Returns:
        dict: User engagement data
    """
    try:
        logger.info(f"[CELERY] Calculating user engagement")

        run_async(connect_to_mongo())

        async def calculate():
            yesterday = datetime.utcnow() - timedelta(days=1)

            # Get all sessions from last 24 hours
            # TODO: Implement session tracking
            # For now, use form submissions as proxy

            submissions = await db.form_responses.find({
                "submitted_at": {"$gte": yesterday}
            }).to_list(None)

            # Active users (users who submitted forms)
            active_users = len(set(str(s.get("respondent_id")) for s in submissions if s.get("respondent_id")))

            # Forms per user
            forms_per_user = (len(submissions) / active_users) if active_users > 0 else 0

            return {
                "status": "success",
                "date": yesterday.date().isoformat(),
                "active_users": active_users,
                "forms_per_user": round(forms_per_user, 2),
                "total_submissions": len(submissions)
            }

        result = run_async(calculate())
        logger.info(f"[CELERY] Engagement calculated: {result['active_users']} active users")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error calculating engagement: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.report_tasks.generate_weekly_report")
def generate_weekly_report(self):
    """
    Generate weekly summary report.

    Returns:
        dict: Weekly report data
    """
    try:
        logger.info(f"[CELERY] Generating weekly report")

        run_async(connect_to_mongo())

        async def generate_report():
            week_ago = datetime.utcnow() - timedelta(days=7)

            # Get all daily analytics for the week
            daily_analytics = await db.daily_analytics.find({
                "created_at": {"$gte": week_ago}
            }).to_list(None)

            total_submissions = sum(
                a.get("form_submissions", {}).get("total", 0)
                for a in daily_analytics
            )

            avg_completion_rate = sum(
                a.get("form_submissions", {}).get("completion_rate", 0)
                for a in daily_analytics
            ) / len(daily_analytics) if daily_analytics else 0

            report = {
                "period": "weekly",
                "start_date": week_ago.date().isoformat(),
                "end_date": datetime.utcnow().date().isoformat(),
                "total_submissions": total_submissions,
                "avg_completion_rate": round(avg_completion_rate, 2),
                "days_analyzed": len(daily_analytics),
                "created_at": datetime.utcnow()
            }

            # Store report
            await db.weekly_reports.insert_one(report)

            return report

        result = run_async(generate_report())
        logger.info(f"[CELERY] Weekly report generated: {result['total_submissions']} submissions")

        return {
            "status": "success",
            "report": result
        }

    except Exception as e:
        logger.exception(f"[CELERY] Error generating weekly report: {e}")
        raise self.retry(exc=e, countdown=120, max_retries=2)
