"""
Shopping list routes for managing user shopping lists.
"""

import logging
from flask import Blueprint, render_template, request, jsonify, current_app, session, make_response, redirect, url_for
from datetime import datetime

from app.services.database_service import DatabaseService
from app.services.shopping_list_service import ShoppingListService
from app.services.user_service import UserService
from app.services.html_generator import HtmlGenerator
from app.services.price_calculator import PriceCalculator
from app.routes.auth import login_required

shopping_list_bp = Blueprint('shopping_list', __name__)
logger = logging.getLogger(__name__)


def get_services():
    """Get service instances."""
    database_service = current_app.database_service
    user_service = UserService(database_service)
    shopping_list_service = ShoppingListService(database_service)
    price_calculator = PriceCalculator()
    html_generator = HtmlGenerator(price_calculator)
    
    return user_service, shopping_list_service, price_calculator, html_generator


@shopping_list_bp.route('/')
@login_required
def shopping_lists_page():
    """Shopping lists overview page."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user - use same simple method as add-to-cart
        user_code = session.get('user_code')
        database_service = current_app.database_service
        user_data = database_service.get_user_by_code(user_code)
        
        if not user_data:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Create User object
        from app.models.user import User
        user = User.from_dict(user_data)
        
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
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        user = User.from_dict(user_data) if user_data else None
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
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        from app.models.user import User
        user = User.from_dict(user_data) if user_data else None
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


@shopping_list_bp.route('/debug-db', methods=['GET'])
@login_required  
def debug_database():
    """Debug endpoint to show raw database contents"""
    try:
        database_service = current_app.database_service
        
        # Get all shopping lists
        all_lists = database_service.execute_query("SELECT * FROM shopping_lists ORDER BY created_at DESC LIMIT 10")
        
        # Get all users
        all_users = database_service.execute_query("SELECT user_id, user_code, preferences FROM users ORDER BY created_at DESC LIMIT 5")
        
        return jsonify({
            'all_shopping_lists': all_lists,
            'all_users': all_users
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@shopping_list_bp.route('/debug-user', methods=['GET'])
@login_required
def debug_user_info():
    """Debug endpoint to show user and shopping list info"""
    try:
        import json
        from app.services.database_service import DatabaseService
        from app.models.user import User
        
        # Get user info
        user_code = session.get('user_code')
        database_service = current_app.database_service
        user_data = database_service.get_user_by_code(user_code)
        
        if not user_data:
            return jsonify({'error': 'User not found', 'user_code': user_code})
        
        user = User.from_dict(user_data)
        
        # Get shopping lists for user
        shopping_lists = database_service.execute_query(
            "SELECT * FROM shopping_lists WHERE user_id = :user_id",
            {'user_id': user.user_id}
        )
        
        # Get shopping list items (from JSONB column, not separate table)
        items = []
        for shopping_list in shopping_lists:
            if shopping_list.get('items'):
                try:
                    list_items = json.loads(shopping_list['items']) if isinstance(shopping_list['items'], str) else shopping_list['items']
                    items.extend(list_items)
                except:
                    pass
        
        return jsonify({
            'user': {
                'user_id': user.user_id,
                'user_code': user.user_code,
                'default_list_id': user.default_list_id,
                'active_lists': user.active_lists
            },
            'shopping_lists': shopping_lists,
            'shopping_list_items': items,
            'session': dict(session)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@shopping_list_bp.route('/add-item', methods=['POST'])
@login_required
def add_item_to_default_list():
    """Add item to user's default shopping list."""
    logger.info(f"=== ADD TO CART DEBUG START ===")
    logger.info(f"Session data: {dict(session)}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request data: {request.get_json()}")
    
    try:
        user_service, shopping_list_service, _, _ = get_services()
        logger.info(f"Services obtained successfully")
        
        # Get current user - since @login_required passed, user is authenticated
        user_code = session.get('user_code')
        logger.info(f"User code from session: {user_code}")
        
        # Get user data from database and create User object
        from app.services.database_service import DatabaseService
        database_service = current_app.database_service
        user_data = database_service.get_user_by_code(user_code)
        logger.info(f"User data from DB: {user_data}")
        
        if not user_data:
            logger.error(f"User not found for user_code: {user_code}")
            return jsonify({'success': False, 'error': 'User not found', 'debug': 'User lookup failed'}), 401
        
        # Create User object from database data
        from app.models.user import User
        user = User.from_dict(user_data)
        logger.info(f"User object created: {user}")
        
        # Get or create default list - simplified approach
        logger.info(f"User default_list_id: {user.default_list_id}")
        logger.info(f"User active_lists: {user.active_lists}")
        
        # Try to use existing list first
        if user.default_list_id:
            list_id = user.default_list_id
            logger.info(f"Using default list ID: {list_id}")
        elif user.active_lists:
            # Use any existing active list
            list_id = list(user.active_lists.keys())[0]
            logger.info(f"Using first active list ID: {list_id}")
        else:
            # Create a simple default list directly in database
            logger.info("No existing lists, creating minimal default list")
            import uuid
            import json
            from datetime import datetime
            
            list_id = str(uuid.uuid4())
            
            # Insert directly into database
            try:
                database_service = current_app.database_service
                logger.info(f"INSERT user_id: {user.user_id}")
                database_service.execute_update(
                    """INSERT INTO shopping_lists 
                       (list_id, user_id, name, status, items) 
                       VALUES (:list_id, :user_id, :name, :status, :items)
                       ON CONFLICT (list_id) DO NOTHING""",
                    {
                        'list_id': list_id,
                        'user_id': user.user_id,
                        'name': 'My Shopping List',
                        'status': 'active',
                        'items': '[]'  # Empty JSON array
                    }
                )
                
                # Update user's default list preference
                try:
                    database_service.execute_update(
                        """UPDATE users 
                           SET preferences = jsonb_set(preferences, '{defaultListId}', :default_list_id)
                           WHERE user_id = :user_id""",
                        {
                            'default_list_id': f'"{list_id}"',  # JSON string value
                            'user_id': user.user_id
                        }
                    )
                    logger.info(f"Updated user default list to: {list_id}")
                except Exception as e:
                    logger.warning(f"Failed to update user default list: {e}")
                
                logger.info(f"Created minimal default list ID: {list_id}")
                
            except Exception as e:
                logger.error(f"Failed to create minimal default list: {e}")
                return jsonify({'success': False, 'error': f'Could not create shopping list: {str(e)}'}), 500
        
        # Skip verification - assume list exists and proceed directly to add item
        logger.info(f"Proceeding to add item to list_id: {list_id}")
        
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
        
        # Add item directly to database instead of using complex shopping_list_service
        logger.info(f"Adding item to database - menora_id: {menora_id}, quantity: {quantity}")
        
        try:
            # Look up complete product data from database
            product_data = database_service.execute_query(
                """SELECT price, name_hebrew, name_english, 
                          CASE 
                            WHEN specifications::text LIKE '%image_url%' 
                            THEN specifications->>'image_url'
                            ELSE NULL 
                          END as image_url
                   FROM products WHERE menora_id = :menora_id""",
                {'menora_id': menora_id}
            )
            
            if product_data and product_data[0]:
                product_info = product_data[0]
                unit_price = float(product_info['price']) if product_info['price'] else 0.0
                name_hebrew = product_info.get('name_hebrew', '')
                name_english = product_info.get('name_english', '')  
                image_url = product_info.get('image_url')
                logger.info(f"Found product: {name_hebrew} / {name_english}, price: {unit_price}")
            else:
                unit_price = 0.0
                name_hebrew = ''
                name_english = ''
                image_url = None
                logger.warning(f"Product not found: {menora_id}")
            
            # Add item to shopping list using JSONB items column
            import uuid
            import json
            from datetime import datetime
            
            item_id = str(uuid.uuid4())
            
            # Create item data for JSONB storage
            item_data = {
                'item_id': item_id,
                'menora_id': menora_id,
                'quantity': quantity,
                'unit_price': float(unit_price),
                'notes': notes,
                'added_at': datetime.utcnow().isoformat(),
                'product': {
                    'hebrew_term': name_hebrew,
                    'english_term': name_english
                },
                'image_url': image_url
            }
            
            # Add item to the JSONB items array and update timestamp and total price
            item_total = quantity * unit_price
            database_service.execute_update(
                """UPDATE shopping_lists 
                   SET items = items || :new_item,
                       updated_at = :updated_at,
                       total_price = COALESCE(total_price, 0) + :item_total
                   WHERE list_id = :list_id""",
                {
                    'new_item': json.dumps([item_data]),  # Add as array element
                    'list_id': list_id,
                    'updated_at': datetime.utcnow(),
                    'item_total': item_total
                }
            )
            
            logger.info(f"Item added successfully to database")
            logger.info(f"=== ADD TO CART DEBUG END - SUCCESS ===")
            
            return jsonify({
                'success': True,
                'message': 'Item added to shopping list',
                'item_id': item_id,
                'redirect_url': f'/shopping-list/{list_id}'
            })
            
        except Exception as e:
            logger.error(f"Failed to add item to database: {e}")
            logger.info(f"=== ADD TO CART DEBUG END - FAILURE ===")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error adding item to default list: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred'
        }), 500


@shopping_list_bp.route('/<list_id>/add-item', methods=['POST'])
@login_required
def add_item_to_list(list_id):
    """Add item to shopping list."""
    try:
        user_service, shopping_list_service, _, _ = get_services()
        
        # Get current user
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        user = User.from_dict(user_data) if user_data else None
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
        # Get current user - use simple database method
        user_code = session.get('user_code')
        database_service = current_app.database_service
        user_data = database_service.get_user_by_code(user_code)
        from app.models.user import User
        user = User.from_dict(user_data) if user_data else None
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get form data
        quantity = request.json.get('quantity')
        notes = request.json.get('notes')
        
        if quantity is not None:
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    # If quantity is 0 or negative, remove the item instead
                    return redirect(url_for('shopping_list.remove_item_from_list', list_id=list_id, item_id=item_id))
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Invalid quantity'
                }), 400
        
        # Update item directly in database JSONB
        try:
            # Get the shopping list to find the item
            shopping_list_data = database_service.execute_query(
                "SELECT items FROM shopping_lists WHERE list_id = :list_id AND user_id = :user_id",
                {'list_id': list_id, 'user_id': user.user_id}
            )
            
            if not shopping_list_data:
                return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
            
            items = shopping_list_data[0]['items']
            if isinstance(items, str):
                import json
                items = json.loads(items)
            
            # Find and update the item
            item_found = False
            for item in items:
                if item.get('item_id') == item_id:
                    item_found = True
                    if quantity is not None:
                        old_quantity = item.get('quantity', 1)
                        item['quantity'] = quantity
                        # Recalculate total price change
                        unit_price = item.get('unit_price', 0)
                        price_difference = (quantity - old_quantity) * unit_price
                    if notes is not None:
                        item['notes'] = notes
                    break
            
            if not item_found:
                return jsonify({'success': False, 'error': 'Item not found'}), 404
            
            # Update the shopping list with modified items
            import json
            from datetime import datetime
            
            update_params = {
                'items': json.dumps(items),
                'list_id': list_id,
                'updated_at': datetime.utcnow()
            }
            
            if quantity is not None and 'price_difference' in locals():
                # Update total price
                update_query = """UPDATE shopping_lists 
                                  SET items = :items,
                                      updated_at = :updated_at,
                                      total_price = COALESCE(total_price, 0) + :price_difference
                                  WHERE list_id = :list_id"""
                update_params['price_difference'] = price_difference
            else:
                # Just update items and timestamp
                update_query = """UPDATE shopping_lists 
                                  SET items = :items,
                                      updated_at = :updated_at
                                  WHERE list_id = :list_id"""
            
            success = database_service.execute_update(update_query, update_params)
            
            if success:
                return jsonify({
                    'success': True,
                    'data': {
                        'list_id': list_id,
                        'item_count': len(items),
                        'totals': {'item_count': len(items)}  # Simplified
                    },
                    'message': 'Item updated successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to update item in database'
                }), 500
                
        except Exception as e:
            logger.error(f"Error updating item {item_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
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
        # Get current user - use simple database method
        user_code = session.get('user_code')
        database_service = current_app.database_service
        user_data = database_service.get_user_by_code(user_code)
        from app.models.user import User
        user = User.from_dict(user_data) if user_data else None
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Remove item directly from database JSONB
        try:
            # Get the shopping list to find the item
            shopping_list_data = database_service.execute_query(
                "SELECT items, total_price FROM shopping_lists WHERE list_id = :list_id AND user_id = :user_id",
                {'list_id': list_id, 'user_id': user.user_id}
            )
            
            if not shopping_list_data:
                return jsonify({'success': False, 'error': 'Shopping list not found'}), 404
            
            items = shopping_list_data[0]['items']
            current_total = float(shopping_list_data[0]['total_price'] or 0)
            
            if isinstance(items, str):
                import json
                items = json.loads(items)
            
            # Find and remove the item
            item_found = False
            removed_price = 0
            for i, item in enumerate(items):
                if item.get('item_id') == item_id:
                    item_found = True
                    # Calculate price to subtract
                    unit_price = item.get('unit_price', 0)
                    quantity = item.get('quantity', 1)
                    removed_price = unit_price * quantity
                    # Remove the item
                    items.pop(i)
                    break
            
            if not item_found:
                return jsonify({'success': False, 'error': 'Item not found'}), 404
            
            # Update the shopping list with modified items
            import json
            from datetime import datetime
            
            success = database_service.execute_update(
                """UPDATE shopping_lists 
                   SET items = :items,
                       updated_at = :updated_at,
                       total_price = GREATEST(COALESCE(total_price, 0) - :removed_price, 0)
                   WHERE list_id = :list_id""",
                {
                    'items': json.dumps(items),
                    'list_id': list_id,
                    'updated_at': datetime.utcnow(),
                    'removed_price': removed_price
                }
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'data': {
                        'list_id': list_id,
                        'item_count': len(items),
                        'totals': {'item_count': len(items)}  # Simplified
                    },
                    'message': 'Item removed from shopping list'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to remove item from database'
                }), 500
                
        except Exception as e:
            logger.error(f"Error removing item {item_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
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
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        user = User.from_dict(user_data) if user_data else None
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
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        user = User.from_dict(user_data) if user_data else None
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
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        user = User.from_dict(user_data) if user_data else None
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
        user_code = session.get('user_code')
        user_data = current_app.database_service.get_user_by_code(user_code)
        user = User.from_dict(user_data) if user_data else None
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
        
        # User is already authenticated by @login_required decorator
        # Get user from session data
        user_code = session.get('user_code')
        if not user_code:
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
        shopping_list = shopping_list_service.get_or_create_default_list(user_code)
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