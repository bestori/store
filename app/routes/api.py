"""
API routes for the Cable Tray Online Store application.

Provides JSON API endpoints according to the API specification.
"""

import logging
from flask import Blueprint, request, jsonify, current_app, session
from datetime import datetime, timezone

from app.services.firebase_service import FirebaseService
from app.services.search_service import SearchService
from app.services.shopping_list_service import ShoppingListService
from app.services.user_service import UserService
from app.services.price_calculator import PriceCalculator
from app.services.html_generator import HtmlGenerator

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)


def get_services():
    """Get service instances."""
    # Always use Firebase services - no production bypass
    firebase_service = FirebaseService(current_app.config)
    user_service = UserService(firebase_service)
    shopping_list_service = ShoppingListService(firebase_service, current_app.excel_data)
        
    # Use singleton SearchService stored on app
    if not hasattr(current_app, 'search_service') or current_app.search_service is None:
        if current_app.excel_data.get('loaded', False):
            current_app.search_service = SearchService(current_app.excel_data)
        else:
            current_app.search_service = None
    search_service = current_app.search_service
    price_calculator = PriceCalculator()
    html_generator = HtmlGenerator(price_calculator)
    
    return user_service, search_service, shopping_list_service, price_calculator, html_generator


def api_response(success=True, data=None, message=None, error=None, status_code=200):
    """Create standardized API response."""
    response = {
        'success': success,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    if error:
        response['error'] = error
    
    return jsonify(response), status_code


@api_bp.route('/products', methods=['GET'])
def get_all_products():
    """
    Get all products for client-side search.
    Returns lightweight product data optimized for search performance.
    """
    try:
        # Check if data is still loading
        if current_app.excel_data.get('loading', False):
            return api_response(
                success=False,
                error="Products are still loading, please try again in a moment",
                status_code=503
            )
        
        # Use ProductService only - no Excel fallback
        products = []
        if hasattr(current_app, 'product_service') and current_app.product_service:
            try:
                products = current_app.product_service.get_all_products()
                logger.info(f"Retrieved {len(products)} products from ProductService")
            except Exception as e:
                logger.error(f"ProductService failed: {str(e)}")
                return api_response(
                    success=False,
                    error="ProductService unavailable",
                    status_code=503
                )
        else:
            # Use excel_data structure (populated from Firestore)
            products = current_app.excel_data.get('products', [])
        
        # Create lightweight product data for client-side search
        product_data = []
        for product in products:
            # Only include essential data for search results
            product_dict = {
                'id': product.menora_id,
                'hebrew': product.descriptions.hebrew if product.descriptions else '',
                'english': product.descriptions.english if product.descriptions else '',
                'category': product.category,
                'supplier_code': product.supplier_code,
                'image_url': product.image_url,
                'has_image': product.has_image,
                'price': product.pricing.price if product.pricing else None,
                'currency': product.pricing.currency if product.pricing else 'ILS'
            }
            
            # Add specifications if available  
            if product.specifications:
                product_dict['type'] = product.specifications.type
                product_dict['material'] = product.specifications.material
                product_dict['height'] = product.specifications.height
                product_dict['width'] = product.specifications.width
                product_dict['thickness'] = product.specifications.thickness
            
            product_data.append(product_dict)
        
        return api_response(
            success=True,
            data={
                'products': product_data,
                'count': len(product_data)
            },
            message=f"Retrieved {len(product_data)} products"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        return api_response(
            success=False,
            error=f"Failed to retrieve products: {str(e)}",
            status_code=500
        )


@api_bp.route('/images/status', methods=['GET'])
def get_image_status():
    """
    Check if background image extraction is complete.
    """
    try:
        # Access the excel loader instance through current_app
        from app.services.excel_loader import ExcelLoader
        
        # Check if we have access to the excel loader instance
        # For now, just return a simple status since we can't easily access the instance
        return api_response(
            success=True,
            data={
                'images_loaded': True,  # Assume loaded for now
                'total_images': 0
            },
            message="Image status retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error getting image status: {str(e)}")
        return api_response(
            success=False,
            error=f"Failed to get image status: {str(e)}",
            status_code=500
        )


def require_session():
    """Validate session and return user."""
    session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not session_id:
        return None, api_response(False, error={'code': 'AUTH_MISSING', 'message': 'Authorization header required'}, status_code=401)
    
    user_service, _, _, _, _ = get_services()
    user = user_service.validate_session(session_id)
    
    if not user:
        return None, api_response(False, error={'code': 'AUTH_INVALID', 'message': 'Invalid or expired session'}, status_code=401)
    
    return user, None


# Authentication endpoints

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint."""
    try:
        data = request.get_json()
        if not data:
            return api_response(False, error={'code': 'INVALID_DATA', 'message': 'JSON data required'}, status_code=400)
        
        user_code = data.get('userCode', '').strip()
        
        if not user_code:
            return api_response(False, error={'code': 'INVALID_INPUT', 'message': 'User code is required'}, status_code=400)
        
        user_service, _, _, _, _ = get_services()
        
        if not user_service.is_valid_user_code(user_code):
            return api_response(False, error={'code': 'INVALID_USER_CODE', 'message': 'Invalid user code format'}, status_code=400)
        
        auth_result = user_service.authenticate_user(user_code)
        
        if auth_result:
            user, session_id = auth_result
            
            response_data = {
                'user': user.to_public_dict(),
                'sessionId': session_id,
                'expiresAt': user.session_expiry.isoformat() if user.session_expiry else None
            }
            
            return api_response(True, data=response_data, message='Login successful')
        else:
            return api_response(False, error={'code': 'AUTH_FAILED', 'message': 'Authentication failed'}, status_code=401)
    
    except Exception as e:
        logger.error(f"Error in API login: {str(e)}")
        return api_response(False, error={'code': 'INTERNAL_ERROR', 'message': 'Login failed'}, status_code=500)


@api_bp.route('/auth/validate', methods=['GET'])
def validate_session():
    """Validate session endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        response_data = {
            'valid': True,
            'userId': user.user_id,
            'expiresAt': user.session_expiry.isoformat() if user.session_expiry else None
        }
        
        return api_response(True, data=response_data)
    
    except Exception as e:
        logger.error(f"Error in API session validation: {str(e)}")
        return api_response(False, error={'code': 'VALIDATION_ERROR', 'message': 'Validation failed'}, status_code=500)


@api_bp.route('/auth/logout', methods=['POST'])
def logout():
    """User logout endpoint."""
    try:
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if session_id:
            user_service, _, _, _, _ = get_services()
            user_service.logout_user(session_id)
        
        return api_response(True, message='Successfully logged out')
    
    except Exception as e:
        logger.error(f"Error in API logout: {str(e)}")
        return api_response(False, error={'code': 'LOGOUT_ERROR', 'message': 'Logout failed'}, status_code=500)


# Search endpoints

@api_bp.route('/search/text', methods=['GET'])
def text_search():
    """Text search endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        query = request.args.get('q', '').strip()
        language = request.args.get('lang')
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        if not query:
            return api_response(False, error={'code': 'INVALID_QUERY', 'message': 'Search query required'}, status_code=400)
        
        _, search_service, _, _, _ = get_services()
        result = search_service.text_search(query, language, limit, offset)
        
        return api_response(True, data=result.to_dict())
    
    except Exception as e:
        logger.error(f"Error in API text search: {str(e)}")
        return api_response(False, error={'code': 'SEARCH_ERROR', 'message': 'Search failed'}, status_code=500)


@api_bp.route('/search/filter', methods=['POST'])
def filter_search():
    """Filter search endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        data = request.get_json()
        if not data:
            return api_response(False, error={'code': 'INVALID_DATA', 'message': 'JSON data required'}, status_code=400)
        
        filters = data.get('filters', {})
        limit = min(data.get('limit', 20), 100)
        offset = data.get('offset', 0)
        
        if not filters:
            return api_response(False, error={'code': 'INVALID_FILTERS', 'message': 'Search filters required'}, status_code=400)
        
        # Clean up empty filters
        clean_filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        
        _, search_service, _, _, _ = get_services()
        result = search_service.filter_search(clean_filters, limit, offset)
        
        return api_response(True, data=result.to_dict())
    
    except Exception as e:
        logger.error(f"Error in API filter search: {str(e)}")
        return api_response(False, error={'code': 'SEARCH_ERROR', 'message': 'Search failed'}, status_code=500)


@api_bp.route('/search/filters', methods=['GET'])
def get_filter_options():
    """Get filter options endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        _, search_service, _, _, _ = get_services()
        filter_options = search_service.get_available_filters()
        
        return api_response(True, data=filter_options)
    
    except Exception as e:
        logger.error(f"Error getting filter options: {str(e)}")
        return api_response(False, error={'code': 'FILTER_ERROR', 'message': 'Failed to get filter options'}, status_code=500)


@api_bp.route('/search/suggest', methods=['GET'])
def search_suggestions():
    """Search suggestions endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        query = request.args.get('q', '').strip()
        language = request.args.get('lang')
        
        if len(query) < 2:
            return api_response(True, data={'suggestions': []})
        
        _, search_service, _, _, _ = get_services()
        suggestions = search_service.get_suggestions(query, language, 5)
        
        return api_response(True, data={'suggestions': suggestions})
    
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        return api_response(False, error={'code': 'SUGGEST_ERROR', 'message': 'Failed to get suggestions'}, status_code=500)


# Shopping list endpoints

@api_bp.route('/shopping-lists', methods=['GET'])
def get_shopping_lists():
    """Get user shopping lists endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        _, _, shopping_list_service, _, _ = get_services()
        shopping_lists = shopping_list_service.get_user_shopping_lists(user)
        
        response_data = {
            'lists': [list_item.to_summary_dict() for list_item in shopping_lists],
            'defaultListId': user.default_list_id
        }
        
        return api_response(True, data=response_data)
    
    except Exception as e:
        logger.error(f"Error getting shopping lists: {str(e)}")
        return api_response(False, error={'code': 'LIST_ERROR', 'message': 'Failed to get shopping lists'}, status_code=500)


@api_bp.route('/shopping-lists/<list_id>', methods=['GET'])
def get_shopping_list_details(list_id):
    """Get shopping list details endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        _, _, shopping_list_service, _, _ = get_services()
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        
        if not shopping_list:
            return api_response(False, error={'code': 'LIST_NOT_FOUND', 'message': 'Shopping list not found'}, status_code=404)
        
        return api_response(True, data=shopping_list.to_dict())
    
    except Exception as e:
        logger.error(f"Error getting shopping list details: {str(e)}")
        return api_response(False, error={'code': 'LIST_ERROR', 'message': 'Failed to get shopping list'}, status_code=500)


@api_bp.route('/shopping-lists', methods=['POST'])
def create_shopping_list():
    """Create shopping list endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        data = request.get_json()
        if not data:
            return api_response(False, error={'code': 'INVALID_DATA', 'message': 'JSON data required'}, status_code=400)
        
        list_name = data.get('listName', '').strip()
        description = data.get('description', '').strip() or None
        
        if not list_name:
            return api_response(False, error={'code': 'INVALID_INPUT', 'message': 'List name required'}, status_code=400)
        
        _, _, shopping_list_service, _, _ = get_services()
        shopping_list = shopping_list_service.create_shopping_list(user, list_name, description)
        
        if shopping_list:
            return api_response(True, data=shopping_list.to_dict(), message='Shopping list created', status_code=201)
        else:
            return api_response(False, error={'code': 'CREATE_FAILED', 'message': 'Failed to create shopping list'}, status_code=500)
    
    except Exception as e:
        logger.error(f"Error creating shopping list: {str(e)}")
        return api_response(False, error={'code': 'CREATE_ERROR', 'message': 'Failed to create shopping list'}, status_code=500)


@api_bp.route('/shopping-lists/<list_id>/items', methods=['POST'])
def add_item_to_list(list_id):
    """Add item to shopping list endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        data = request.get_json()
        if not data:
            return api_response(False, error={'code': 'INVALID_DATA', 'message': 'JSON data required'}, status_code=400)
        
        menora_id = data.get('menoraId', '').strip()
        quantity = data.get('quantity', 1)
        notes = data.get('notes', '').strip() or None
        
        if not menora_id:
            return api_response(False, error={'code': 'INVALID_INPUT', 'message': 'Product ID required'}, status_code=400)
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return api_response(False, error={'code': 'INVALID_QUANTITY', 'message': 'Invalid quantity'}, status_code=400)
        
        _, _, shopping_list_service, _, _ = get_services()
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        
        if not shopping_list:
            return api_response(False, error={'code': 'LIST_NOT_FOUND', 'message': 'Shopping list not found'}, status_code=404)
        
        success = shopping_list_service.add_item_to_list(shopping_list, menora_id, quantity, notes)
        
        if success:
            # Find the added item
            added_item = None
            for item in shopping_list.items:
                if item.menora_id == menora_id:
                    added_item = item
                    break
            
            response_data = {
                'itemId': added_item.item_id if added_item else None,
                'menoraId': menora_id,
                'quantity': quantity,
                'addedAt': datetime.now(timezone.utc).isoformat()
            }
            
            return api_response(True, data=response_data, message='Item added successfully', status_code=201)
        else:
            return api_response(False, error={'code': 'ADD_FAILED', 'message': 'Failed to add item'}, status_code=500)
    
    except Exception as e:
        logger.error(f"Error adding item to list: {str(e)}")
        return api_response(False, error={'code': 'ADD_ERROR', 'message': 'Failed to add item'}, status_code=500)


@api_bp.route('/shopping-lists/<list_id>/generate-html', methods=['POST'])
def generate_html_list(list_id):
    """Generate HTML shopping list endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        data = request.get_json() or {}
        
        language = data.get('language', 'hebrew')
        include_images = data.get('includeImages', False)
        format_type = data.get('format', 'print')
        
        _, _, shopping_list_service, price_calculator, html_generator = get_services()
        shopping_list = shopping_list_service.get_shopping_list(list_id, user)
        
        if not shopping_list:
            return api_response(False, error={'code': 'LIST_NOT_FOUND', 'message': 'Shopping list not found'}, status_code=404)
        
        html_content = html_generator.generate_shopping_list_html(
            shopping_list, user, language, include_images, format_type
        )
        
        # Create download URL (in a real app, this would be stored and served)
        download_url = f"/shopping-list/{list_id}/generate-html?lang={language}&download=true"
        
        response_data = {
            'htmlContent': html_content,
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'downloadUrl': download_url
        }
        
        return api_response(True, data=response_data, message='HTML generated successfully')
    
    except Exception as e:
        logger.error(f"Error generating HTML: {str(e)}")
        return api_response(False, error={'code': 'HTML_ERROR', 'message': 'Failed to generate HTML'}, status_code=500)


# Product endpoints

@api_bp.route('/products/<menora_id>', methods=['GET'])
def get_product_details(menora_id):
    """Get product details endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        _, search_service, _, _, _ = get_services()
        product = search_service.get_product_by_id(menora_id)
        
        if not product:
            return api_response(False, error={'code': 'PRODUCT_NOT_FOUND', 'message': 'Product not found'}, status_code=404)
        
        return api_response(True, data=product.to_dict())
    
    except Exception as e:
        logger.error(f"Error getting product details: {str(e)}")
        return api_response(False, error={'code': 'PRODUCT_ERROR', 'message': 'Failed to get product'}, status_code=500)


@api_bp.route('/products/calculate-price', methods=['POST'])
def calculate_pricing():
    """Calculate pricing endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        data = request.get_json()
        if not data:
            return api_response(False, error={'code': 'INVALID_DATA', 'message': 'JSON data required'}, status_code=400)
        
        items = data.get('items', [])
        
        if not items:
            return api_response(False, error={'code': 'INVALID_INPUT', 'message': 'Items list required'}, status_code=400)
        
        _, search_service, shopping_list_service, price_calculator, _ = get_services()
        
        calculated_items = []
        subtotal = 0.0
        
        for item_data in items:
            menora_id = item_data.get('menoraId', '')
            quantity = item_data.get('quantity', 1)
            
            if not menora_id:
                continue
            
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    continue
            except (ValueError, TypeError):
                continue
            
            product = search_service.get_product_by_id(menora_id)
            if product:
                price_info = price_calculator.calculate_item_price(product, quantity)
                
                calculated_items.append({
                    'menoraId': menora_id,
                    'quantity': quantity,
                    'unitPrice': price_info['unit_price'],
                    'totalPrice': price_info['total_price'],
                    'appliedDiscount': 'bulk_discount' if price_info['bulk_discount_applied'] else None
                })
                
                subtotal += price_info['total_price']
        
        # Calculate summary
        tax = subtotal * 0.17  # Israeli VAT
        total = subtotal + tax
        
        response_data = {
            'items': calculated_items,
            'summary': {
                'subtotal': round(subtotal, 2),
                'discount': 0.0,  # Could add discount logic here
                'tax': round(tax, 2),
                'total': round(total, 2),
                'currency': 'ILS'
            }
        }
        
        return api_response(True, data=response_data)
    
    except Exception as e:
        logger.error(f"Error calculating pricing: {str(e)}")
        return api_response(False, error={'code': 'PRICING_ERROR', 'message': 'Failed to calculate pricing'}, status_code=500)


# Admin endpoints (optional)

@api_bp.route('/admin/refresh-data', methods=['POST'])
def refresh_data():
    """Refresh Firestore data cache endpoint."""
    try:
        # In a production app, you'd check admin permissions here
        # For now, allow any authenticated user to refresh data
        
        user, error_response = require_session()
        if error_response:
            return error_response
        
        # Clear ProductService cache to force reload from Firestore
        if hasattr(current_app, 'product_service') and current_app.product_service:
            current_app.product_service.clear_cache()
            
            # Reload products from Firestore
            products = current_app.product_service.get_all_products()
            
            # Update application cache
            current_app.excel_data['products'] = products
            current_app.excel_data['loaded'] = True
            
            # Reinitialize search service
            from app.services.search_service import SearchService
            current_app.search_service = SearchService(current_app.excel_data)
            
            response_data = {
                'productsLoaded': len(products),
                'loadTime': 'N/A',
                'lastRefresh': datetime.now(timezone.utc).isoformat(),
                'dataSource': 'firestore'
            }
            
            return api_response(True, data=response_data, message='Firestore data refreshed successfully')
        else:
            return api_response(False, error={'code': 'SERVICE_UNAVAILABLE', 'message': 'ProductService not available'}, status_code=503)
    
    except Exception as e:
        logger.error(f"Error refreshing data: {str(e)}")
        return api_response(False, error={'code': 'REFRESH_ERROR', 'message': 'Failed to refresh data'}, status_code=500)


@api_bp.route('/admin/stats', methods=['GET'])
def get_statistics():
    """Get system statistics endpoint."""
    try:
        user, error_response = require_session()
        if error_response:
            return error_response
        
        user_service, search_service, shopping_list_service, _, _ = get_services()
        
        # Get various statistics
        user_stats = user_service.firebase.get_user_statistics()
        list_stats = shopping_list_service.get_list_statistics()
        search_stats = search_service.get_statistics()
        
        response_data = {
            'users': user_stats,
            'shoppingLists': list_stats,
            'searches': {
                'totalProducts': search_stats['total_products'],
                'withPricing': search_stats['with_pricing']
            },
            'system': {
                'dataLastRefreshed': current_app.excel_data.get('loaded_at', '').isoformat() if hasattr(current_app, 'excel_data') else None,
                'uptime': 'N/A',  # Would implement actual uptime tracking
                'memoryUsage': 'N/A'  # Would implement actual memory monitoring
            }
        }
        
        return api_response(True, data=response_data)
    
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return api_response(False, error={'code': 'STATS_ERROR', 'message': 'Failed to get statistics'}, status_code=500)


@api_bp.route('/data/loading-status', methods=['GET'])
def get_loading_status():
    """Get product data loading status."""
    try:
        excel_data = getattr(current_app, 'excel_data', {})
        product_service = getattr(current_app, 'product_service', None)
        
        status_data = {
            'loading': excel_data.get('loading', False),
            'loaded': excel_data.get('loaded', False),
            'syncing': excel_data.get('syncing', False),
            'productCount': len(excel_data.get('products', [])),
            'hasSearchService': current_app.search_service is not None,
            'hasProductService': product_service is not None,
            'usingFirestore': product_service is not None and product_service.is_available(),
            'firestoreOnly': True
        }
        
        # Add ProductService cache stats if available
        if product_service:
            try:
                cache_stats = product_service.get_cache_stats()
                status_data['productService'] = {
                    'available': product_service.is_available(),
                    'cacheStats': cache_stats
                }
            except Exception as e:
                logger.warning(f"Error getting ProductService stats: {str(e)}")
                status_data['productService'] = {
                    'available': product_service.is_available(),
                    'error': str(e)
                }
        
        return api_response(True, data=status_data)
    
    except Exception as e:
        logger.error(f"Error getting loading status: {str(e)}")
        return api_response(False, error={'code': 'STATUS_ERROR', 'message': 'Failed to get loading status'}, status_code=500)


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run."""
    try:
        excel_data = getattr(current_app, 'excel_data', {})
        product_service = getattr(current_app, 'product_service', None)
        
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'dataLoading': excel_data.get('loading', False),
            'dataLoaded': excel_data.get('loaded', False),
            'dataSyncing': excel_data.get('syncing', False),
            'productCount': len(excel_data.get('products', [])),
            'firestoreAvailable': product_service is not None and product_service.is_available(),
            'dataSource': 'firestore',
            'firestoreOnly': True
        }
        
        return api_response(True, data=health_data)
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return api_response(False, error={'code': 'HEALTH_ERROR', 'message': 'Health check failed'}, status_code=500)