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
    """Simple health check endpoint."""
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}


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