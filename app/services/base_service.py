# app/services/base_service.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database

class BaseService:
    """
    A base class for all services.
    
    Provides a common `db` attribute and an initialization method
    to ensure services have access to the database connection.
    """
    def __init__(self):
        self.db: AsyncIOMotorDatabase = None

    async def initialize(self):
        """
        Initializes the service by acquiring a database connection.
        This method should be called on application startup for each service.
        """
        if self.db is None:
            self.db = await get_database()