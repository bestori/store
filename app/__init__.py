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
    
    # Temporarily disable CSRF to test search functionality
    csrf.init_app(app)
    app.config['WTF_CSRF_ENABLED'] = False
        
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
    """Initialize product services with PostgreSQL and load products from Excel."""
    # Initialize loading state
    app.loading_state = {
        'loading': True,
        'loaded': False,
        'syncing': False,
        'error': None,
        'progress': 0,
        'current_step': 'Initializing...',
        'product_count': 0
    }
    app.search_service = None
    app.database_service = None
    
    def init_database_services():
        """Background thread function to initialize database services and load products."""
        with app.app_context():
            try:
                app.logger.info("Starting PostgreSQL database initialization...")
                app.loading_state['current_step'] = 'Connecting to database...'
                app.loading_state['progress'] = 25
                
                from app.services.database_service import DatabaseService
                from app.services.search_service import SearchService
                
                # Initialize database service
                app.database_service = DatabaseService(app.config)
                
                if not app.database_service.is_available():
                    app.logger.error("Database service not available!")
                    app.loading_state['loading'] = False
                    app.loading_state['loaded'] = False
                    app.loading_state['error'] = 'Database connection failed'
                    return
                
                app.logger.info("Database connected successfully")
                app.loading_state['current_step'] = 'Creating database tables...'
                app.loading_state['progress'] = 40
                
                # Create tables if they don't exist
                if not app.database_service.create_tables():
                    app.logger.error("Failed to create database tables!")
                    app.loading_state['loading'] = False
                    app.loading_state['loaded'] = False
                    app.loading_state['error'] = 'Failed to create database tables'
                    return
                
                app.logger.info("Database tables created/verified")
                app.loading_state['current_step'] = 'Loading products from Excel files...'
                app.loading_state['progress'] = 60
                app.loading_state['syncing'] = True
                
                # Always load products from Excel files (updates existing, no duplicates)
                from app.services.excel_loader import ExcelLoader
                
                try:
                    excel_loader = ExcelLoader(app.config)
                    excel_data = excel_loader.load_data()
                    
                    app.logger.info(f"Excel data loaded: {len(excel_data.get('products', []))} products")
                    app.loading_state['current_step'] = 'Saving products to database...'
                    app.loading_state['progress'] = 80
                    
                    # Load/update products in database
                    loaded_count = 0
                    for product in excel_data.get('products', []):
                        # Convert Product object to database format
                        if hasattr(product, 'menora_id'):
                            product_data = {
                                'menora_id': product.menora_id,
                                'name_hebrew': product.descriptions.hebrew if product.descriptions else '',
                                'name_english': product.descriptions.english if product.descriptions else '',
                                'description_hebrew': product.descriptions.hebrew if product.descriptions else '',
                                'description_english': product.descriptions.english if product.descriptions else '',
                                'price': product.pricing.price if product.pricing else 0,
                                'category': product.category or '',
                                'subcategory': product.subcategory or '',
                                'specifications': {
                                    'type': product.specifications.type if product.specifications else '',
                                    'height': product.specifications.height if product.specifications else None,
                                    'width': product.specifications.width if product.specifications else None,
                                    'thickness': product.specifications.thickness if product.specifications else None,
                                    'galvanization': product.specifications.galvanization if product.specifications else '',
                                    'material': product.specifications.material if product.specifications else ''
                                } if product.specifications else {},
                                'dimensions': {},
                                'weight': 0,
                                'material': product.specifications.material if product.specifications else '',
                                'coating': product.specifications.galvanization if product.specifications else '',
                                'standard': ''
                            }
                        else:
                            # Handle dict format
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
                        
                        if app.database_service.insert_product(product_data):
                            loaded_count += 1
                    
                    app.logger.info(f"Successfully loaded {loaded_count} products to database")
                    app.loading_state['product_count'] = loaded_count
                    
                except Exception as sync_error:
                    app.logger.error(f"Error loading Excel to database: {str(sync_error)}")
                    app.loading_state['error'] = f'Error loading products: {str(sync_error)}'
                    app.loading_state['loading'] = False
                    app.loading_state['loaded'] = False
                    return
                finally:
                    app.loading_state['syncing'] = False
                
                app.loading_state['current_step'] = 'Initializing search service...'
                app.loading_state['progress'] = 90
                
                # Initialize search service with database
                app.search_service = SearchService(database_service=app.database_service)
                
                # Initialize product service for API endpoints
                from app.services.product_service import ProductService
                app.product_service = ProductService(app.database_service)
                
                # Loading complete
                app.loading_state['loading'] = False
                app.loading_state['loaded'] = True
                app.loading_state['current_step'] = 'Ready!'
                app.loading_state['progress'] = 100
                
                final_count = app.database_service.get_products_count()
                app.logger.info(f"Database initialization complete: {final_count} products ready")
                
            except Exception as e:
                app.logger.error(f"Database service initialization failed: {str(e)}")
                app.loading_state['loading'] = False
                app.loading_state['loaded'] = False
                app.loading_state['syncing'] = False
                app.loading_state['error'] = f'Initialization failed: {str(e)}'
    
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