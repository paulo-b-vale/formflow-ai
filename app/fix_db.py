import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings
from datetime import datetime

async def fix_db():
    print("Starting database fix...")
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    
    # Delete test accounts
    res = await db.users.delete_many({'email': {'$regex': r'.*@service\.local$'}})
    print(f"Deleted {res.deleted_count} invalid users (service.local)")
    
    now = datetime.utcnow()
    users = await db.users.find({}).to_list(length=1000)
    fixed_count = 0
    for u in users:
        updates = {}
        if u.get('created_at') is None: updates['created_at'] = now
        if u.get('updated_at') is None: updates['updated_at'] = now
        if u.get('is_active') is None: updates['is_active'] = True
        if u.get('role') is None: updates['role'] = 'user'
        
        # Ensure role is a string if it's an enum object
        if hasattr(u.get('role'), 'value'):
            updates['role'] = u['role'].value
            
        if updates:
            await db.users.update_one({'_id': u['_id']}, {'$set': updates})
            fixed_count += 1
            
    print(f"Fixed {fixed_count} users by adding missing fields")
    client.close()
    print("Database fix complete.")

if __name__ == "__main__":
    asyncio.run(fix_db())
