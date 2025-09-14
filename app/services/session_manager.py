"""
Session management service for handling user sessions and cleanup.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import threading
import time

from .firebase_service import FirebaseService
from ..models.user import User

logger = logging.getLogger(__name__)


class SessionManager:
    """Service for managing user sessions and periodic cleanup."""
    
    def __init__(self, firebase_service: FirebaseService, cleanup_interval: int = 3600):
        """
        Initialize session manager.
        
        Args:
            firebase_service: Firebase service instance
            cleanup_interval: Cleanup interval in seconds (default: 1 hour)
        """
        self.firebase_service = firebase_service
        self.cleanup_interval = cleanup_interval
        self.cleanup_thread = None
        self.running = False
    
    def start_cleanup_task(self):
        """Start the background cleanup task."""
        if self.running:
            return
        
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info(f"Session cleanup task started with {self.cleanup_interval}s interval")
    
    def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        logger.info("Session cleanup task stopped")
    
    def _cleanup_loop(self):
        """Background loop for periodic session cleanup."""
        while self.running:
            try:
                self.cleanup_expired_sessions()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying on error
    
    def cleanup_expired_sessions(self):
        """Clean up expired user sessions."""
        try:
            if self.firebase_service.is_mock_mode:
                logger.debug("Session cleanup skipped - mock mode")
                return
            
            # Calculate expiration threshold (24 hours by default)
            expiration_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Get expired sessions
            expired_sessions = self.firebase_service.get_collection_query(
                'user_sessions',
                [('last_activity', '<', expiration_threshold)],
                limit=100
            )
            
            if not expired_sessions:
                logger.debug("No expired sessions found")
                return
            
            # Delete expired sessions
            deleted_count = 0
            for session_data in expired_sessions:
                try:
                    session_id = session_data.get('session_id')
                    user_code = session_data.get('user_code', 'unknown')
                    
                    if session_id:
                        self.firebase_service.delete_document('user_sessions', session_id)
                        deleted_count += 1
                        logger.debug(f"Deleted expired session for user {user_code}")
                        
                except Exception as e:
                    logger.error(f"Error deleting session: {str(e)}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions")
                
        except Exception as e:
            logger.error(f"Error in session cleanup: {str(e)}")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active user sessions."""
        try:
            if self.firebase_service.is_mock_mode:
                return 0
            
            # Get sessions active in last 24 hours
            active_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
            active_sessions = self.firebase_service.get_collection_query(
                'user_sessions',
                [('last_activity', '>=', active_threshold)],
                count_only=True
            )
            
            return len(active_sessions) if isinstance(active_sessions, list) else active_sessions
            
        except Exception as e:
            logger.error(f"Error getting active sessions count: {str(e)}")
            return 0
    
    def get_user_active_sessions(self, user_id: str) -> List[dict]:
        """
        Get active sessions for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active session data
        """
        try:
            if self.firebase_service.is_mock_mode:
                return []
            
            # Get sessions for user active in last 24 hours
            active_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
            user_sessions = self.firebase_service.get_collection_query(
                'user_sessions',
                [
                    ('user_id', '==', user_id),
                    ('last_activity', '>=', active_threshold)
                ]
            )
            
            return user_sessions or []
            
        except Exception as e:
            logger.error(f"Error getting user active sessions: {str(e)}")
            return []
    
    def invalidate_user_sessions(self, user_id: str, except_session_id: Optional[str] = None):
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            except_session_id: Optional session ID to keep active
        """
        try:
            if self.firebase_service.is_mock_mode:
                logger.debug(f"Session invalidation skipped for user {user_id} - mock mode")
                return
            
            # Get all user sessions
            user_sessions = self.firebase_service.get_collection_query(
                'user_sessions',
                [('user_id', '==', user_id)]
            )
            
            invalidated_count = 0
            for session_data in user_sessions:
                session_id = session_data.get('session_id')
                
                if session_id and session_id != except_session_id:
                    self.firebase_service.delete_document('user_sessions', session_id)
                    invalidated_count += 1
            
            logger.info(f"Invalidated {invalidated_count} sessions for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating user sessions: {str(e)}")
    
    def update_session_activity(self, session_id: str):
        """
        Update session last activity timestamp.
        
        Args:
            session_id: Session ID to update
        """
        try:
            if self.firebase_service.is_mock_mode:
                return
            
            self.firebase_service.update_document('user_sessions', session_id, {
                'last_activity': datetime.now(timezone.utc)
            })
            
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """
        Get session information.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found
        """
        try:
            if self.firebase_service.is_mock_mode:
                return None
            
            session_data = self.firebase_service.get_document('user_sessions', session_id)
            return session_data
            
        except Exception as e:
            logger.error(f"Error getting session info: {str(e)}")
            return None
    
    def cleanup_old_activities(self, days_to_keep: int = 30):
        """
        Clean up old user activity records.
        
        Args:
            days_to_keep: Number of days of activity to keep
        """
        try:
            if self.firebase_service.is_mock_mode:
                logger.debug("Activity cleanup skipped - mock mode")
                return
            
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Get old activities
            old_activities = self.firebase_service.get_collection_query(
                'user_activities',
                [('timestamp', '<', cutoff_date)],
                limit=500  # Process in batches
            )
            
            if not old_activities:
                logger.debug("No old activities found")
                return
            
            # Delete old activities
            deleted_count = 0
            for activity_data in old_activities:
                try:
                    activity_id = activity_data.get('id') or activity_data.get('_id')
                    if activity_id:
                        self.firebase_service.delete_document('user_activities', activity_id)
                        deleted_count += 1
                        
                except Exception as e:
                    logger.error(f"Error deleting activity: {str(e)}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old activity records")
                
        except Exception as e:
            logger.error(f"Error in activity cleanup: {str(e)}")
    
    def get_system_stats(self) -> dict:
        """
        Get system statistics.
        
        Returns:
            Dictionary with system stats
        """
        try:
            stats = {
                'active_sessions': self.get_active_sessions_count(),
                'cleanup_running': self.running,
                'last_cleanup': datetime.now(timezone.utc).isoformat()
            }
            
            if not self.firebase_service.is_mock_mode:
                # Get total users count
                users = self.firebase_service.get_collection_query('users', [], count_only=True)
                stats['total_users'] = len(users) if isinstance(users, list) else users
                
                # Get total shopping lists count
                lists = self.firebase_service.get_collection_query('shopping_lists', [], count_only=True)
                stats['total_lists'] = len(lists) if isinstance(lists, list) else lists
            else:
                stats['total_users'] = 0
                stats['total_lists'] = 0
                stats['mock_mode'] = True
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}")
            return {
                'active_sessions': 0,
                'cleanup_running': self.running,
                'error': str(e)
            }