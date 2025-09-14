"""
User service for managing user authentication and sessions.

This service handles user authentication via unique codes, session management,
and user-related operations.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import uuid

from app.models.user import User
from app.services.firebase_service import FirebaseService


class UserService:
    """
    Service for user authentication and management.
    
    Handles user code-based authentication, session management,
    and user profile operations.
    """
    
    def __init__(self, firebase_service: FirebaseService):
        """
        Initialize user service with Firebase service.
        
        Args:
            firebase_service: Firebase service instance
        """
        self.firebase = firebase_service
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
            
            # Get or create user
            user = self.firebase.get_user_by_code(user_code)
            
            if not user:
                # Create new user
                user = self.firebase.create_user(user_code)
                if not user:
                    self.logger.error(f"Failed to create user: {user_code}")
                    return None
                
                self.logger.info(f"Created new user: {user_code}")
            else:
                self.logger.info(f"Found existing user: {user_code}")
            
            # Create new session
            session_id = self._create_session(user)
            
            if not session_id:
                self.logger.error(f"Failed to create session for user: {user_code}")
                return None
            
            # Update user with new session
            user.create_new_session()
            self.firebase.update_user(user)
            
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
                    # Get user data
                    user_code = user_id.replace('user_', '')
                    user = self.firebase.get_user_by_code(user_code)
                    
                    if user and user.is_session_valid():
                        return user
                else:
                    # Remove expired session from cache
                    del self._session_cache[session_id]
            
            # Validate with Firebase
            user_id = self.firebase.validate_session(session_id)
            
            if user_id:
                user_code = user_id.replace('user_', '')
                user = self.firebase.get_user_by_code(user_code)
                
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
            
            # Invalidate in Firebase
            success = self.firebase.invalidate_session(session_id)
            
            # Also update user record
            user = self.validate_session(session_id)  # This will fail after invalidation
            if user:
                user.invalidate_session()
                self.firebase.update_user(user)
            
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
            
            # Save to Firebase
            success = self.firebase.update_user(user)
            
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
            # Get shopping lists count
            shopping_lists = self.firebase.get_shopping_lists_by_user(user.user_id)
            
            active_lists = sum(1 for list_item in shopping_lists if list_item.status == 'active')
            total_items = sum(list_item.get_item_count() for list_item in shopping_lists)
            total_value = sum(list_item.get_total_price() for list_item in shopping_lists if list_item.status == 'active')
            
            return {
                'total_lists': len(shopping_lists),
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
            
            # Create session in Firebase
            success = self.firebase.create_user_session(user.user_id, session_id, expiry)
            
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