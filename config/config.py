"""
Configuration settings for the Cable Tray Online Store application.
"""

import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.absolute()


class Config:
    """Base configuration."""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cable-tray-dev-key-change-in-production'
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = BASE_DIR / 'data' / 'sessions'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Excel Files Configuration
    EXCEL_DATA_DIR = BASE_DIR / 'data' / 'excel_files'
    SHOPPING_LIST_FILE = 'NEW Shopping list test.xlsm'
    PRICE_TABLE_FILE = 'טבלת מחירים ורד 01092025.xlsx'
    
    # Database Configuration
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'your_secure_password_here')
    DB_NAME = os.environ.get('DB_NAME', 'solel-bone')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    CLOUD_SQL_CONNECTION_NAME = os.environ.get('CLOUD_SQL_CONNECTION_NAME', 'solel-bone:europe-west1:solel-bone-db')
    
    # Application Settings
    DEFAULT_LANGUAGE = 'hebrew'
    DEFAULT_CURRENCY = 'ILS'
    RESULTS_PER_PAGE = 20
    MAX_RESULTS_PER_PAGE = 100
    
    # Cache Settings
    EXCEL_CACHE_TIMEOUT = 3600  # 1 hour
    SEARCH_CACHE_TIMEOUT = 300  # 5 minutes
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_DEFAULT = "100 per minute"
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = BASE_DIR / 'logs' / 'app.log'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'
    
    # Shorter cache timeouts for development
    EXCEL_CACHE_TIMEOUT = 60  # 1 minute
    SEARCH_CACHE_TIMEOUT = 30  # 30 seconds


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Production security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    
    # Longer cache timeouts for production
    EXCEL_CACHE_TIMEOUT = 7200  # 2 hours
    SEARCH_CACHE_TIMEOUT = 600   # 10 minutes


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    
    # Use in-memory session for testing
    SESSION_TYPE = 'null'
    
    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False
    
    # Short cache timeouts for testing
    EXCEL_CACHE_TIMEOUT = 1
    SEARCH_CACHE_TIMEOUT = 1


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Get configuration based on environment."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])