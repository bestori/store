"""
Flask routes for the Cable Tray Online Store application.
"""

# Import all route blueprints
from .main import main_bp
from .auth import auth_bp
from .search import search_bp
from .shopping_list import shopping_list_bp
from .api import api_bp

__all__ = [
    'main_bp',
    'auth_bp', 
    'search_bp',
    'shopping_list_bp',
    'api_bp'
]