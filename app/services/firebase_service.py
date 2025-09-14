"""
Firebase Firestore service for managing user data and shopping lists.

This service handles all interactions with Firebase Firestore for storing
user information, shopping lists, and session management.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import os

# Import Firebase modules (optional import to handle missing dependencies)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    from google.cloud.firestore import Client
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

from app.models.user import User
from app.models.shopping_list import ShoppingList
from app.models.shopping_item import ShoppingItem


class FirebaseService:
    """
    Service for Firebase Firestore operations.
    
    Handles user management, shopping lists, and session data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Firebase service with configuration.
        
        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._db: Optional[Client] = None
        self._initialized = False
        self._mock_mode = False
        
        # Initialize Firebase if available
        if FIREBASE_AVAILABLE:
            self._initialize_firebase()
        else:
            self.logger.warning("Firebase SDK not available - running in mock mode")
            self._mock_mode = True
    
    def _initialize_firebase(self):
        """Initialize Firebase connection."""
        try:
            # Try multiple credential path sources
            credentials_path = self.config.get('FIREBASE_CREDENTIALS_PATH')
            if not credentials_path:
                # Try looking in the project root
                credentials_path = os.path.join(os.getcwd(), 'firebase-credentials.json')
            
            project_id = self.config.get('FIREBASE_PROJECT_ID')
            
            if not credentials_path or not os.path.exists(credentials_path):
                self.logger.warning(f"Firebase credentials not found at: {credentials_path} - using mock mode")
                self._mock_mode = True
                return
            
            # Initialize Firebase app if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id
                })
            
            # Get Firestore client
            self._db = firestore.client()
            self._initialized = True
            
            self.logger.info(f"Firebase initialized successfully for project: {project_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Firebase: {str(e)}")
            self._initialized = False
            self._mock_mode = True
    
    def is_available(self) -> bool:
        """Check if Firebase is available and initialized."""
        return FIREBASE_AVAILABLE and self._initialized
    
    @property
    def is_mock_mode(self) -> bool:
        """Check if Firebase is running in mock mode."""
        return self._mock_mode
    
    # User Management
    
    def get_user_by_code(self, user_code: str) -> Optional[User]:
        """
        Get user by user code.
        
        Args:
            user_code: Unique user code
            
        Returns:
            User instance or None if not found
        """
        if not self.is_available():
            return self._mock_get_user_by_code(user_code)
        
        try:
            user_id = f"user_{user_code}"
            doc_ref = self._db.collection('users').document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                user_data = doc.to_dict()
                return User.from_dict(user_data)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting user {user_code}: {str(e)}")
            return None
    
    def create_user(self, user_code: str) -> Optional[User]:
        """
        Create a new user.
        
        Args:
            user_code: Unique user code
            
        Returns:
            Created User instance or None if failed
        """
        if not self.is_available():
            return self._mock_create_user(user_code)
        
        try:
            user = User.create_new_user(user_code)
            user_data = user.to_dict()
            
            doc_ref = self._db.collection('users').document(user.user_id)
            doc_ref.set(user_data)
            
            self.logger.info(f"Created new user: {user_code}")
            return user
            
        except Exception as e:
            self.logger.error(f"Error creating user {user_code}: {str(e)}")
            return None
    
    def update_user(self, user: User) -> bool:
        """
        Update user information.
        
        Args:
            user: User instance to update
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return self._mock_update_user(user)
        
        try:
            user_data = user.to_dict()
            doc_ref = self._db.collection('users').document(user.user_id)
            doc_ref.set(user_data, merge=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating user {user.user_code}: {str(e)}")
            return False
    
    # Shopping List Management
    
    def get_shopping_lists_by_user(self, user_id: str) -> List[ShoppingList]:
        """
        Get all shopping lists for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of shopping lists
        """
        if not self.is_available():
            return self._mock_get_shopping_lists_by_user(user_id)
        
        try:
            query = self._db.collection('shopping_lists').where('userId', '==', user_id)
            docs = query.get()
            
            shopping_lists = []
            for doc in docs:
                list_data = doc.to_dict()
                shopping_list = ShoppingList.from_dict(list_data)
                shopping_lists.append(shopping_list)
            
            return shopping_lists
            
        except Exception as e:
            self.logger.error(f"Error getting shopping lists for user {user_id}: {str(e)}")
            return []
    
    def get_shopping_list(self, list_id: str) -> Optional[ShoppingList]:
        """
        Get shopping list by ID.
        
        Args:
            list_id: Shopping list ID
            
        Returns:
            ShoppingList instance or None if not found
        """
        if not self.is_available():
            return self._mock_get_shopping_list(list_id)
        
        try:
            doc_ref = self._db.collection('shopping_lists').document(list_id)
            doc = doc_ref.get()
            
            if doc.exists:
                list_data = doc.to_dict()
                return ShoppingList.from_dict(list_data)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting shopping list {list_id}: {str(e)}")
            return None
    
    def save_shopping_list(self, shopping_list: ShoppingList) -> bool:
        """
        Save shopping list to Firebase.
        
        Args:
            shopping_list: ShoppingList instance to save
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return self._mock_save_shopping_list(shopping_list)
        
        try:
            list_data = shopping_list.to_dict()
            doc_ref = self._db.collection('shopping_lists').document(shopping_list.list_id)
            doc_ref.set(list_data)
            
            self.logger.debug(f"Saved shopping list: {shopping_list.list_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving shopping list {shopping_list.list_id}: {str(e)}")
            return False
    
    def delete_shopping_list(self, list_id: str) -> bool:
        """
        Delete shopping list.
        
        Args:
            list_id: Shopping list ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return self._mock_delete_shopping_list(list_id)
        
        try:
            doc_ref = self._db.collection('shopping_lists').document(list_id)
            doc_ref.delete()
            
            self.logger.info(f"Deleted shopping list: {list_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting shopping list {list_id}: {str(e)}")
            return False
    
    # User Session Management
    
    def create_user_session(self, user_id: str, session_id: str, expiry: datetime) -> bool:
        """
        Create user session record.
        
        Args:
            user_id: User ID
            session_id: Session ID
            expiry: Session expiry datetime
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return True  # Mock always succeeds
        
        try:
            session_data = {
                'userId': user_id,
                'sessionId': session_id,
                'expiresAt': expiry,
                'createdAt': datetime.now(timezone.utc),
                'active': True
            }
            
            doc_ref = self._db.collection('user_sessions').document(session_id)
            doc_ref.set(session_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating session {session_id}: {str(e)}")
            return False
    
    def validate_session(self, session_id: str) -> Optional[str]:
        """
        Validate session and return user ID if valid.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            User ID if session is valid, None otherwise
        """
        if not self.is_available():
            return f"user_mock"  # Mock validation
        
        try:
            doc_ref = self._db.collection('user_sessions').document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                session_data = doc.to_dict()
                
                # Check if session is active and not expired
                if (session_data.get('active', False) and
                    session_data.get('expiresAt') > datetime.now(timezone.utc)):
                    
                    return session_data.get('userId')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error validating session {session_id}: {str(e)}")
            return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate user session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return True  # Mock always succeeds
        
        try:
            doc_ref = self._db.collection('user_sessions').document(session_id)
            doc_ref.update({'active': False})
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error invalidating session {session_id}: {str(e)}")
            return False
    
    # Mock methods for when Firebase is not available
    
    def _mock_get_user_by_code(self, user_code: str) -> Optional[User]:
        """Mock implementation for getting user."""
        self.logger.debug(f"Mock: Getting user {user_code}")
        # Return None to simulate user not found (will trigger creation)
        return None
    
    def _mock_create_user(self, user_code: str) -> Optional[User]:
        """Mock implementation for creating user."""
        self.logger.debug(f"Mock: Creating user {user_code}")
        return User.create_new_user(user_code)
    
    def _mock_update_user(self, user: User) -> bool:
        """Mock implementation for updating user."""
        self.logger.debug(f"Mock: Updating user {user.user_code}")
        return True
    
    def _mock_get_shopping_lists_by_user(self, user_id: str) -> List[ShoppingList]:
        """Mock implementation for getting shopping lists."""
        self.logger.debug(f"Mock: Getting shopping lists for user {user_id}")
        return []
    
    def _mock_get_shopping_list(self, list_id: str) -> Optional[ShoppingList]:
        """Mock implementation for getting shopping list."""
        self.logger.debug(f"Mock: Getting shopping list {list_id}")
        return None
    
    def _mock_save_shopping_list(self, shopping_list: ShoppingList) -> bool:
        """Mock implementation for saving shopping list."""
        self.logger.debug(f"Mock: Saving shopping list {shopping_list.list_id}")
        return True
    
    def _mock_delete_shopping_list(self, list_id: str) -> bool:
        """Mock implementation for deleting shopping list."""
        self.logger.debug(f"Mock: Deleting shopping list {list_id}")
        return True
    
    # Statistics and Analytics
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics."""
        if not self.is_available():
            return {
                'total_users': 1,
                'active_users': 1,
                'new_users_today': 0
            }
        
        try:
            # This would require more complex queries in production
            users_collection = self._db.collection('users')
            total_users = len(list(users_collection.get()))
            
            return {
                'total_users': total_users,
                'active_users': total_users,  # Simplified
                'new_users_today': 0  # Would need date filtering
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user statistics: {str(e)}")
            return {'total_users': 0, 'active_users': 0, 'new_users_today': 0}
    
    def get_shopping_list_statistics(self) -> Dict[str, Any]:
        """Get shopping list statistics."""
        if not self.is_available():
            return {
                'total_lists': 0,
                'active_lists': 0,
                'completed_lists': 0
            }
        
        try:
            lists_collection = self._db.collection('shopping_lists')
            all_lists = list(lists_collection.get())
            
            total_lists = len(all_lists)
            active_lists = sum(1 for doc in all_lists if doc.to_dict().get('status') == 'active')
            completed_lists = sum(1 for doc in all_lists if doc.to_dict().get('status') == 'completed')
            
            return {
                'total_lists': total_lists,
                'active_lists': active_lists,
                'completed_lists': completed_lists
            }
            
        except Exception as e:
            self.logger.error(f"Error getting shopping list statistics: {str(e)}")
            return {'total_lists': 0, 'active_lists': 0, 'completed_lists': 0}
    
    def get_collection_query(self, collection_name: str, filters: List = None, count_only: bool = False, limit: int = None) -> List[Dict[str, Any]]:
        """
        Execute a query on a Firestore collection with optional filters.
        
        Args:
            collection_name: Name of the collection
            filters: List of filter tuples (field, operator, value)
            count_only: If True, return count instead of documents
            limit: Maximum number of documents to return
            
        Returns:
            List of documents or count
        """
        if self.is_mock_mode:
            # Return empty results in mock mode
            return [] if not count_only else 0
            
        if not self.is_available():
            return [] if not count_only else 0
        
        try:
            collection_ref = self._db.collection(collection_name)
            query = collection_ref
            
            # Apply filters if provided
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            # Apply limit if provided
            if limit:
                query = query.limit(limit)
            
            # Execute query
            results = query.get()
            documents = [doc.to_dict() for doc in results]
            
            return len(documents) if count_only else documents
            
        except Exception as e:
            self.logger.error(f"Error querying collection {collection_name}: {str(e)}")
            return [] if not count_only else 0