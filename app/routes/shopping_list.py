"""
Shopping list routes for managing user shopping lists.
"""

import logging
from flask import Blueprint, render_template, request, jsonify, current_app, session, make_response, redirect, url_for
from datetime import datetime

from app.services.firebase_service import FirebaseService
from app.services.shopping_list_service import ShoppingListService
from app.services.user_service import UserService
from app.services.html_generator import HtmlGenerator
from app.services.price_calculator import PriceCalculator
from app.routes.auth import login_required

shopping_list_bp = Blueprint('shopping_list', __name__)
logger = logging.getLogger(__name__)


def get_services():
    """Get service instances."""
    firebase_service = FirebaseService(current_app.config)
    user_service = UserService(firebase_service)
    shopping_list_service = ShoppingListService(firebase_service, current_app.excel_data)
    price_calculator = PriceCalculator()
    html_generator = HtmlGenerator(price_calculator)
    
    return user_service, shopping_list_service, price_calculator, html_generator


@shopping_list_bp.route('/')
@login_required
def shopping_lists_page():
    """Shopping lists overview page."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Get user's shopping lists
        shopping_lists = shopping_list_service.get_user_shopping_lists(user)
        
        return render_template('shopping_lists.html', 
                             shopping_lists=shopping_lists,
                             user=user)
        
    except Exception as e:
        logger.error(f"Error loading shopping lists page: {str(e)}")
        return render_template('error.html', 
                             error_message="An error occurred loading your shopping lists."), 500


@shopping_list_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_shopping_list():
    """Create new shopping list."""
    if request.method == 'GET':
        return render_template('create_shopping_list.html')
    
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get form data
        list_name = (request.json.get('list_name') or '').strip()
        description = (request.json.get('description') or '').strip() or None
        
        if not list_name:
            return jsonify({
                'success': False,
                'error': 'List name is required'
            }), 400
        
        # Create shopping list
        shopping_list = shopping_list_service.create_shopping_list(
            user=user,
            list_name=list_name,
            description=description
        )
        
        if shopping_list:
            return jsonify({
                'success': True,
                'data': {
                    'list_id': shopping_list.list_id,
                    'list_name': shopping_list.list_name,
                    'description': shopping_list.description
                },
                'message': 'Shopping list created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create shopping list'
            }), 500
        
    except Exception as e:
        logger.error(f"Error creating shopping list: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred creating the shopping list'
        }), 500


@shopping_list_bp.route('/<list_id>')
@login_required
def view_shopping_list(list_id):
    """View specific shopping list."""
    try:
        user_service, shopping_list_service, price_calculator, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Get shopping list
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        if not shopping_list:
            return render_template('404.html'), 404
        
        # Calculate totals
        totals = shopping_list_service.calculate_list_totals(shopping_list)
        
        return render_template('shopping_list_detail.html', 
                             shopping_list=shopping_list,
                             totals=totals,
                             user=user)
        
    except Exception as e:
        logger.error(f"Error viewing shopping list {list_id}: {str(e)}")
        return render_template('error.html', 
                             error_message="An error occurred loading the shopping list."), 500


@shopping_list_bp.route('/<list_id>/add-item', methods=['POST'])
@login_required
def add_item_to_list(list_id):
    """Add item to shopping list."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get shopping list
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        if not shopping_list:
            return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
        
        # Get form data
        menora_id = (request.json.get('menora_id') or '').strip()
        quantity = request.json.get('quantity', 1)
        notes = (request.json.get('notes') or '').strip() or None
        
        if not menora_id:
            return jsonify({
                'success': False,
                'error': 'Product ID is required'
            }), 400
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid quantity'
            }), 400
        
        # Add item to list
        success = shopping_list_service.add_item_to_list(
            shopping_list=shopping_list,
            menora_id=menora_id,
            quantity=quantity,
            notes=notes
        )
        
        if success:
            # Get updated totals
            totals = shopping_list_service.calculate_list_totals(shopping_list)
            
            return jsonify({
                'success': True,
                'data': {
                    'list_id': shopping_list.list_id,
                    'item_count': shopping_list.get_item_count(),
                    'totals': totals
                },
                'message': 'Item added to shopping list'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add item to shopping list'
            }), 500
        
    except Exception as e:
        logger.error(f"Error adding item to list {list_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred adding the item'
        }), 500


@shopping_list_bp.route('/<list_id>/update-item/<item_id>', methods=['PUT'])
@login_required
def update_item_in_list(list_id, item_id):
    """Update item in shopping list."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get shopping list
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        if not shopping_list:
            return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
        
        # Get form data
        quantity = request.json.get('quantity')
        notes = request.json.get('notes')
        
        if quantity is not None:
            try:
                quantity = int(quantity)
                if quantity < 0:
                    raise ValueError("Quantity cannot be negative")
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Invalid quantity'
                }), 400
        
        # Update item
        success = shopping_list_service.update_item_in_list(
            shopping_list=shopping_list,
            item_id=item_id,
            quantity=quantity,
            notes=notes
        )
        
        if success:
            # Get updated totals
            totals = shopping_list_service.calculate_list_totals(shopping_list)
            
            return jsonify({
                'success': True,
                'data': {
                    'list_id': shopping_list.list_id,
                    'item_count': shopping_list.get_item_count(),
                    'totals': totals
                },
                'message': 'Item updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update item'
            }), 500
        
    except Exception as e:
        logger.error(f"Error updating item {item_id} in list {list_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred updating the item'
        }), 500


@shopping_list_bp.route('/<list_id>/remove-item/<item_id>', methods=['DELETE'])
@login_required
def remove_item_from_list(list_id, item_id):
    """Remove item from shopping list."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get shopping list
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        if not shopping_list:
            return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
        
        # Remove item
        success = shopping_list_service.remove_item_from_list(shopping_list, item_id)
        
        if success:
            # Get updated totals
            totals = shopping_list_service.calculate_list_totals(shopping_list)
            
            return jsonify({
                'success': True,
                'data': {
                    'list_id': shopping_list.list_id,
                    'item_count': shopping_list.get_item_count(),
                    'totals': totals
                },
                'message': 'Item removed from shopping list'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to remove item'
            }), 500
        
    except Exception as e:
        logger.error(f"Error removing item {item_id} from list {list_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred removing the item'
        }), 500


@shopping_list_bp.route('/<list_id>/generate-html')
@login_required
def generate_html_list(list_id):
    """Generate HTML shopping list."""
    try:
        user_service, shopping_list_service, price_calculator, html_generator = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get shopping list
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        if not shopping_list:
            return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
        
        # Get parameters
        language = request.args.get('lang', session.get('preferred_language', 'hebrew'))
        include_images = request.args.get('images', 'false').lower() == 'true'
        format_type = request.args.get('format', 'print')
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Generate HTML
        html_content = html_generator.generate_shopping_list_html(
            shopping_list=shopping_list,
            user=user,
            language=language,
            include_images=include_images,
            format_type=format_type
        )
        
        if download:
            # Return as file download
            response = make_response(html_content)
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="shopping-list-{user.user_code}-{list_id[:8]}.html"'
            return response
        else:
            # Return as regular response
            return html_content
        
    except Exception as e:
        logger.error(f"Error generating HTML for list {list_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred generating the HTML list'
        }), 500


@shopping_list_bp.route('/<list_id>/update', methods=['PUT'])
@login_required
def update_shopping_list(list_id):
    """Update shopping list information."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get shopping list
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        if not shopping_list:
            return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
        
        # Get form data
        list_name = (request.json.get('list_name') or '').strip()
        description = request.json.get('description')
        
        if description is not None:
            description = description.strip() or None
        
        # Update shopping list
        success = shopping_list_service.update_shopping_list(
            shopping_list=shopping_list,
            list_name=list_name if list_name else None,
            description=description
        )
        
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'list_id': shopping_list.list_id,
                    'list_name': shopping_list.list_name,
                    'description': shopping_list.description
                },
                'message': 'Shopping list updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update shopping list'
            }), 500
        
    except Exception as e:
        logger.error(f"Error updating shopping list {list_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred updating the shopping list'
        }), 500


@shopping_list_bp.route('/<list_id>/delete', methods=['DELETE'])
@login_required
def delete_shopping_list(list_id):
    """Delete shopping list."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get shopping list
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        if not shopping_list:
            return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
        
        # Delete shopping list
        success = shopping_list_service.delete_shopping_list(shopping_list, user)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Shopping list deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete shopping list'
            }), 500
        
    except Exception as e:
        logger.error(f"Error deleting shopping list {list_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred deleting the shopping list'
        }), 500


@shopping_list_bp.route('/<list_id>/duplicate', methods=['POST'])
@login_required
def duplicate_shopping_list(list_id):
    """Duplicate shopping list."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get shopping list
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        if not shopping_list:
            return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
        
        # Get new name
        new_name = (request.json.get('new_name') or '').strip()
        
        # Duplicate shopping list
        new_list = shopping_list_service.duplicate_shopping_list(
            shopping_list=shopping_list,
            user=user,
            new_name=new_name if new_name else None
        )
        
        if new_list:
            return jsonify({
                'success': True,
                'data': {
                    'list_id': new_list.list_id,
                    'list_name': new_list.list_name,
                    'description': new_list.description,
                    'item_count': new_list.get_item_count()
                },
                'message': 'Shopping list duplicated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to duplicate shopping list'
            }), 500
        
    except Exception as e:
        logger.error(f"Error duplicating shopping list {list_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred duplicating the shopping list'
        }), 500


@shopping_list_bp.route('/add-item', methods=['POST'])
@login_required
def add_item():
    """Add item to user's default shopping list (auto-create if needed)."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user = user_service.validate_session(session.get('session_id'))
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get form data
        menora_id = (request.json.get('menora_id') or '').strip()
        quantity = request.json.get('quantity', 1)
        notes = (request.json.get('notes') or '').strip() or None
        
        if not menora_id:
            return jsonify({
                'success': False,
                'error': 'Product ID is required'
            }), 400
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid quantity'
            }), 400
        
        # Get or create default shopping list
        shopping_list = shopping_list_service.get_or_create_default_list(user)
        if not shopping_list:
            return jsonify({
                'success': False,
                'error': 'Failed to create shopping list'
            }), 500
        
        # Add item to list
        success = shopping_list_service.add_item_to_list(
            shopping_list=shopping_list,
            menora_id=menora_id,
            quantity=quantity,
            notes=notes
        )
        
        if success:
            # Get updated totals
            totals = shopping_list_service.calculate_list_totals(shopping_list)
            
            return jsonify({
                'success': True,
                'data': {
                    'list_id': shopping_list.list_id,
                    'list_name': shopping_list.list_name,
                    'item_count': shopping_list.get_item_count(),
                    'totals': totals
                },
                'message': 'Item added to shopping list'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add item to shopping list'
            }), 500
        
    except Exception as e:
        logger.error(f"Error adding item to default list: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred adding the item'
        }), 500