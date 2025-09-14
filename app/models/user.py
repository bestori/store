"""
User model for managing user authentication and preferences.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid


@dataclass
class UserStats:
    """User usage statistics."""
    total_lists: int = 0
    total_items: int = 0
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'totalLists': self.total_lists,
            'totalItems': self.total_items,
            'lastLoginAt': self.last_login_at.isoformat() if self.last_login_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class User:
    """
    User model for managing user authentication and data.
    
    Users are identified by unique login codes without traditional registration.
    """
    
    # User identification
    user_id: str
    user_code: str
    display_name: Optional[str] = None
    
    # User preferences
    preferred_language: str = 'hebrew'
    default_currency: str = 'ILS'
    
    # Shopping lists references
    active_lists: Optional[List[str]] = None
    default_list_id: Optional[str] = None
    
    # Usage statistics
    stats: Optional[UserStats] = None
    
    # Session management
    current_session: Optional[str] = None
    session_expiry: Optional[datetime] = None
    
    # Metadata
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.display_name is None:
            self.display_name = self.user_code
        
        if self.active_lists is None:
            self.active_lists = []
        
        if self.stats is None:
            self.stats = UserStats()
        
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid."""
        if not self.current_session or not self.session_expiry:
            return False
        
        return datetime.now(timezone.utc) < self.session_expiry
    
    def create_new_session(self, expiry_hours: int = 8) -> str:
        """
        Create a new session for the user.
        
        Args:
            expiry_hours: Session expiry time in hours
            
        Returns:
            Session ID
        """
        from datetime import timedelta
        
        self.current_session = str(uuid.uuid4())
        self.session_expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        self.updated_at = datetime.now(timezone.utc)
        
        # Update last login
        if self.stats:
            self.stats.last_login_at = datetime.now(timezone.utc)
        
        return self.current_session
    
    def invalidate_session(self):
        """Invalidate current session."""
        self.current_session = None
        self.session_expiry = None
        self.updated_at = datetime.now(timezone.utc)
    
    def add_shopping_list(self, list_id: str, set_as_default: bool = False):
        """
        Add a shopping list to user's active lists.
        
        Args:
            list_id: Shopping list ID
            set_as_default: Whether to set as default list
        """
        if list_id not in self.active_lists:
            self.active_lists.append(list_id)
        
        if set_as_default or not self.default_list_id:
            self.default_list_id = list_id
        
        # Update stats
        if self.stats:
            self.stats.total_lists = len(self.active_lists)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_shopping_list(self, list_id: str):
        """
        Remove a shopping list from user's active lists.
        
        Args:
            list_id: Shopping list ID to remove
        """
        if list_id in self.active_lists:
            self.active_lists.remove(list_id)
        
        # If this was the default list, set a new default
        if self.default_list_id == list_id:
            self.default_list_id = self.active_lists[0] if self.active_lists else None
        
        # Update stats
        if self.stats:
            self.stats.total_lists = len(self.active_lists)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def update_item_count(self, total_items: int):
        """Update total items count in user stats."""
        if self.stats:
            self.stats.total_items = total_items
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary format for storage."""
        return {
            'userId': self.user_id,
            'userCode': self.user_code,
            'displayName': self.display_name,
            'preferredLanguage': self.preferred_language,
            'defaultCurrency': self.default_currency,
            'activeLists': self.active_lists,
            'defaultListId': self.default_list_id,
            'stats': self.stats.to_dict() if self.stats else None,
            'currentSession': self.current_session,
            'sessionExpiry': self.session_expiry.isoformat() if self.session_expiry else None,
            'active': self.active,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary format for API responses (excluding sensitive data)."""
        return {
            'userId': self.user_id,
            'userCode': self.user_code,
            'preferredLanguage': self.preferred_language,
            'defaultCurrency': self.default_currency,
            'activeLists': self.active_lists,
            'defaultListId': self.default_list_id,
            'stats': {
                'totalLists': self.stats.total_lists if self.stats else 0,
                'totalItems': self.stats.total_items if self.stats else 0,
                'lastLoginAt': self.stats.last_login_at.isoformat() if self.stats and self.stats.last_login_at else None
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create User instance from dictionary data.
        
        Args:
            data: Dictionary containing user data
            
        Returns:
            User instance
        """
        # Parse datetime fields
        created_at = None
        if data.get('createdAt'):
            created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        
        updated_at = None
        if data.get('updatedAt'):
            updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))
        
        session_expiry = None
        if data.get('sessionExpiry'):
            session_expiry = datetime.fromisoformat(data['sessionExpiry'].replace('Z', '+00:00'))
        
        # Parse stats
        stats = None
        if data.get('stats'):
            stats_data = data['stats']
            last_login = None
            created = None
            
            if stats_data.get('lastLoginAt'):
                last_login = datetime.fromisoformat(stats_data['lastLoginAt'].replace('Z', '+00:00'))
            if stats_data.get('createdAt'):
                created = datetime.fromisoformat(stats_data['createdAt'].replace('Z', '+00:00'))
            
            stats = UserStats(
                total_lists=stats_data.get('totalLists', 0),
                total_items=stats_data.get('totalItems', 0),
                last_login_at=last_login,
                created_at=created
            )
        
        return cls(
            user_id=data.get('userId', ''),
            user_code=data.get('userCode', ''),
            display_name=data.get('displayName'),
            preferred_language=data.get('preferredLanguage', 'hebrew'),
            default_currency=data.get('defaultCurrency', 'ILS'),
            active_lists=data.get('activeLists', []),
            default_list_id=data.get('defaultListId'),
            stats=stats,
            current_session=data.get('currentSession'),
            session_expiry=session_expiry,
            active=data.get('active', True),
            created_at=created_at,
            updated_at=updated_at
        )
    
    @classmethod
    def create_new_user(cls, user_code: str) -> 'User':
        """
        Create a new user with the given code.
        
        Args:
            user_code: Unique user code
            
        Returns:
            New User instance
        """
        user_id = f"user_{user_code}"
        
        return cls(
            user_id=user_id,
            user_code=user_code,
            display_name=user_code
        )