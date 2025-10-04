"""Module to handle initialization of all services that inherit from BaseService."""
from app.services.auth_service import auth_service
from app.services.user_service import user_service
from app.services.forms_service import forms_service
from app.services.file_service import file_service
from app.services.analytics_service import analytics_service
from app.services.enhanced_conversation_service import enhanced_conversation_service


async def initialize_all_services():
    """Initialize all services that require database or external resource connections."""
    services_to_initialize = [
        auth_service,
        user_service,
        forms_service,
        file_service,
        analytics_service,
        enhanced_conversation_service,
    ]
    
    for service in services_to_initialize:
        try:
            await service.initialize()
        except Exception as e:
            print(f"Error initializing service {service.__class__.__name__}: {e}")
            # Don't raise the exception here since we want to continue initializing other services