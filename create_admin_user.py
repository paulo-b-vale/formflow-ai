#!/usr/bin/env python3
"""
Script to create an initial admin user in the database
"""

import asyncio
import os
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Add the project root to the Python path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.security import get_password_hash
from app.models.enums import UserRole
from app.config.settings import settings


async def create_admin_user(email: str, password: str, name: str = "Admin User"):
    """Create an initial admin user in the database."""
    
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    try:
        # Check if admin user already exists
        existing_admin = await db.users.find_one({"role": "admin"})
        if existing_admin:
            print(f"Admin user already exists: {existing_admin['email']}")
            return False
        
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create the admin user document
        admin_user = {
            "email": email,
            "name": name,
            "hashed_password": hashed_password,
            "role": UserRole.ADMIN.value,  # Use the enum value
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert the admin user into the database
        result = await db.users.insert_one(admin_user)
        
        print(f"Admin user created successfully with ID: {result.inserted_id}")
        print(f"Email: {email}")
        print("Please use these credentials to log in to the admin panel.")
        
        return True
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False
    finally:
        client.close()


async def main():
    """Main function to create an admin user."""
    
    # Default values - you can change these
    email = input("Enter admin email (default: admin@example.com): ").strip()
    if not email:
        email = "admin@example.com"
    
    password = input("Enter admin password (default: admin123): ").strip()
    if not password:
        password = "admin123"
    
    name = input("Enter admin name (default: Admin User): ").strip()
    if not name:
        name = "Admin User"
    
    print("\nCreating admin user...")
    success = await create_admin_user(email, password, name)
    
    if success:
        print("\nAdmin user created successfully!")
        print(f"Login credentials:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print("\nYou can now access the admin panel at /admin in the frontend.")
    else:
        print("\nFailed to create admin user.")


if __name__ == "__main__":
    asyncio.run(main())