"""
Session Cleanup DAG

Runs daily at 3 AM to clean up expired sessions and old data.

This DAG orchestrates Celery tasks for maintenance operations.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import logging
import os
import sys

# Add app directory to Python path so we can import Celery
sys.path.insert(0, os.path.abspath('/app'))

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'flowform_ai',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['admin@flowform-ai.com'],
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    'session_cleanup',
    default_args=default_args,
    description='Clean up expired sessions and old data via Celery',
    schedule_interval='0 3 * * *',  # 3 AM daily
    start_date=days_ago(1),
    catchup=False,
    tags=['maintenance', 'cleanup', 'celery'],
)


def trigger_cleanup_expired_sessions(**context):
    """Trigger Celery task to clean up expired sessions"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: cleanup_expired_sessions")

    result = celery_app.send_task(
        'app.tasks.maintenance_tasks.cleanup_expired_sessions'
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    context['ti'].xcom_push(key='task_id', value=task_id)

    return {"status": "triggered", "celery_task_id": task_id}


def trigger_archive_old_conversations(**context):
    """Trigger Celery task to archive old conversations"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: archive_old_conversations")

    result = celery_app.send_task(
        'app.tasks.maintenance_tasks.archive_old_conversations',
        kwargs={'days_old': 90}
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    context['ti'].xcom_push(key='task_id', value=task_id)

    return {"status": "triggered", "celery_task_id": task_id}


def trigger_cleanup_incomplete_forms(**context):
    """Trigger Celery task to clean up incomplete forms"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: cleanup_incomplete_forms")

    result = celery_app.send_task(
        'app.tasks.maintenance_tasks.cleanup_incomplete_forms',
        kwargs={'days_old': 30}
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    context['ti'].xcom_push(key='task_id', value=task_id)

    return {"status": "triggered", "celery_task_id": task_id}


def trigger_cleanup_agent_logs(**context):
    """Trigger Celery task to clean up old agent logs"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: cleanup_old_agent_logs")

    result = celery_app.send_task(
        'app.tasks.agent_tasks.cleanup_old_agent_logs',
        kwargs={'days_to_keep': 90}
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    context['ti'].xcom_push(key='task_id', value=task_id)

    return {"status": "triggered", "celery_task_id": task_id}


def trigger_optimize_database_indexes(**context):
    """Trigger Celery task to optimize database indexes"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: optimize_database_indexes")

    result = celery_app.send_task(
        'app.tasks.maintenance_tasks.optimize_database_indexes'
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    context['ti'].xcom_push(key='task_id', value=task_id)

    return {"status": "triggered", "celery_task_id": task_id}


# Define tasks - All trigger Celery tasks
cleanup_sessions = PythonOperator(
    task_id='cleanup_sessions',
    python_callable=trigger_cleanup_expired_sessions,
    dag=dag,
)

archive_conversations = PythonOperator(
    task_id='archive_conversations',
    python_callable=trigger_archive_old_conversations,
    dag=dag,
)

cleanup_forms = PythonOperator(
    task_id='cleanup_incomplete_forms',
    python_callable=trigger_cleanup_incomplete_forms,
    dag=dag,
)

cleanup_agent_logs = PythonOperator(
    task_id='cleanup_agent_logs',
    python_callable=trigger_cleanup_agent_logs,
    dag=dag,
)

optimize_indexes = PythonOperator(
    task_id='optimize_indexes',
    python_callable=trigger_optimize_database_indexes,
    dag=dag,
)

# Set dependencies
# Run cleanup tasks in parallel, then optimize indexes at the end
[cleanup_sessions, archive_conversations, cleanup_forms, cleanup_agent_logs] >> optimize_indexes
