# app/sessions/session_manager_fixed.py
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import uuid4
from enum import Enum
from app.utils.observability import ObservabilityMixin, monitor

logger = logging.getLogger(__name__)


class EnhancedBaseAgent(ObservabilityMixin):
    """Base agent class providing common functionality for all agents."""
    
    def __init__(self, db, session_data: 'SessionData'):
        super().__init__()
        self.db = db
        self.session_data = session_data

    async def _log_conversation_turn(self, role: str, message: str, form_response_id: str = None):
        """Log a conversation turn with enhanced metadata."""
        from datetime import datetime
        
        log_entry = {
            "session_id": self.session_data.session_id,
            "role": role,
            "message": message,
            "timestamp": datetime.utcnow(),
            "form_response_id": form_response_id
        }
        
        try:
            await self.db.conversation_logs.insert_one(log_entry)
        except Exception as e:
            self.log_error(f"Failed to log conversation turn: {e}")

    async def _build_success_response(self, message: str, is_complete: bool = False, form_response_id: str = None):
        """Build a standardized success response."""
        try:
            # Log the conversation turn
            await self._log_conversation_turn("assistant", message, form_response_id)
            
            return {
                "message": message,
                "is_complete": is_complete,
                "form_response_id": form_response_id,
                "status": "success"
            }
        except Exception as e:
            self.log_error(f"Error building success response: {e}")
            return {
                "message": f"An error occurred: {str(e)}",
                "is_complete": True,
                "status": "error"
            }

    async def _build_error_response(self, error_message: str):
        """Build a standardized error response."""
        try:
            return {
                "message": error_message,
                "is_complete": True,
                "status": "error"
            }
        except Exception as e:
            self.log_error(f"Error building error response: {e}")
            return {
                "message": "An unexpected error occurred",
                "is_complete": True,
                "status": "error"
            }


class RedisManager:
    """Simple Redis manager for session storage (placeholder implementation)."""
    
    def __init__(self):
        self.redis_client = None
        
    async def get_redis(self):
        """Get Redis client instance with better error handling."""
        if self.redis_client:
            try:
                # Test if connection is still alive
                await self.redis_client.ping()
                return self.redis_client
            except:
                # If connection failed, reset and try to reconnect
                self.redis_client = None
        
        try:
            # Try to import redis
            import redis.asyncio as redis
            # Use environment variable or default Redis URL
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")  # Use env var or default
            self.redis_client = redis.from_url(redis_url, 
                                              socket_connect_timeout=5,
                                              socket_timeout=5,
                                              retry_on_timeout=True)
            # Test the connection
            await self.redis_client.ping()
            return self.redis_client
        except ImportError:
            logger.warning("Redis not installed. Falling back to in-memory storage.")
            # If redis is not available, return a mock object
            class MockRedis:
                async def ping(self):
                    return True
                async def get(self, key):
                    return None
                async def set(self, key, value, ex=None):
                    pass
                async def delete(self, key):
                    pass
                async def keys(self, pattern):
                    return []
                async def close(self):
                    pass
            return MockRedis()
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory storage.")
            # Return mock Redis client if connection fails
            class MockRedis:
                async def ping(self):
                    return True
                async def get(self, key):
                    return None
                async def set(self, key, value, ex=None):
                    pass
                async def delete(self, key):
                    pass
                async def keys(self, pattern):
                    return []
                async def close(self):
                    pass
            return MockRedis()
    
    async def save_session(self, session_data: 'SessionData') -> bool:
        """Save session to Redis with TTL."""
        try:
            redis_client = await self.get_redis()
            import json
            session_dict = session_data.to_dict()
            await redis_client.setex(
                f"session:{session_data.session_id}",
                120 * 60,  # TTL in seconds (2 hours)
                json.dumps(session_dict, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Error saving session to Redis: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional['SessionData']:
        """Retrieve session from Redis."""
        try:
            redis_client = await self.get_redis()
            session_data_json = await redis_client.get(f"session:{session_id}")
            if session_data_json:
                import json
                session_dict = json.loads(session_data_json)
                return SessionData.from_dict(session_dict)
            return None
        except Exception as e:
            logger.error(f"Error retrieving session from Redis: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        try:
            redis_client = await self.get_redis()
            result = await redis_client.delete(f"session:{session_id}")
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting session from Redis: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List['SessionData']:
        """Get all sessions for a user from Redis."""
        try:
            redis_client = await self.get_redis()
            # In a real Redis implementation, you would use Redis patterns or a secondary index
            # For now, return empty list as this is complex to implement without proper indexing
            return []
        except Exception as e:
            logger.error(f"Error getting user sessions from Redis: {e}")
            return []
    
    async def cleanup_expired_sessions(self, timeout_minutes: int) -> int:
        """Clean up expired sessions from Redis. Since Redis handles TTL automatically, 
        we just return 0 deleted count as expired keys are already removed."""
        # Redis automatically removes expired keys, so we just return 0
        # This is a placeholder implementation to satisfy the interface
        return 0
    
    async def get_session_analytics(self) -> Dict[str, Any]:
        """Get session analytics from Redis storage."""
        try:
            redis_client = await self.get_redis()
            # Count keys with session pattern to get total count
            session_keys = []
            try:
                session_keys = await redis_client.keys("session:*")
            except:
                pass  # Redis might not support keys command in cluster mode
            
            total_sessions = len(session_keys) if session_keys else 0
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": total_sessions,  # Assuming all stored sessions are active until TTL expires
                "sessions_by_state": {},
                "average_session_duration": 0,
                "sessions_created_today": 0,
                "sessions_completed_today": 0
            }
        except Exception as e:
            logger.error(f"Error getting session analytics from Redis: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "sessions_by_state": {},
                "average_session_duration": 0,
                "sessions_created_today": 0,
                "sessions_completed_today": 0
            }
        
    async def close(self):
        """Close the Redis connection."""
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


class SessionState(Enum):
    """Enumeration of possible session states."""
    STARTING = "STARTING"
    IN_PROGRESS = "IN_PROGRESS"
    CONFIRMATION = "CONFIRMATION"
    AWAITING_FORM_CONFIRMATION = "AWAITING_FORM_CONFIRMATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"


class SessionData:
    """Enhanced session data with better timeout handling"""
    
    def __init__(self, session_id: str, user_id: str, form_template_id: str = None, **kwargs):
        self.session_id = session_id
        self.user_id = user_id
        self.form_template_id = form_template_id
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.last_activity = kwargs.get('last_activity', datetime.utcnow())
        
        # Enhanced state handling
        state = kwargs.get('state', SessionState.STARTING.value)
        if isinstance(state, SessionState):
            self.state = state
        else:
            try:
                self.state = SessionState(state.upper() if isinstance(state, str) else state)
            except ValueError:
                logger.warning(f"Invalid state value: {state}, defaulting to IN_PROGRESS")
                self.state = SessionState.IN_PROGRESS
        
        self.responses = kwargs.get('responses', {})
        self.missing_required_fields = kwargs.get('missing_required_fields', [])
        self.conversation_history = kwargs.get('conversation_history', [])
        self.current_field_index = kwargs.get('current_field_index', 0)
        self.current_field = kwargs.get('current_field', None)
        self.field_responses = kwargs.get('field_responses', {})
        self.submission_id = kwargs.get('submission_id', None)
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.completed_at = kwargs.get('completed_at', None)
        
        # Track session activity for better timeout handling
        self.activity_count = kwargs.get('activity_count', 0)
        self.last_user_message = kwargs.get('last_user_message', '')

    def update_activity(self):
        """Update session activity timestamp and counter."""
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.activity_count += 1

    def is_active(self, timeout_minutes: int = 120) -> bool:
        """Enhanced activity check with more lenient timeout."""
        if not self.last_activity:
            return False
        
        if isinstance(self.last_activity, str):
            try:
                last_activity = datetime.fromisoformat(self.last_activity)
            except ValueError:
                logger.warning(f"Invalid last_activity format: {self.last_activity}")
                return False
        else:
            last_activity = self.last_activity
            
        time_since_activity = datetime.utcnow() - last_activity
        is_active = time_since_activity.total_seconds() < (timeout_minutes * 60)
        
        # Log activity status for debugging
        if not is_active:
            logger.info(f"Session {self.session_id} marked inactive. Last activity: {time_since_activity.total_seconds():.0f} seconds ago")
        
        return is_active

    def is_recently_created(self, minutes: int = 5) -> bool:
        """Check if session was created recently (helps prevent premature expiration)."""
        if not self.created_at:
            return False
            
        if isinstance(self.created_at, str):
            try:
                created_at = datetime.fromisoformat(self.created_at)
            except ValueError:
                return False
        else:
            created_at = self.created_at
            
        time_since_creation = datetime.utcnow() - created_at
        return time_since_creation.total_seconds() < (minutes * 60)

    def to_dict(self) -> Dict[str, Any]:
        """Enhanced serialization with better datetime handling."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'form_template_id': self.form_template_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'state': self.state.value if isinstance(self.state, SessionState) else self.state,
            'responses': self.responses,
            'missing_required_fields': self.missing_required_fields,
            'conversation_history': self.conversation_history,
            'current_field_index': self.current_field_index,
            'current_field': self.current_field,
            'field_responses': self.field_responses,
            'submission_id': self.submission_id,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'activity_count': self.activity_count,
            'last_user_message': self.last_user_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Enhanced deserialization with better error handling."""
        try:
            # Convert state
            if 'state' in data:
                try:
                    data['state'] = SessionState(data['state']) if isinstance(data['state'], str) else data['state']
                except ValueError:
                    logger.warning(f"Invalid state in data: {data['state']}, defaulting to IN_PROGRESS")
                    data['state'] = SessionState.IN_PROGRESS
            
            # Convert datetime strings
            datetime_fields = ['created_at', 'last_activity', 'updated_at', 'completed_at']
            for field in datetime_fields:
                if field in data and data[field]:
                    try:
                        data[field] = datetime.fromisoformat(data[field])
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid datetime format for {field}: {data[field]}, error: {e}")
                        if field in ['created_at', 'last_activity', 'updated_at']:
                            data[field] = datetime.utcnow()  # Set to now for critical fields
                        else:
                            data[field] = None

            return cls(**data)
            
        except Exception as e:
            logger.error(f"Error deserializing session data: {e}")
            # Return a minimal valid session if deserialization fails
            return cls(
                session_id=data.get('session_id', str(uuid4())),
                user_id=data.get('user_id', ''),
                form_template_id=data.get('form_template_id', '')
            )


class SessionManager(ObservabilityMixin):
    """Enhanced session manager with improved timeout handling and reliability."""
    
    def __init__(self, storage_backend=None, session_timeout_minutes: int = 120):
        """Initialize with longer default timeout to prevent premature expiration."""
        self.storage_backend = storage_backend or InMemorySessionStorage()
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.session_timeout_minutes = session_timeout_minutes  # Store for easy access
        self._cleanup_task = None
        logger.info(f"SessionManager initialized with {session_timeout_minutes} minute timeout")
    
    async def start_cleanup_task(self):
        """Start background cleanup with more conservative timing."""
        async def cleanup_loop():
            while True:
                try:
                    await self._cleanup_expired_sessions()
                    await asyncio.sleep(600)  # Cleanup every 10 minutes instead of 5
                except Exception as e:
                    logger.error(f"Error in session cleanup: {e}")
                    await asyncio.sleep(120)  # Wait 2 minutes on error
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    @monitor
    async def create_session(self, user_id: str, **kwargs) -> SessionData:
        """Create a new session with enhanced initialization."""
        session_id = str(uuid4())
        
        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            state=SessionState.STARTING,
            **kwargs
        )
        
        # Ensure session is saved successfully
        save_success = await self.storage_backend.save_session(session_data)
        if not save_success:
            logger.error(f"Failed to save new session {session_id}")
            raise Exception(f"Could not create session {session_id}")
        
        self.log_info(f"Created new session {session_id} for user {user_id}")
        return session_data
    
    @monitor
    async def get_session(self, session_id: str) -> Optional['SessionData']:
        """Enhanced session retrieval with better timeout logic."""
        if not session_id:
            return None
        
        session_data = await self.storage_backend.get_session(session_id)
        
        if not session_data:
            self.log_debug(f"Session {session_id} not found in storage")
            return None
        
        # Enhanced activity check - be more lenient for recently created sessions
        if session_data.is_recently_created(minutes=10):
            # Recently created sessions get more time
            self.log_debug(f"Session {session_id} is recently created, skipping timeout check")
            session_data.update_activity()  # Update activity
            await self.storage_backend.save_session(session_data)  # Save the update
            return session_data
        
        # Regular timeout check for older sessions
        if not session_data.is_active(timeout_minutes=self.session_timeout_minutes):
            self.log_info(f"Session {session_id} has expired")
            await self.delete_session(session_id)
            return None
        
        # Update activity and save
        session_data.update_activity()
        await self.storage_backend.save_session(session_data)
        
        return session_data
    
    @monitor
    async def save_session(self, session_data: 'SessionData') -> bool:
        """Enhanced session saving with validation."""
        session_data.updated_at = datetime.utcnow()
        session_data.last_activity = datetime.utcnow()
        
        success = await self.storage_backend.save_session(session_data)
        
        if success:
            self.log_debug(f"Saved session {session_data.session_id}")
        else:
            self.log_error(f"Failed to save session {session_data.session_id}")
        
        return success
    
    @monitor
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session with logging."""
        success = await self.storage_backend.delete_session(session_id)
        
        if success:
            self.log_info(f"Deleted session {session_id}")
        else:
            self.log_warning(f"Failed to delete session {session_id}")
        
        return success
    
    @monitor
    async def get_user_sessions(self, user_id: str, active_only: bool = True) -> List['SessionData']:
        """Get all sessions for a user with enhanced filtering."""
        sessions = await self.storage_backend.get_user_sessions(user_id)
        
        if active_only:
            active_sessions = []
            
            for session in sessions:
                # Use the same logic as get_session for consistency
                if session.is_recently_created(minutes=10) or session.is_active(timeout_minutes=self.session_timeout_minutes):
                    active_sessions.append(session)
                else:
                    # Clean up expired session
                    await self.delete_session(session.session_id)
            
            return active_sessions
        
        return sessions
    
    @monitor
    async def cleanup_user_sessions(self, user_id: str, keep_latest: int = 1) -> int:
        """Clean up old sessions for a user, keeping the most recent ones."""
        sessions = await self.get_user_sessions(user_id, active_only=False)
        
        if len(sessions) <= keep_latest:
            return 0
        
        # Sort by last activity (most recent first)
        sessions.sort(key=lambda s: s.last_activity, reverse=True)
        
        # Delete older sessions
        sessions_to_delete = sessions[keep_latest:]
        deleted_count = 0
        
        for session in sessions_to_delete:
            if await self.delete_session(session.session_id):
                deleted_count += 1
        
        self.log_info(f"Cleaned up {deleted_count} sessions for user {user_id}")
        return deleted_count
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions with conservative approach."""
        try:
            # Use longer timeout for cleanup to be more conservative
            cleanup_timeout_minutes = max(self.session_timeout_minutes * 2, 240)  # At least 4 hours
            
            deleted_count = await self.storage_backend.cleanup_expired_sessions(
                timeout_minutes=cleanup_timeout_minutes
            )
            
            if deleted_count > 0:
                self.log_info(f"Cleaned up {deleted_count} expired sessions (timeout: {cleanup_timeout_minutes} minutes)")
                
        except Exception as e:
            self.log_error(f"Error during session cleanup: {e}")
    
    async def get_session_analytics(self) -> Dict[str, Any]:
        """Get analytics about current sessions."""
        try:
            analytics = await self.storage_backend.get_session_analytics()
            return analytics
        except Exception as e:
            self.log_error(f"Error getting session analytics: {e}")
            return {}
    
    async def clear_all_sessions(self):
        """Clear all sessions - useful for debugging or resetting state."""
        try:
            cleared_count = await self.storage_backend.clear_all_sessions()
            self.log_info(f"Cleared {cleared_count} sessions")
            return cleared_count
        except Exception as e:
            self.log_error(f"Error clearing all sessions: {e}")
            return 0

    async def close(self):
        """Clean up resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if hasattr(self.storage_backend, 'close'):
            await self.storage_backend.close()


class InMemorySessionStorage:
    """Enhanced in-memory session storage with better timeout handling."""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._user_sessions: Dict[str, List[str]] = {}
    
    async def save_session(self, session_data: 'SessionData') -> bool:
        """Save session data to memory with validation."""
        try:
            session_dict = session_data.to_dict()
            self._sessions[session_data.session_id] = session_dict
            
            # Track user sessions
            user_id = session_data.user_id
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            
            if session_data.session_id not in self._user_sessions[user_id]:
                self._user_sessions[user_id].append(session_data.session_id)
            
            logger.debug(f"Saved session {session_data.session_id} to memory")
            return True
            
        except Exception as e:
            logger.error(f"Error saving session to memory: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional['SessionData']:
        """Retrieve session from memory with enhanced error handling."""
        try:
            session_dict = self._sessions.get(session_id)
            if not session_dict:
                logger.debug(f"Session {session_id} not found in memory storage")
                return None
            
            session_data = SessionData.from_dict(session_dict)
            logger.debug(f"Retrieved session {session_id} from memory")
            return session_data
            
        except Exception as e:
            logger.error(f"Error retrieving session from memory: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from memory with cleanup."""
        try:
            if session_id in self._sessions:
                session_dict = self._sessions.pop(session_id)
                user_id = session_dict.get("user_id")
                
                # Remove from user sessions tracking
                if user_id and user_id in self._user_sessions:
                    try:
                        self._user_sessions[user_id].remove(session_id)
                        if not self._user_sessions[user_id]:
                            del self._user_sessions[user_id]
                    except ValueError:
                        pass  # Session ID not in list
                
                logger.debug(f"Deleted session {session_id} from memory")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting session from memory: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List['SessionData']:
        """Get all sessions for a user from memory."""
        try:
            session_ids = self._user_sessions.get(user_id, [])
            sessions = []
            
            for session_id in session_ids[:]:  # Copy to allow modification
                session_dict = self._sessions.get(session_id)
                if session_dict:
                    sessions.append(SessionData.from_dict(session_dict))
                else:
                    # Clean up stale reference
                    self._user_sessions[user_id].remove(session_id)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting user sessions from memory: {e}")
            return []
    
    async def cleanup_expired_sessions(self, timeout_minutes: int) -> int:
        """Clean up expired sessions from memory with conservative timeout."""
        try:
            current_time = datetime.utcnow()
            expired_sessions = []
            
            for session_id, session_dict in self._sessions.items():
                try:
                    # Create SessionData object to use enhanced timeout logic
                    session_data = SessionData.from_dict(session_dict)
                    
                    # Don't expire recently created sessions
                    if session_data.is_recently_created(minutes=10):
                        continue
                    
                    # Use the session's own activity check
                    if not session_data.is_active(timeout_minutes=timeout_minutes):
                        expired_sessions.append(session_id)
                        
                except Exception as e:
                    logger.warning(f"Error checking session {session_id} expiration: {e}")
                    # Mark problematic sessions for deletion
                    expired_sessions.append(session_id)
            
            # Delete expired sessions
            deleted_count = 0
            for session_id in expired_sessions:
                if await self.delete_session(session_id):
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions from memory")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    async def get_session_analytics(self) -> Dict[str, Any]:
        """Get session analytics from memory storage."""
        try:
            current_time = datetime.utcnow()
            today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            total_sessions = len(self._sessions)
            active_sessions = 0
            sessions_by_state = {}
            sessions_created_today = 0
            sessions_completed_today = 0
            session_durations = []
            
            for session_dict in self._sessions.values():
                try:
                    session_data = SessionData.from_dict(session_dict)
                    
                    # Check if active (within timeout)
                    if session_data.is_active(timeout_minutes=30):  # 30 min for "active"
                        active_sessions += 1
                    
                    # Count by state
                    state = session_data.state.value if isinstance(session_data.state, SessionState) else session_data.state
                    sessions_by_state[state] = sessions_by_state.get(state, 0) + 1
                    
                    # Count sessions created today
                    if session_data.created_at >= today_start:
                        sessions_created_today += 1
                    
                    # Count sessions completed today and calculate duration
                    if session_data.completed_at and session_data.completed_at >= today_start:
                        sessions_completed_today += 1
                        duration = (session_data.completed_at - session_data.created_at).total_seconds() / 60
                        session_durations.append(duration)
                
                except Exception as e:
                    logger.debug(f"Error processing session analytics: {e}")
                    continue
            
            average_duration = sum(session_durations) / len(session_durations) if session_durations else 0
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "sessions_by_state": sessions_by_state,
                "average_session_duration": round(average_duration, 2),
                "sessions_created_today": sessions_created_today,
                "sessions_completed_today": sessions_completed_today
            }
            
        except Exception as e:
            logger.error(f"Error getting session analytics: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "sessions_by_state": {},
                "average_session_duration": 0,
                "sessions_created_today": 0,
                "sessions_completed_today": 0
            }

    async def clear_all_sessions(self) -> int:
        """Clear all sessions from memory storage."""
        try:
            session_count = len(self._sessions)
            self._sessions.clear()
            self._user_sessions.clear()
            logger.info(f"Cleared {session_count} sessions from memory")
            return session_count
        except Exception as e:
            logger.error(f"Error clearing sessions: {e}")
            return 0