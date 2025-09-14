"""
User service for managing user authentication and sessions.

This service handles user authentication via unique codes, session management,
and user-related operations.
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import uuid

from app.models.user import User
from app.services.database_service import DatabaseService


class UserService:
    """
    Service for user authentication and management.
    
    Handles user code-based authentication, session management,
    and user profile operations using PostgreSQL.
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize user service with database service.
        
        Args:
            database_service: Database service instance
        """
        self.db = database_service
        self.logger = logging.getLogger(__name__)
        
        # In-memory session cache for performance
        self._session_cache: Dict[str, Tuple[str, datetime]] = {}
    
    def authenticate_user(self, user_code: str) -> Optional[Tuple[User, str]]:
        """
        Authenticate user by code and create session.
        
        Args:
            user_code: User's unique code
            
        Returns:
            Tuple of (User, session_id) if successful, None otherwise
        """
        try:
            if not user_code or not user_code.strip():
                self.logger.warning("Empty user code provided")
                return None
            
            user_code = user_code.strip().upper()
            self.logger.info(f"Authenticating user: {user_code}")
            
            # Get or create user from PostgreSQL
            user_data = self.db.get_user_by_code(user_code)
            
            if not user_data:
                # Create new user
                if not self.db.create_user(user_code):
                    self.logger.error(f"Failed to create user: {user_code}")
                    return None
                
                # Get the created user
                user_data = self.db.get_user_by_code(user_code)
                if not user_data:
                    self.logger.error(f"Failed to retrieve created user: {user_code}")
                    return None
                
                self.logger.info(f"Created new user: {user_code}")
            else:
                self.logger.info(f"Found existing user: {user_code}")
            
            # Convert database data to User object
            user = User.from_dict(user_data)
            
            # Create new session
            session_id = self._create_session(user)
            
            if not session_id:
                self.logger.error(f"Failed to create session for user: {user_code}")
                return None
            
            # Update user with new session
            user.create_new_session()
            # Update user in database
            self._update_user_in_db(user)
            
            return user, session_id
            
        except Exception as e:
            self.logger.error(f"Error authenticating user {user_code}: {str(e)}")
            return None
    
    def validate_session(self, session_id: str) -> Optional[User]:
        """
        Validate session and return user if valid.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            User instance if session is valid, None otherwise
        """
        try:
            if not session_id:
                return None
            
            # Check cache first
            if session_id in self._session_cache:
                user_id, expiry = self._session_cache[session_id]
                
                if datetime.now(timezone.utc) < expiry:
                    # Get user data from database
                    user_code = user_id.replace('user_', '')
                    user_data = self.db.get_user_by_code(user_code)
                    
                    if user_data:
                        user = User.from_dict(user_data)
                        if user and user.is_session_valid():
                            return user
                else:
                    # Remove expired session from cache
                    del self._session_cache[session_id]
            
            # Validate with database
            user_id = self._validate_session_in_db(session_id)
            
            if user_id:
                user_code = user_id.replace('user_', '')
                user_data = self.db.get_user_by_code(user_code)
                
                if user_data:
                    user = User.from_dict(user_data)
                    if user and user.is_session_valid():
                        # Cache valid session
                        self._session_cache[session_id] = (user_id, user.session_expiry)
                        return user
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error validating session {session_id}: {str(e)}")
            return None
    
    def logout_user(self, session_id: str) -> bool:
        """
        Logout user by invalidating session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from cache
            if session_id in self._session_cache:
                del self._session_cache[session_id]
            
            # Invalidate in database
            success = self._invalidate_session_in_db(session_id)
            
            # Also update user record
            user = self.validate_session(session_id)  # This will fail after invalidation
            if user:
                user.invalidate_session()
                self._update_user_in_db(user)
            
            self.logger.info(f"User logged out: {session_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error logging out session {session_id}: {str(e)}")
            return False
    
    def update_user_preferences(self, user: User, preferences: Dict[str, Any]) -> bool:
        """
        Update user preferences.
        
        Args:
            user: User instance to update
            preferences: Dictionary of preferences to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update allowed preferences
            if 'preferred_language' in preferences:
                user.preferred_language = preferences['preferred_language']
            
            if 'default_currency' in preferences:
                user.default_currency = preferences['default_currency']
            
            # Save to database
            success = self._update_user_in_db(user)
            
            if success:
                self.logger.info(f"Updated preferences for user: {user.user_code}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating user preferences: {str(e)}")
            return False
    
    def get_user_statistics(self, user: User) -> Dict[str, Any]:
        """
        Get statistics for a specific user.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary of user statistics
        """
        try:
            # Get shopping lists count from database
            shopping_lists_result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM shopping_lists WHERE user_id = :user_id",
                {'user_id': user.user_id}
            )
            active_lists = shopping_lists_result[0]['count'] if shopping_lists_result else 0
            
            # Get total items count
            items_result = self.db.execute_query(
                """SELECT COUNT(*) as count 
                   FROM shopping_lists sl, jsonb_array_elements(sl.items) as item
                   WHERE sl.user_id = :user_id""",
                {'user_id': user.user_id}
            )
            total_items = items_result[0]['count'] if items_result else 0
            # Get total value
            value_result = self.db.execute_query(
                "SELECT COALESCE(SUM(total_price), 0) as total_value FROM shopping_lists WHERE user_id = :user_id",
                {'user_id': user.user_id}
            )
            total_value = float(value_result[0]['total_value'] or 0) if value_result else 0.0
            
            return {
                'total_lists': active_lists,
                'active_lists': active_lists,
                'total_items': total_items,
                'total_value': total_value,
                'currency': user.default_currency,
                'member_since': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.stats.last_login_at.isoformat() if user.stats and user.stats.last_login_at else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user statistics: {str(e)}")
            return {}
    
    def _create_session(self, user: User, expiry_hours: int = 8) -> Optional[str]:
        """
        Create a new session for user.
        
        Args:
            user: User instance
            expiry_hours: Session expiry time in hours
            
        Returns:
            Session ID if successful, None otherwise
        """
        try:
            session_id = str(uuid.uuid4())
            expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
            
            # Create session in database
            success = self._create_session_in_db(user.user_id, session_id, expiry)
            
            if success:
                # Cache session
                self._session_cache[session_id] = (user.user_id, expiry)
                
                self.logger.debug(f"Created session for user {user.user_code}: {session_id}")
                return session_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating session: {str(e)}")
            return None
    
    def refresh_session(self, session_id: str, expiry_hours: int = 8) -> Optional[str]:
        """
        Refresh an existing session.
        
        Args:
            session_id: Current session ID
            expiry_hours: New expiry time in hours
            
        Returns:
            New session ID if successful, None otherwise
        """
        try:
            # Validate current session
            user = self.validate_session(session_id)
            
            if not user:
                return None
            
            # Invalidate current session
            self.logout_user(session_id)
            
            # Create new session
            return self._create_session(user, expiry_hours)
            
        except Exception as e:
            self.logger.error(f"Error refreshing session {session_id}: {str(e)}")
            return None
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions from cache."""
        try:
            now = datetime.now(timezone.utc)
            expired_sessions = []
            
            for session_id, (user_id, expiry) in self._session_cache.items():
                if now >= expiry:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._session_cache[session_id]
            
            if expired_sessions:
                self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up expired sessions: {str(e)}")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions in cache."""
        return len(self._session_cache)
    
    def is_valid_user_code(self, user_code: str) -> bool:
        """
        Validate user code format.
        
        Args:
            user_code: User code to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not user_code or not isinstance(user_code, str):
            return False
        
        user_code = user_code.strip()
        
        # Basic validation - alphanumeric, 3-20 characters
        if not (3 <= len(user_code) <= 20):
            return False
        
        # Allow alphanumeric characters and common separators
        import re
        pattern = r'^[A-Za-z0-9_-]+$'
        
        return bool(re.match(pattern, user_code))
    
    def _update_user_in_db(self, user: User) -> bool:
        """Update user in PostgreSQL database."""
        try:
            import json
            user_data = user.to_dict()
            
            # Convert preferences dict to JSON string for PostgreSQL
            preferences_json = json.dumps(user_data.get('preferences', {}))
            
            return self.db.execute_update(
                """UPDATE users SET 
                   preferences = :preferences,
                   updated_at = CURRENT_TIMESTAMP,
                   last_activity = CURRENT_TIMESTAMP
                   WHERE user_id = :user_id""",
                {
                    'user_id': user.user_id,
                    'preferences': preferences_json
                }
            )
        except Exception as e:
            self.logger.error(f"Error updating user in database: {str(e)}")
            return False
    
    def _validate_session_in_db(self, session_id: str) -> Optional[str]:
        """Validate session in PostgreSQL database."""
        try:
            results = self.db.execute_query(
                """SELECT user_id FROM user_sessions 
                   WHERE session_id = :session_id 
                   AND active = true 
                   AND expires_at > CURRENT_TIMESTAMP""",
                {'session_id': session_id}
            )
            
            if results:
                return results[0]['user_id']
            return None
            
        except Exception as e:
            self.logger.error(f"Error validating session in database: {str(e)}")
            return None
    
    def _create_session_in_db(self, user_id: str, session_id: str, expiry: datetime) -> bool:
        """Create session record in PostgreSQL database."""
        try:
            return self.db.execute_update(
                """INSERT INTO user_sessions (session_id, user_id, expires_at, created_at, active)
                   VALUES (:session_id, :user_id, :expires_at, CURRENT_TIMESTAMP, true)
                   ON CONFLICT (session_id) DO UPDATE SET
                   expires_at = EXCLUDED.expires_at,
                   active = true""",
                {
                    'session_id': session_id,
                    'user_id': user_id,
                    'expires_at': expiry
                }
            )
        except Exception as e:
            self.logger.error(f"Error creating session in database: {str(e)}")
            return False
    
    def _invalidate_session_in_db(self, session_id: str) -> bool:
        """Invalidate session in PostgreSQL database."""
        try:
            return self.db.execute_update(
                "UPDATE user_sessions SET active = false WHERE session_id = :session_id",
                {'session_id': session_id}
            )
        except Exception as e:
            self.logger.error(f"Error invalidating session in database: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get user service statistics."""
        try:
            # Get total users count
            users_result = self.db.execute_query("SELECT COUNT(*) as count FROM users")
            total_users = users_result[0]['count'] if users_result else 0
            
            # Get active sessions count
            sessions_result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM user_sessions WHERE active = true"
            )
            active_sessions = sessions_result[0]['count'] if sessions_result else 0
            
            return {
                'total_users': total_users,
                'active_sessions': active_sessions
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user statistics: {str(e)}")
            return {'total_users': 0, 'active_sessions': 0}
    
    def _update_user_in_db(self, user: User) -> bool:
        """Update user in PostgreSQL database."""
        try:
            return self.db.execute_update(
                """UPDATE users SET 
                   preferences = :preferences,
                   updated_at = CURRENT_TIMESTAMP,
                   last_activity = CURRENT_TIMESTAMP
                   WHERE user_id = :user_id""",
                {
                    'user_id': user.user_id,
                    'preferences': json.dumps({
                        'preferredLanguage': user.preferred_language,
                        'defaultCurrency': user.default_currency,
                        'activeLists': user.active_lists,
                        'defaultListId': user.default_list_id,
                        'stats': user.stats.to_dict() if user.stats else None
                    })
                }
            )
        except Exception as e:
            self.logger.error(f"Error updating user in database: {str(e)}")
            return False