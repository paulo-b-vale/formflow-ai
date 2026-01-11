"""
Daily Analytics Pipeline DAG

Runs daily at 2 AM to aggregate form submissions, user metrics, and system stats.

This DAG orchestrates Celery tasks for analytics processing.
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

# Default arguments for the DAG
default_args = {
    'owner': 'flowform_ai',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'daily_analytics_pipeline',
    default_args=default_args,
    description='Aggregate daily analytics and metrics via Celery',
    schedule_interval='0 2 * * *',  # 2 AM daily
    start_date=days_ago(1),
    catchup=False,
    tags=['analytics', 'daily', 'celery'],
)


def trigger_aggregate_form_submissions(**context):
    """Trigger Celery task to aggregate form submissions"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: aggregate_form_submissions")

    # Send task to Celery
    result = celery_app.send_task(
        'app.tasks.report_tasks.aggregate_form_submissions'
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    # Push task_id to XCom for monitoring
    context['ti'].xcom_push(key='task_id', value=task_id)

    return {"status": "triggered", "celery_task_id": task_id}


def trigger_calculate_user_engagement(**context):
    """Trigger Celery task to calculate user engagement"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: calculate_user_engagement")

    result = celery_app.send_task(
        'app.tasks.report_tasks.calculate_user_engagement'
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    context['ti'].xcom_push(key='task_id', value=task_id)

    return {"status": "triggered", "celery_task_id": task_id}


def trigger_update_agent_performance_stats(**context):
    """Trigger Celery task to update agent performance stats"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: update_agent_performance_stats")

    result = celery_app.send_task(
        'app.tasks.agent_tasks.update_agent_performance_stats'
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    context['ti'].xcom_push(key='task_id', value=task_id)

    return {"status": "triggered", "celery_task_id": task_id}


def trigger_generate_daily_analytics(**context):
    """Trigger Celery task to generate complete daily analytics"""
    from app.celery_app import celery_app

    logger.info("[AIRFLOW] Triggering Celery task: generate_daily_analytics")

    # This task aggregates all analytics into one comprehensive report
    result = celery_app.send_task(
        'app.tasks.report_tasks.generate_daily_analytics'
    )

    task_id = result.id
    logger.info(f"[AIRFLOW] Celery task triggered: {task_id}")

    # Pull task IDs from previous tasks
    ti = context['ti']
    previous_tasks = {
        'aggregate_submissions': ti.xcom_pull(task_ids='aggregate_submissions', key='task_id'),
        'calculate_engagement': ti.xcom_pull(task_ids='calculate_engagement', key='task_id'),
        'update_agent_stats': ti.xcom_pull(task_ids='update_agent_stats', key='task_id'),
    }

    logger.info(f"[AIRFLOW] Previous Celery tasks: {previous_tasks}")
    context['ti'].xcom_push(key='task_id', value=task_id)

    return {
        "status": "triggered",
        "celery_task_id": task_id,
        "depends_on": previous_tasks
    }


# Define tasks - All trigger Celery tasks
aggregate_submissions = PythonOperator(
    task_id='aggregate_submissions',
    python_callable=trigger_aggregate_form_submissions,
    dag=dag,
)

calculate_engagement = PythonOperator(
    task_id='calculate_engagement',
    python_callable=trigger_calculate_user_engagement,
    dag=dag,
)

update_agent_stats = PythonOperator(
    task_id='update_agent_stats',
    python_callable=trigger_update_agent_performance_stats,
    dag=dag,
)

generate_daily_analytics = PythonOperator(
    task_id='generate_daily_analytics',
    python_callable=trigger_generate_daily_analytics,
    dag=dag,
)

# Set task dependencies
# Run aggregations in parallel, then generate comprehensive analytics
[aggregate_submissions, calculate_engagement, update_agent_stats] >> generate_daily_analytics
