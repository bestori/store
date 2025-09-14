"""
Authentication routes for user login/logout.
"""

import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app

from app.services.database_service import DatabaseService
from app.services.user_service import UserService
from app.services.shopping_list_service import ShoppingListService
from app.services.user_statistics_service import UserStatisticsService

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


def get_user_service() -> UserService:
    """Get user service instance."""
    if not hasattr(current_app, 'database_service') or not current_app.database_service:
        raise RuntimeError("Database service not available")
    database_service = current_app.database_service
    return UserService(database_service)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler."""
    if request.method == 'GET':
        # Show login form
        return render_template('login.html')
    
    try:
        # Handle login form submission
        user_code = request.form.get('user_code', '').strip()
        
        if not user_code:
            flash('Please enter a user code.', 'error')
            return render_template('login.html')
        
        # Check if database service is available
        if not hasattr(current_app, 'database_service') or not current_app.database_service:
            flash('System is still initializing. Please wait a moment and try again.', 'error')
            return render_template('login.html')
        
        # Validate user code format
        user_service = get_user_service()
        if not user_service.is_valid_user_code(user_code):
            flash('Invalid user code format. Please use alphanumeric characters only.', 'error')
            return render_template('login.html')
        
        # Authenticate user
        auth_result = user_service.authenticate_user(user_code)
        
        if auth_result:
            user, session_id = auth_result
            
            # Store user information in session
            session['user_id'] = user.user_id
            session['user_code'] = user.user_code
            session['session_id'] = session_id
            session['preferred_language'] = user.preferred_language
            
            logger.info(f"User logged in successfully: {user_code}")
            flash(f'Welcome, {user_code}!', 'success')
            
            # Redirect to search page
            return redirect(url_for('search.search_page'))
        
        else:
            flash('Login failed. Please check your user code and try again.', 'error')
            return render_template('login.html')
    
    except RuntimeError as e:
        logger.error(f"Database service not available during login: {str(e)}")
        flash('System is still initializing. Please wait a moment and try again.', 'error')
        return render_template('login.html')
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        flash('An error occurred during login. Please try again.', 'error')
        return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """User logout."""
    try:
        session_id = session.get('session_id')
        user_code = session.get('user_code')
        
        if session_id:
            # Invalidate session in backend
            user_service = get_user_service()
            user_service.logout_user(session_id)
        
        # Clear session
        session.clear()
        
        logger.info(f"User logged out: {user_code}")
        flash('You have been logged out successfully.', 'success')
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        session.clear()  # Clear session anyway
        return redirect(url_for('main.index'))


@auth_bp.route('/validate', methods=['POST'])
def validate_session():
    """AJAX endpoint to validate user session."""
    try:
        session_id = session.get('session_id')
        
        if not session_id:
            return jsonify({
                'valid': False,
                'error': 'No session found'
            })
        
        user_service = get_user_service()
        user = user_service.validate_session(session_id)
        
        if user:
            return jsonify({
                'valid': True,
                'user_code': user.user_code,
                'preferred_language': user.preferred_language
            })
        else:
            # Session invalid, clear it
            session.clear()
            return jsonify({
                'valid': False,
                'error': 'Session expired'
            })
    
    except Exception as e:
        logger.error(f"Error validating session: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Validation error'
        }), 500


@auth_bp.route('/profile')
def profile():
    """User profile page."""
    try:
        # Check if user is logged in
        if 'user_code' not in session:
            return redirect(url_for('auth.login'))
        
        # Get services
        database_service = current_app.database_service
        user_service = UserService(database_service)
        shopping_list_service = ShoppingListService(database_service)
        statistics_service = UserStatisticsService(database_service)
        
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        user = User.from_dict(user_data) if user_data else None
        
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Get user's shopping lists and statistics
        shopping_lists = shopping_list_service.get_user_shopping_lists(user)
        user_stats = statistics_service.calculate_user_statistics(user, shopping_lists)
        recent_activity = statistics_service.get_recent_activity(user.user_id)
        
        return render_template('profile.html', 
                             user=user, 
                             user_stats=user_stats, 
                             recent_activity=recent_activity)
        
    except Exception as e:
        logger.error(f"Error loading profile: {str(e)}")
        return render_template('error.html', 
                             error_message="An error occurred loading your profile."), 500


@auth_bp.route('/profile/update', methods=['POST'])
def update_profile():
    """Update user profile."""
    try:
        # Check if user is logged in
        if 'user_code' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_service = get_user_service()
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        user = User.from_dict(user_data) if user_data else None
        
        if not user:
            session.clear()
            return jsonify({'success': False, 'error': 'Session expired'}), 401
        
        # Get form data
        preferences = {
            'preferred_language': request.form.get('preferred_language', user.preferred_language),
            'default_currency': request.form.get('default_currency', user.default_currency)
        }
        
        # Update user preferences
        success = user_service.update_user_preferences(user, preferences)
        
        if success:
            # Update session
            session['preferred_language'] = preferences['preferred_language']
            
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update profile'
            })
    
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred updating your profile'
        }), 500


# Authentication required decorator
def login_required(f):
    """Decorator to require authentication for routes."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if this is an API request (expects JSON response)
        is_api_request = request.path.startswith('/api/') or request.path.startswith('/shopping-list/')
        
        # Debug: Log session data
        logger.info(f"Session data: {dict(session)}")
        logger.info(f"Request path: {request.path}")
        
        # Simple session check - just verify user_code exists
        if 'user_code' not in session:
            logger.warning(f"No user_code in session. Session keys: {list(session.keys())}")
            if is_api_request:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        
        # For API requests, just pass through - no heavy validation
        if is_api_request:
            return f(*args, **kwargs)
        
        # For web requests, do full validation
        try:
            user_service = get_user_service()
            user_code = session.get('user_code')
            user_data = current_app.database_service.get_user_by_code(user_code)
            user = User.from_dict(user_data) if user_data else None
            
            if not user:
                session.clear()
                return redirect(url_for('auth.login'))
            
            # Make user available to the route
            request.current_user = user
            
        except Exception as e:
            logger.error(f"Error validating session in decorator: {str(e)}")
            session.clear()
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    
    return decorated_function