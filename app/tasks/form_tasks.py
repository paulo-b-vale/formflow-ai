"""
Form-related Celery Tasks

Async tasks for form processing, submission, and validation.
"""

from app.celery_app import celery_app
from app.database import db, connect_to_mongo
from datetime import datetime
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


@celery_app.task(bind=True, name="app.tasks.form_tasks.save_form_response_async")
def save_form_response_async(self, form_response_data: dict):
    """
    Save form response to database asynchronously.

    This is the URGENT use case - moves database writes to background.
    User gets instant "Submitted!" response, actual save happens async.

    Args:
        form_response_data: Form response dict to save

    Returns:
        str: Inserted document ID
    """
    try:
        logger.info(f"[CELERY] Saving form response async, task_id={self.request.id}")

        # Connect to database
        run_async(connect_to_mongo())

        # Convert string IDs to ObjectId
        if "form_template_id" in form_response_data and isinstance(form_response_data["form_template_id"], str):
            form_response_data["form_template_id"] = ObjectId(form_response_data["form_template_id"])

        if "context_id" in form_response_data and form_response_data["context_id"]:
            if isinstance(form_response_data["context_id"], str):
                form_response_data["context_id"] = ObjectId(form_response_data["context_id"])

        if "respondent_id" in form_response_data and isinstance(form_response_data["respondent_id"], str):
            form_response_data["respondent_id"] = ObjectId(form_response_data["respondent_id"])

        # Set timestamp
        form_response_data["submitted_at"] = datetime.utcnow()

        # Insert into database
        async def insert():
            result = await db.form_responses.insert_one(form_response_data)
            return str(result.inserted_id)

        response_id = run_async(insert())

        logger.info(f"[CELERY] Form response saved successfully: {response_id}")

        # TODO: Send confirmation email here
        # TODO: Trigger webhooks here

        return response_id

    except Exception as e:
        logger.exception(f"[CELERY] Error saving form response: {e}")
        # Retry up to 3 times
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.form_tasks.validate_form_response")
def validate_form_response(self, form_template_id: str, responses: dict):
    """
    Validate form responses asynchronously.

    Args:
        form_template_id: Form template ID
        responses: Response data

    Returns:
        dict: Validation result
    """
    try:
        logger.info(f"[CELERY] Validating form response for template {form_template_id}")

        # Connect to database
        run_async(connect_to_mongo())

        async def validate():
            # Get form template
            template = await db.form_templates.find_one({"_id": ObjectId(form_template_id)})

            if not template:
                return {"valid": False, "error": "Form template not found"}

            # Validate each field
            errors = []
            fields = template.get("fields", [])

            for field in fields:
                field_id = field.get("field_id")
                is_required = field.get("required", False)

                if is_required and field_id not in responses:
                    errors.append(f"Required field '{field_id}' is missing")

            if errors:
                return {"valid": False, "errors": errors}

            return {"valid": True, "errors": []}

        result = run_async(validate())
        logger.info(f"[CELERY] Validation complete: {result}")

        return result

    except Exception as e:
        logger.exception(f"[CELERY] Error validating form: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.form_tasks.process_bulk_forms")
def process_bulk_forms(self, form_data_list: list):
    """
    Process multiple form submissions in bulk.

    Useful for CSV uploads or batch imports.

    Args:
        form_data_list: List of form data dicts

    Returns:
        dict: Processing results
    """
    try:
        logger.info(f"[CELERY] Processing {len(form_data_list)} forms in bulk")

        results = {
            "total": len(form_data_list),
            "successful": 0,
            "failed": 0,
            "errors": []
        }

        for i, form_data in enumerate(form_data_list):
            try:
                # Queue individual save task
                save_form_response_async.delay(form_data)
                results["successful"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "index": i,
                    "error": str(e)
                })

        logger.info(f"[CELERY] Bulk processing complete: {results}")
        return results

    except Exception as e:
        logger.exception(f"[CELERY] Error in bulk processing: {e}")
        raise self.retry(exc=e, countdown=120, max_retries=2)
