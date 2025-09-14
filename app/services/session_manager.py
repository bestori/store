"""
Session management service for handling user sessions and cleanup.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import threading
import time

from app.services.database_service import DatabaseService
from app.models.user import User

logger = logging.getLogger(__name__)


class SessionManager:
    """Service for managing user sessions and periodic cleanup."""
    
    def __init__(self, database_service: DatabaseService, cleanup_interval: int = 3600):
        """
        Initialize session manager.
        
        Args:
            database_service: Database service instance
            cleanup_interval: Cleanup interval in seconds (default: 1 hour)
        """
        self.db = database_service
        self.cleanup_interval = cleanup_interval
        self.cleanup_thread = None
        self._stop_cleanup = False
        self.logger = logging.getLogger(__name__)
        
        # Start cleanup thread
        self.start_cleanup_thread()
    
    def start_cleanup_thread(self):
        """Start the cleanup thread."""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self._stop_cleanup = False
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()
            self.logger.info("Session cleanup thread started")
    
    def stop_cleanup_thread(self):
        """Stop the cleanup thread."""
        self._stop_cleanup = True
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        self.logger.info("Session cleanup thread stopped")
    
    def _cleanup_loop(self):
        """Main cleanup loop."""
        while not self._stop_cleanup:
            try:
                self.cleanup_expired_sessions()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        try:
            # Delete expired sessions
            result = self.db.execute_update(
                """DELETE FROM user_sessions 
                   WHERE expires_at < :now""",
                {'now': datetime.now(timezone.utc)}
            )
            
            if result:
                self.logger.info("Cleaned up expired sessions")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired sessions: {str(e)}")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        try:
            result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM user_sessions WHERE expires_at > :now",
                {'now': datetime.now(timezone.utc)}
            )
            return result[0]['count'] if result else 0
        except Exception as e:
            self.logger.error(f"Error getting active sessions count: {str(e)}")
            return 0
    
    def get_user_sessions(self, user_id: str) -> List[dict]:
        """Get all sessions for a user."""
        try:
            sessions = self.db.execute_query(
                """SELECT session_id, created_at, expires_at, last_activity 
                   FROM user_sessions 
                   WHERE user_id = :user_id AND expires_at > :now
                   ORDER BY last_activity DESC""",
                {'user_id': user_id, 'now': datetime.now(timezone.utc)}
            )
            return sessions or []
        except Exception as e:
            self.logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    def cleanup_user_sessions(self, user_id: str, keep_latest: int = 5):
        """Clean up old sessions for a user, keeping only the latest ones."""
        try:
            # Get sessions to delete (keep only the latest ones)
            sessions_to_delete = self.db.execute_query(
                """SELECT session_id FROM user_sessions 
                   WHERE user_id = :user_id 
                   ORDER BY last_activity DESC 
                   OFFSET :keep_count""",
                {'user_id': user_id, 'keep_count': keep_latest}
            )
            
            if sessions_to_delete:
                session_ids = [s['session_id'] for s in sessions_to_delete]
                placeholders = ','.join([f':id_{i}' for i in range(len(session_ids))])
                
                self.db.execute_update(
                    f"DELETE FROM user_sessions WHERE session_id IN ({placeholders})",
                    {f'id_{i}': sid for i, sid in enumerate(session_ids)}
                )
                
                self.logger.info(f"Cleaned up {len(session_ids)} old sessions for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up user sessions: {str(e)}")
    
    def update_session_activity(self, session_id: str):
        """Update last activity timestamp for a session."""
        try:
            self.db.execute_update(
                """UPDATE user_sessions 
                   SET last_activity = :now 
                   WHERE session_id = :session_id""",
                {'now': datetime.now(timezone.utc), 'session_id': session_id}
            )
        except Exception as e:
            self.logger.error(f"Error updating session activity: {str(e)}")
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data by session ID."""
        try:
            result = self.db.execute_query(
                """SELECT session_id, user_id, created_at, expires_at, last_activity 
                   FROM user_sessions 
                   WHERE session_id = :session_id AND expires_at > :now""",
                {'session_id': session_id, 'now': datetime.now(timezone.utc)}
            )
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting session: {str(e)}")
            return None
    
    def cleanup_old_activities(self, days: int = 30):
        """Clean up old user activities."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = self.db.execute_update(
                "DELETE FROM user_activities WHERE created_at < :cutoff_date",
                {'cutoff_date': cutoff_date}
            )
            
            if result:
                self.logger.info(f"Cleaned up activities older than {days} days")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old activities: {str(e)}")
    
    def get_statistics(self) -> dict:
        """Get session manager statistics."""
        try:
            stats = {}
            
            # Get user count
            user_result = self.db.execute_query("SELECT COUNT(*) as count FROM users")
            stats['total_users'] = user_result[0]['count'] if user_result else 0
            
            # Get shopping list count
            list_result = self.db.execute_query("SELECT COUNT(*) as count FROM shopping_lists")
            stats['total_shopping_lists'] = list_result[0]['count'] if list_result else 0
            
            # Get active sessions count
            stats['active_sessions'] = self.get_active_sessions_count()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {str(e)}")
            return {}