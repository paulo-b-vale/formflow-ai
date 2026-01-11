#!/usr/bin/env python3
"""Script to set a user as admin"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings

async def set_admin():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    result = await db.users.update_one(
        {"email": "admin@example.com"}, 
        {"$set": {"role": "admin"}}
    )
    print(f"Modified {result.modified_count} user(s)")
    client.close()

if __name__ == "__main__":
    asyncio.run(set_admin())
