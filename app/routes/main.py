"""
Main routes for the Cable Tray Online Store application.
"""

import logging
from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, current_app, request, jsonify

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


@main_bp.route('/health')
def health():
    """Comprehensive health check endpoint with detailed diagnostics."""
    import os
    import sys
    import traceback
    
    status = {
        'timestamp': datetime.now().isoformat(),
        'app_status': 'running',
        'python_version': sys.version,
        'environment': dict(os.environ),
        'database': {},
        'excel_files': {},
        'services': {},
        'errors': [],
        'warnings': []
    }
    
    # Check database connection
    try:
        if hasattr(current_app, 'database_service') and current_app.database_service:
            db_service = current_app.database_service
            status['database']['service_exists'] = True
            status['database']['is_available'] = db_service.is_available()
            
            if db_service.is_available():
                try:
                    # Test database connection
                    status['database']['connection_test'] = 'attempting...'
                    test_result = db_service.execute_query("SELECT 1 as test")
                    status['database']['connection_test'] = f'success: {test_result}'
                    
                    # Get product count
                    product_count = db_service.get_products_count()
                    status['database']['products_count'] = product_count
                    
                    # Test table existence
                    tables_query = """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    """
                    tables = db_service.execute_query(tables_query)
                    status['database']['tables'] = [t['table_name'] for t in tables]
                    
                except Exception as db_error:
                    status['database']['connection_test'] = f'failed: {str(db_error)}'
                    status['errors'].append(f'Database query error: {str(db_error)}')
                    status['errors'].append(f'Database traceback: {traceback.format_exc()}')
            else:
                status['database']['connection_test'] = 'service not available'
        else:
            status['database']['service_exists'] = False
            status['warnings'].append('database_service not found in current_app')
    except Exception as e:
        status['database']['error'] = str(e)
        status['errors'].append(f'Database check error: {str(e)}')
        status['errors'].append(f'Database check traceback: {traceback.format_exc()}')
    
    # Check Excel files
    try:
        excel_dir = os.path.join(os.getcwd(), 'data', 'excel_files')
        status['excel_files']['directory_path'] = excel_dir
        status['excel_files']['directory_exists'] = os.path.exists(excel_dir)
        status['excel_files']['cwd'] = os.getcwd()
        
        if os.path.exists(excel_dir):
            files = os.listdir(excel_dir)
            status['excel_files']['files_found'] = len(files)
            status['excel_files']['files_list'] = []
            
            for file in files:
                file_path = os.path.join(excel_dir, file)
                file_info = {
                    'name': file,
                    'size': os.path.getsize(file_path),
                    'readable': os.access(file_path, os.R_OK)
                }
                status['excel_files']['files_list'].append(file_info)
        else:
            status['excel_files']['files_found'] = 0
            status['excel_files']['files_list'] = []
            status['warnings'].append(f'Excel directory not found: {excel_dir}')
            
            # Try to find data directory
            possible_paths = [
                'data/excel_files',
                './data/excel_files',
                '../data/excel_files',
                '/app/data/excel_files'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    status['excel_files'][f'found_alternative'] = path
                    break
                    
    except Exception as e:
        status['excel_files']['error'] = str(e)
        status['errors'].append(f'Excel files check error: {str(e)}')
    
    # Check app services
    try:
        services_to_check = ['database_service', 'search_service', 'excel_data', 'session_manager']
        for service_name in services_to_check:
            if hasattr(current_app, service_name):
                service = getattr(current_app, service_name)
                status['services'][service_name] = {
                    'exists': True,
                    'type': str(type(service)),
                    'value': str(service) if service is not None else 'None'
                }
                
                # Special checks for excel_data
                if service_name == 'excel_data' and isinstance(service, dict):
                    status['services'][service_name]['keys'] = list(service.keys())
                    status['services'][service_name]['loading'] = service.get('loading', 'unknown')
                    status['services'][service_name]['loaded'] = service.get('loaded', 'unknown')
                    status['services'][service_name]['products_count'] = len(service.get('products', []))
            else:
                status['services'][service_name] = {'exists': False}
    except Exception as e:
        status['services']['error'] = str(e)
        status['errors'].append(f'Services check error: {str(e)}')
    
    # Check configuration
    try:
        config_keys = ['DATABASE_URL', 'FLASK_ENV', 'DB_PASSWORD', 'CLOUD_SQL_CONNECTION_NAME']
        status['config'] = {}
        for key in config_keys:
            env_value = os.environ.get(key)
            if env_value:
                # Mask passwords
                if 'PASSWORD' in key or 'SECRET' in key:
                    status['config'][key] = f"{'*' * (len(env_value) - 4)}{env_value[-4:]}" if len(env_value) > 4 else "***"
                else:
                    status['config'][key] = env_value
            else:
                status['config'][key] = 'not_set'
    except Exception as e:
        status['config'] = {'error': str(e)}
    
    # Overall health assessment
    if status['errors']:
        status['overall_status'] = 'unhealthy'
    elif status['warnings']:
        status['overall_status'] = 'degraded'
    else:
        status['overall_status'] = 'healthy'
    
    return jsonify(status)


@main_bp.route('/load-excel')
def load_excel():
    """Manually trigger Excel data loading into database."""
    try:
        if not hasattr(current_app, 'database_service') or not current_app.database_service:
            return jsonify({'error': 'Database service not available'}), 500
            
        if not current_app.database_service.is_available():
            return jsonify({'error': 'Database not connected'}), 500
        
        # Load Excel data
        from app.services.excel_loader import ExcelLoader
        
        excel_loader = ExcelLoader(current_app.config)
        excel_data = excel_loader.load_data()
        
        products = excel_data.get('products', [])
        loaded_count = 0
        
        # Insert products into database
        for product in products:
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
            
            # Convert dict/list fields to JSON strings for PostgreSQL
            import json
            product_data['specifications'] = json.dumps(product_data['specifications'])
            product_data['dimensions'] = json.dumps(product_data['dimensions'])
            
            if current_app.database_service.insert_product(product_data):
                loaded_count += 1
        
        # Update excel_data status
        current_app.excel_data['loaded'] = True
        current_app.excel_data['loading'] = False
        current_app.excel_data['syncing'] = False
        
        return jsonify({
            'success': True,
            'products_found': len(products),
            'products_loaded': loaded_count,
            'database_count': current_app.database_service.get_products_count()
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@main_bp.route('/')
def index():
    """Home page - show login for anonymous users, dashboard for authenticated users."""
    try:
        if 'user_code' in session and 'user_id' in session:
            # User is logged in, show dashboard
            from app.services.firebase_service import FirebaseService
            from app.services.user_service import UserService
            from app.services.shopping_list_service import ShoppingListService
            
            # Get services
            firebase_service = FirebaseService(current_app.config)
            user_service = UserService(firebase_service)
            shopping_list_service = ShoppingListService(firebase_service, current_app.excel_data)
            
            # Get current user
            user = user_service.validate_session(session.get('session_id'))
            if not user:
                session.clear()
                return render_template('index.html')
            
            # Get recent shopping lists (last 3)
            all_lists = shopping_list_service.get_user_shopping_lists(user)
            recent_lists = sorted(all_lists, key=lambda x: x.updated_at or x.created_at, reverse=True)[:3]
            
            return render_template('index.html', user=user, recent_lists=recent_lists)
        
        # User not logged in, show login page
        return render_template('index.html')
        
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('error.html', 
                             error_message="An error occurred loading the home page."), 500


@main_bp.route('/about')
def about():
    """About page."""
    try:
        return render_template('about.html')
        
    except Exception as e:
        logger.error(f"Error in about route: {str(e)}")
        return render_template('error.html', 
                             error_message="An error occurred loading the about page."), 500


@main_bp.route('/help')
def help_page():
    """Help page."""
    try:
        return render_template('help.html')
        
    except Exception as e:
        logger.error(f"Error in help route: {str(e)}")
        return render_template('error.html', 
                             error_message="An error occurred loading the help page."), 500


@main_bp.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Check if Excel data exists and loading status
        has_excel_data = hasattr(current_app, 'excel_data') and bool(current_app.excel_data)
        is_loading = current_app.excel_data.get('loading', False) if has_excel_data else False
        products_count = len(current_app.excel_data.get('products', [])) if has_excel_data else 0
        
        # App is healthy if it started, regardless of Excel loading status
        status = 'healthy'
        if has_excel_data and current_app.excel_data.get('error'):
            status = 'degraded'  # Can serve but with limited functionality
        
        return {
            'status': status,
            'excel_data_loading': is_loading,
            'excel_data_loaded': not is_loading and products_count > 0,
            'products_count': products_count,
            'error': current_app.excel_data.get('error') if has_excel_data else None
        }
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }, 500





@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404


@main_bp.route('/set-language', methods=['POST'])
def set_language():
    """Set user's preferred language."""
    try:
        data = request.get_json()
        language = data.get('language', 'hebrew')
        
        if language not in ['hebrew', 'english']:
            return jsonify({'success': False, 'error': 'Invalid language'}), 400
        
        session['preferred_language'] = language
        
        return jsonify({'success': True, 'language': language})
        
    except Exception as e:
        logger.error(f"Error setting language: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to set language'}), 500


@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404


@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', 
                         error_message="An internal server error occurred."), 500