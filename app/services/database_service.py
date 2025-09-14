"""
Database service for Cloud SQL PostgreSQL integration.

This service handles all database operations using SQLAlchemy with PostgreSQL.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for PostgreSQL database operations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize database service with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._engine = None
        self._session_factory = None
        self._initialized = False
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection."""
        try:
            # Check for Railway DATABASE_URL first
            database_url = os.environ.get('DATABASE_URL')
            
            if not database_url:
                # Fallback to individual config variables
                db_user = self.config.get('DB_USER', 'postgres')
                db_password = self.config.get('DB_PASSWORD', 'your_secure_password_here')
                db_name = self.config.get('DB_NAME', 'railway')
                db_host = self.config.get('DB_HOST', 'localhost')
                db_port = self.config.get('DB_PORT', '5432')
                database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            self._engine = create_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False  # Set to True for SQL debugging
            )
            
            self._session_factory = sessionmaker(bind=self._engine)
            self._initialized = True
            
            # Test connection
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                self.logger.info("Database connection successful")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            self._initialized = False
    
    def is_available(self) -> bool:
        """Check if database is available."""
        return self._initialized and self._engine is not None
    
    def get_session(self) -> Session:
        """Get database session."""
        if not self.is_available():
            raise RuntimeError("Database not available")
        return self._session_factory()
    
    def create_tables(self):
        """Create database tables."""
        if not self.is_available():
            return False
        
        try:
            with self._engine.connect() as conn:
                # Create users table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) UNIQUE NOT NULL,
                    user_code VARCHAR(255) UNIQUE NOT NULL,
                    preferences JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """))
                
                # Create products table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    menora_id VARCHAR(255) UNIQUE NOT NULL,
                    name_hebrew VARCHAR(500),
                    name_english VARCHAR(500),
                    description_hebrew TEXT,
                    description_english TEXT,
                    price DECIMAL(10,2),
                    category VARCHAR(255),
                    subcategory VARCHAR(255),
                    specifications JSONB DEFAULT '{}',
                    dimensions JSONB DEFAULT '{}',
                    weight DECIMAL(10,3),
                    material VARCHAR(255),
                    coating VARCHAR(255),
                    standard VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """))
                
                # Create shopping_lists table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS shopping_lists (
                    id SERIAL PRIMARY KEY,
                    list_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    name VARCHAR(500) NOT NULL,
                    status VARCHAR(50) DEFAULT 'active',
                    items JSONB DEFAULT '[]',
                    total_price DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """))
                
                # Create user_sessions table
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """))
                
                # Create indexes for better performance
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_menora_id ON products(menora_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_name_hebrew ON products(name_hebrew)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_products_name_english ON products(name_english)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_user_code ON users(user_code)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_shopping_lists_user_id ON shopping_lists(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id)"))
                
                conn.commit()
                self.logger.info("Database tables created successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create tables: {str(e)}")
            return False
    
    def execute_query(self, query: str, params: dict = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        if not self.is_available():
            return []
        
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            return []
    
    def execute_update(self, query: str, params: dict = None) -> bool:
        """Execute an INSERT/UPDATE/DELETE query."""
        if not self.is_available():
            return False
        
        try:
            with self._engine.connect() as conn:
                conn.execute(text(query), params or {})
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Update execution failed: {str(e)}")
            return False
    
    def get_user_by_code(self, user_code: str) -> Optional[Dict[str, Any]]:
        """Get user by user code."""
        results = self.execute_query(
            """SELECT 
                user_id as "userId",
                user_code as "userCode", 
                preferences,
                created_at as "createdAt",
                updated_at as "updatedAt",
                last_activity as "lastActivity"
               FROM users WHERE user_code = :user_code""",
            {"user_code": user_code}
        )
        return results[0] if results else None
    
    def create_user(self, user_code: str) -> bool:
        """Create a new user."""
        user_id = f"user_{user_code}"
        return self.execute_update(
            """INSERT INTO users (user_id, user_code, preferences) 
               VALUES (:user_id, :user_code, '{}')""",
            {"user_id": user_id, "user_code": user_code}
        )
    
    def get_products_count(self) -> int:
        """Get total number of products."""
        results = self.execute_query("SELECT COUNT(*) as count FROM products")
        return results[0]["count"] if results else 0
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products."""
        return self.execute_query("SELECT * FROM products ORDER BY name_hebrew")
    
    def insert_product(self, product_data: Dict[str, Any]) -> bool:
        """Insert a product into the database."""
        import json
        
        # Convert dict fields to JSON strings for PostgreSQL
        processed_data = product_data.copy()
        
        # Convert specifications dict to JSON string
        if 'specifications' in processed_data and isinstance(processed_data['specifications'], dict):
            processed_data['specifications'] = json.dumps(processed_data['specifications'])
        
        # Convert dimensions dict to JSON string
        if 'dimensions' in processed_data and isinstance(processed_data['dimensions'], dict):
            processed_data['dimensions'] = json.dumps(processed_data['dimensions'])
        
        return self.execute_update(
            """INSERT INTO products (
                menora_id, name_hebrew, name_english, description_hebrew, 
                description_english, price, category, subcategory, 
                specifications, dimensions, weight, material, coating, standard
            ) VALUES (
                :menora_id, :name_hebrew, :name_english, :description_hebrew,
                :description_english, :price, :category, :subcategory,
                :specifications, :dimensions, :weight, :material, :coating, :standard
            ) ON CONFLICT (menora_id) DO UPDATE SET
                name_hebrew = EXCLUDED.name_hebrew,
                name_english = EXCLUDED.name_english,
                price = EXCLUDED.price,
                updated_at = CURRENT_TIMESTAMP""",
            processed_data
        )
    
    def search_products(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search products by name."""
        return self.execute_query(
            """SELECT * FROM products 
               WHERE name_hebrew ILIKE :query OR name_english ILIKE :query 
               OR menora_id ILIKE :query
               ORDER BY name_hebrew 
               LIMIT :limit""",
            {"query": f"%{query}%", "limit": limit}
        )
    
    def get_products_count(self) -> int:
        """Get total number of products."""
        try:
            result = self.execute_query("SELECT COUNT(*) as count FROM products")
            return result[0]['count'] if result else 0
        except Exception as e:
            self.logger.error(f"Error getting products count: {str(e)}")
            return 0
    
    def get_user_by_code(self, user_code: str) -> Optional[Dict[str, Any]]:
        """Get user by user code."""
        try:
            result = self.execute_query(
                "SELECT * FROM users WHERE user_code = :user_code LIMIT 1",
                {'user_code': user_code}
            )
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Error getting user by code: {str(e)}")
            return None
    
    def create_user(self, user_code: str) -> bool:
        """Create a new user."""
        try:
            user_id = f"user_{user_code}"
            return self.execute_update(
                """INSERT INTO users (user_id, user_code, preferences, created_at, updated_at, last_activity)
                   VALUES (:user_id, :user_code, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                   ON CONFLICT (user_code) DO NOTHING""",
                {'user_id': user_id, 'user_code': user_code}
            )
        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            return False