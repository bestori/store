"""
Flask application factory for Cable Tray Online Store.
"""

import os
import logging
from pathlib import Path
from flask import Flask
from flask_session import Session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

# Import configuration
from config.config import get_config


def create_app(config_name=None):
    """Create and configure Flask application."""
    
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load configuration
    config_obj = get_config(config_name)
    app.config.from_object(config_obj)
    
    # Ensure required directories exist
    _create_directories(app)
    
    # Setup logging
    _setup_logging(app)
    
    # Initialize extensions
    _init_extensions(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Setup error handlers
    _setup_error_handlers(app)
    
    # Initialize data cache
    _init_data_cache(app)
    
    # Initialize session manager
    _init_session_manager(app)
    
    return app


def _create_directories(app):
    """Create necessary directories if they don't exist."""
    directories = [
        Path(app.config['SESSION_FILE_DIR']),
        Path(app.config['LOG_FILE']).parent,
        Path(app.config['EXCEL_DATA_DIR']),
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def _setup_logging(app):
    """Setup application logging."""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    log_file = Path(app.config.get('LOG_FILE', 'logs/app.log'))
    
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s [%(name)s] %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Add console handler for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Configure app logger
    app.logger.setLevel(log_level)
    
    # Configure specific loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask HTTP logs
    logging.getLogger('urllib3').setLevel(logging.WARNING)   # Reduce HTTP client logs
    
    app.logger.info('Store application startup')
    app.logger.info(f'Logging configured - Level: {app.config.get("LOG_LEVEL", "INFO")}, File: {log_file}')


def _init_extensions(app):
    """Initialize Flask extensions."""
    
    # Session management
    Session(app)
    
    # CSRF Protection
    csrf = CSRFProtect()
    
    # Enable CSRF in production with proper SECRET_KEY
    if app.debug:
        csrf.init_app(app)
        app.config['WTF_CSRF_ENABLED'] = False
    else:
        csrf.init_app(app)
        app.config['WTF_CSRF_ENABLED'] = True
        
    app.csrf = csrf
    
    # CORS for API endpoints
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization", "X-CSRFToken"]
        }
    })
    
    # Rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '100 per hour')]
    )
    limiter.init_app(app)
    app.limiter = limiter
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        # Prevent XSS attacks
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # HTTPS enforcement in production
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers['Content-Security-Policy'] = csp
        
        return response


def _register_blueprints(app):
    """Register application blueprints."""
    
    # Import blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.search import search_bp
    from app.routes.shopping_list import shopping_list_bp
    from app.routes.api import api_bp
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(search_bp, url_prefix='/search')
    app.register_blueprint(shopping_list_bp, url_prefix='/shopping-list')
    app.register_blueprint(api_bp, url_prefix='/api/v1')


def _setup_error_handlers(app):
    """Setup error handlers."""
    from flask import render_template, request
    
    @app.errorhandler(404)
    def not_found(error):
        # Return JSON for API requests, HTML for web requests
        if request.path.startswith('/api/'):
            return {'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Resource not found'}}, 404
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {str(error)}")
        # Return JSON for API requests, HTML for web requests
        if request.path.startswith('/api/'):
            return {'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': 'Internal server error'}}, 500
        return render_template('error.html', error_message="An internal server error occurred."), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        # Return JSON for API requests, HTML for web requests
        if request.path.startswith('/api/'):
            return {'success': False, 'error': {'code': 'RATE_LIMIT_EXCEEDED', 'message': 'Rate limit exceeded'}}, 429
        return render_template('error.html', error_message="Rate limit exceeded. Please try again later."), 429


def _init_data_cache(app):
    """Initialize product services with Cloud SQL PostgreSQL."""
    # Initialize services
    app.excel_data = {'products': [], 'prices': {}, 'loading': True, 'loaded': False, 'syncing': False}
    app.search_service = None
    app.database_service = None
    
    def init_database_services():
        """Background thread function to initialize database services."""
        with app.app_context():
            try:
                app.logger.info("Starting Cloud SQL database initialization...")
                
                from app.services.database_service import DatabaseService
                from app.services.search_service import SearchService
                
                # Initialize database service
                app.database_service = DatabaseService(app.config)
                
                if not app.database_service.is_available():
                    app.logger.error("Database service not available!")
                    app.excel_data['loading'] = False
                    app.excel_data['loaded'] = False
                    return
                
                # Create tables if they don't exist
                if not app.database_service.create_tables():
                    app.logger.error("Failed to create database tables!")
                    app.excel_data['loading'] = False
                    app.excel_data['loaded'] = False
                    return
                
                # Check if database has products
                product_count = app.database_service.get_products_count()
                app.logger.info(f"Found {product_count} products in database")
                
                if product_count == 0:
                    app.logger.info("No products in database, syncing from Excel in background...")
                    app.excel_data['syncing'] = True
                    
                    # Load and sync Excel data to database in background
                    from app.services.excel_loader import ExcelLoader
                    
                    try:
                        excel_loader = ExcelLoader(app.config)
                        excel_data = excel_loader.load_data()
                        
                        # Migrate products to database
                        for product in excel_data.get('products', []):
                            product_data = {
                                'menora_id': product.get('menora_id', ''),
                                'name_hebrew': product.get('name_hebrew', ''),
                                'name_english': product.get('name_english', ''),
                                'description_hebrew': product.get('description_hebrew', ''),
                                'description_english': product.get('description_english', ''),
                                'price': product.get('price', 0),
                                'category': product.get('category', ''),
                                'subcategory': product.get('subcategory', ''),
                                'specifications': product.get('specifications', {}),
                                'dimensions': product.get('dimensions', {}),
                                'weight': product.get('weight', 0),
                                'material': product.get('material', ''),
                                'coating': product.get('coating', ''),
                                'standard': product.get('standard', '')
                            }
                            app.database_service.insert_product(product_data)
                        
                        app.logger.info(f"Successfully synced {len(excel_data.get('products', []))} products to database")
                        
                    except Exception as sync_error:
                        app.logger.error(f"Error syncing Excel to database: {str(sync_error)}")
                    finally:
                        app.excel_data['syncing'] = False
                
                # Service is ready
                app.excel_data['loading'] = False
                app.excel_data['loaded'] = True
                
                # Initialize search service with database
                app.search_service = SearchService(app.excel_data, database_service=app.database_service)
                
                app.logger.info(f"Database initialization complete: {app.database_service.get_products_count()} products ready")
                
            except Exception as e:
                app.logger.error(f"Database service initialization failed: {str(e)}")
                app.excel_data['loading'] = False
                app.excel_data['loaded'] = False
                app.excel_data['syncing'] = False
    
    # Start background initialization
    import threading
    thread = threading.Thread(target=init_database_services, daemon=True)
    thread.start()
    
    app.logger.info("Database service initialization started in background")


def _init_session_manager(app):
    """Initialize session manager for cleanup tasks."""
    try:
        from app.services.session_manager import SessionManager
        
        if hasattr(app, 'database_service') and app.database_service:
            session_manager = SessionManager(
                app.database_service, 
                cleanup_interval=app.config.get('SESSION_CLEANUP_INTERVAL', 3600)
            )
            
            # Store session manager in app for access from routes
            app.session_manager = session_manager
            
            # Start cleanup task
            session_manager.start_cleanup_task()
            
            app.logger.info("Session manager initialized and cleanup task started")
            
            # Register cleanup on app teardown
            @app.teardown_appcontext
            def shutdown_session_manager(exception=None):
                if hasattr(app, 'session_manager'):
                    app.session_manager.stop_cleanup_task()
        else:
            app.logger.warning("Database service not available - session manager disabled")
            app.session_manager = None
                
    except Exception as e:
        app.logger.error(f"Failed to initialize session manager: {str(e)}")
        app.session_manager = None


# Create application instance for development
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)