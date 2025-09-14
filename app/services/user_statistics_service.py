"""
User statistics service for calculating and managing user activity statistics.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from app.services.database_service import DatabaseService
from app.models.user import User
from app.models.shopping_list import ShoppingList

logger = logging.getLogger(__name__)


@dataclass
class UserStatistics:
    """User activity statistics - simplified to exact requirements."""
    total_lists: int = 0      # Total shopping lists
    total_items: int = 0      # Total items across all lists  
    total_searches: int = 0   # Total searches performed
    total_value: float = 0.0  # Total value of all lists
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_lists': self.total_lists,
            'total_items': self.total_items,
            'total_searches': self.total_searches,
            'total_value': self.total_value
        }


class UserStatisticsService:
    """Service for calculating and managing user activity statistics."""
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize user statistics service.
        
        Args:
            database_service: Database service instance
        """
        self.db = database_service
        self.logger = logging.getLogger(__name__)
    
    def calculate_user_statistics(self, user: User) -> UserStatistics:
        """
        Calculate comprehensive statistics for a user.
        
        Args:
            user: User instance
            
        Returns:
            UserStatistics instance
        """
        try:
            stats = UserStatistics()
            
            # Get shopping list statistics
            list_stats = self._get_shopping_list_stats(user.user_id)
            stats.total_lists = list_stats['total_lists']
            stats.total_items = list_stats['total_items']
            stats.total_value = list_stats['total_value']
            
            # Get search statistics
            search_stats = self._get_search_stats(user.user_id)
            stats.total_searches = search_stats['total_searches']
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating user statistics: {str(e)}")
            return UserStatistics()
    
    def _get_shopping_list_stats(self, user_id: str) -> Dict[str, Any]:
        """Get shopping list statistics for a user."""
        try:
            # Get total lists count
            lists_result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM shopping_lists WHERE user_id = :user_id",
                {'user_id': user_id}
            )
            total_lists = lists_result[0]['count'] if lists_result else 0
            
            # Get total items and value
            items_result = self.db.execute_query(
                """SELECT 
                       COUNT(*) as total_items,
                       COALESCE(SUM(total_price), 0) as total_value
                   FROM shopping_lists 
                   WHERE user_id = :user_id""",
                {'user_id': user_id}
            )
            
            if items_result:
                total_items = items_result[0]['total_items'] or 0
                total_value = float(items_result[0]['total_value'] or 0)
            else:
                total_items = 0
                total_value = 0.0
            
            return {
                'total_lists': total_lists,
                'total_items': total_items,
                'total_value': total_value
            }
            
        except Exception as e:
            self.logger.error(f"Error getting shopping list stats: {str(e)}")
            return {'total_lists': 0, 'total_items': 0, 'total_value': 0.0}
    
    def _get_search_stats(self, user_id: str) -> Dict[str, Any]:
        """Get search statistics for a user."""
        try:
            # Get search count from user activities
            search_result = self.db.execute_query(
                """SELECT COUNT(*) as count 
                   FROM user_activities 
                   WHERE user_id = :user_id AND activity_type = 'search'""",
                {'user_id': user_id}
            )
            
            total_searches = search_result[0]['count'] if search_result else 0
            
            return {'total_searches': total_searches}
            
        except Exception as e:
            self.logger.error(f"Error getting search stats: {str(e)}")
            return {'total_searches': 0}
    
    def record_user_activity(self, user_id: str, activity_type: str, 
                           details: Optional[Dict[str, Any]] = None):
        """
        Record user activity for statistics.
        
        Args:
            user_id: User ID
            activity_type: Type of activity (search, list_created, etc.)
            details: Optional activity details
        """
        try:
            activity_data = {
                'user_id': user_id,
                'activity_type': activity_type,
                'details': details or {},
                'created_at': datetime.now(timezone.utc)
            }
            
            self.db.execute_update(
                """INSERT INTO user_activities (user_id, activity_type, details, created_at)
                   VALUES (:user_id, :activity_type, :details, :created_at)""",
                activity_data
            )
            
        except Exception as e:
            self.logger.error(f"Error recording user activity: {str(e)}")
    
    def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get user activity summary for the last N days.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Dictionary with activity summary
        """
        try:
            cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            # Get activity counts by type
            activities_result = self.db.execute_query(
                """SELECT activity_type, COUNT(*) as count
                   FROM user_activities 
                   WHERE user_id = :user_id AND created_at >= :cutoff_date
                   GROUP BY activity_type""",
                {'user_id': user_id, 'cutoff_date': cutoff_date}
            )
            
            activity_summary = {}
            for activity in activities_result:
                activity_summary[activity['activity_type']] = activity['count']
            
            return activity_summary
            
        except Exception as e:
            self.logger.error(f"Error getting user activity summary: {str(e)}")
            return {}
    
    def get_top_searched_products(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most searched products by a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            
        Returns:
            List of product search data
        """
        try:
            # Get search activities with product details
            searches_result = self.db.execute_query(
                """SELECT details->>'query' as query, COUNT(*) as count
                   FROM user_activities 
                   WHERE user_id = :user_id 
                     AND activity_type = 'search'
                     AND details->>'query' IS NOT NULL
                   GROUP BY details->>'query'
                   ORDER BY count DESC
                   LIMIT :limit""",
                {'user_id': user_id, 'limit': limit}
            )
            
            return searches_result or []
            
        except Exception as e:
            self.logger.error(f"Error getting top searched products: {str(e)}")
            return []
    
    def cleanup_old_activities(self, days: int = 90):
        """
        Clean up old user activities.
        
        Args:
            days: Number of days to keep activities
        """
        try:
            cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            result = self.db.execute_update(
                "DELETE FROM user_activities WHERE created_at < :cutoff_date",
                {'cutoff_date': cutoff_date}
            )
            
            if result:
                self.logger.info(f"Cleaned up activities older than {days} days")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old activities: {str(e)}")
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """
        Get global statistics across all users.
        
        Returns:
            Dictionary with global statistics
        """
        try:
            stats = {}
            
            # Get total users
            users_result = self.db.execute_query("SELECT COUNT(*) as count FROM users")
            stats['total_users'] = users_result[0]['count'] if users_result else 0
            
            # Get total shopping lists
            lists_result = self.db.execute_query("SELECT COUNT(*) as count FROM shopping_lists")
            stats['total_shopping_lists'] = lists_result[0]['count'] if lists_result else 0
            
            # Get total searches
            searches_result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM user_activities WHERE activity_type = 'search'"
            )
            stats['total_searches'] = searches_result[0]['count'] if searches_result else 0
            
            # Get total value
            value_result = self.db.execute_query(
                "SELECT COALESCE(SUM(total_price), 0) as total_value FROM shopping_lists"
            )
            stats['total_value'] = float(value_result[0]['total_value'] or 0) if value_result else 0.0
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting global statistics: {str(e)}")
            return {}