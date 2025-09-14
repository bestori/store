"""
User statistics service for calculating and managing user activity statistics.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from .firebase_service import FirebaseService
from ..models.user import User
from ..models.shopping_list import ShoppingList

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
            'total_value': round(self.total_value, 2)
        }


@dataclass
class ActivityEntry:
    """User activity entry."""
    type: str  # 'list_created', 'item_added', 'search', 'list_exported', etc.
    description: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }


class UserStatisticsService:
    """Service for managing user statistics and activity tracking."""
    
    def __init__(self, firebase_service: FirebaseService):
        """
        Initialize user statistics service.
        
        Args:
            firebase_service: Firebase service instance
        """
        self.firebase_service = firebase_service
    
    def calculate_user_statistics(self, user: User, shopping_lists: List[ShoppingList]) -> UserStatistics:
        """
        Calculate user statistics - exact requirements: total lists, items, searches, value.
        
        Args:
            user: User instance
            shopping_lists: List of user's shopping lists
            
        Returns:
            UserStatistics instance
        """
        try:
            # Total lists
            total_lists = len(shopping_lists)
            
            # Total items across all lists
            total_items = sum(shopping_list.get_item_count() for shopping_list in shopping_lists)
            
            # Total value of all lists
            total_value = sum(shopping_list.get_total_value() for shopping_list in shopping_lists)
            
            # Total searches performed
            total_searches = self._get_user_search_count(user.user_id)
            
            return UserStatistics(
                total_lists=total_lists,
                total_items=total_items,
                total_searches=total_searches,
                total_value=total_value
            )
            
        except Exception as e:
            logger.error(f"Error calculating user statistics: {str(e)}")
            return UserStatistics()
    
    def get_recent_activity(self, user_id: str, limit: int = 10) -> List[ActivityEntry]:
        """
        Get recent user activity.
        
        Args:
            user_id: User ID
            limit: Maximum number of activities to return
            
        Returns:
            List of recent ActivityEntry instances
        """
        try:
            if self.firebase_service.is_mock_mode:
                # Return mock activity data for development
                return self._get_mock_recent_activity(limit)
            
            # Get from Firebase
            activities_data = self.firebase_service.get_collection_query(
                'user_activities',
                [('user_id', '==', user_id)],
                order_by=[('timestamp', 'desc')],
                limit=limit
            )
            
            activities = []
            for activity_data in activities_data:
                timestamp = activity_data.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif timestamp:
                    # Firestore timestamp
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                activities.append(ActivityEntry(
                    type=activity_data.get('type', 'unknown'),
                    description=activity_data.get('description', ''),
                    timestamp=timestamp or datetime.now(timezone.utc),
                    metadata=activity_data.get('metadata')
                ))
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {str(e)}")
            return []
    
    def log_activity(self, user_id: str, activity_type: str, description: str, 
                    metadata: Optional[Dict[str, Any]] = None):
        """
        Log user activity.
        
        Args:
            user_id: User ID
            activity_type: Type of activity
            description: Human-readable description
            metadata: Optional additional data
        """
        try:
            if self.firebase_service.is_mock_mode:
                # In mock mode, just log locally
                logger.info(f"Activity logged for user {user_id}: {activity_type} - {description}")
                return
            
            activity_data = {
                'user_id': user_id,
                'type': activity_type,
                'description': description,
                'timestamp': datetime.now(timezone.utc),
                'metadata': metadata or {}
            }
            
            # Save to Firebase
            self.firebase_service.add_document('user_activities', activity_data)
            
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
    
    def _get_user_search_count(self, user_id: str) -> int:
        """Get total search count for user."""
        try:
            if self.firebase_service.is_mock_mode:
                # Return mock data
                return 42
            
            # Count search activities
            search_activities = self.firebase_service.get_collection_query(
                'user_activities',
                [('user_id', '==', user_id), ('type', '==', 'search')],
                count_only=True
            )
            
            return len(search_activities) if isinstance(search_activities, list) else search_activities
            
        except Exception as e:
            logger.error(f"Error getting search count: {str(e)}")
            return 0
    
    def _get_mock_recent_activity(self, limit: int) -> List[ActivityEntry]:
        """Generate mock recent activity for development."""
        import random
        from datetime import timedelta
        
        activity_types = [
            ('list_created', 'Created new shopping list "{}"'),
            ('item_added', 'Added {} items to shopping list'),
            ('search', 'Searched for "{}" products'),
            ('list_exported', 'Exported shopping list to HTML'),
            ('list_updated', 'Updated shopping list "{}"')
        ]
        
        mock_activities = []
        now = datetime.now(timezone.utc)
        
        for i in range(min(limit, 8)):
            activity_type, description_template = random.choice(activity_types)
            
            # Generate mock description based on type
            if activity_type == 'list_created':
                description = description_template.format(f"Project List {i+1}")
            elif activity_type == 'item_added':
                description = description_template.format(random.randint(1, 5))
            elif activity_type == 'search':
                search_terms = ['cable tray', 'galvanized', '100mm', 'ladder type', 'perforated']
                description = description_template.format(random.choice(search_terms))
            elif activity_type == 'list_exported':
                description = description_template
            else:
                description = description_template.format(f"List {i+1}")
            
            # Generate timestamp (random within last 30 days)
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            timestamp = now - timedelta(days=days_ago, hours=hours_ago)
            
            mock_activities.append(ActivityEntry(
                type=activity_type,
                description=description,
                timestamp=timestamp
            ))
        
        # Sort by timestamp descending
        mock_activities.sort(key=lambda x: x.timestamp, reverse=True)
        
        return mock_activities
    
    def update_user_last_activity(self, user_id: str):
        """Update user's last activity timestamp."""
        try:
            if not self.firebase_service.is_mock_mode:
                self.firebase_service.update_document('users', user_id, {
                    'last_activity': datetime.now(timezone.utc)
                })
        except Exception as e:
            logger.error(f"Error updating last activity: {str(e)}")