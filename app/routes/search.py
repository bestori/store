"""
Search routes for product search functionality.
"""

import logging
from flask import Blueprint, render_template, request, jsonify, current_app, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.services.search_service import SearchService
from app.routes.auth import login_required

search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)


def get_search_service() -> SearchService:
    """Get singleton search service instance from app."""
    if not hasattr(current_app, 'search_service') or current_app.search_service is None:
        if hasattr(current_app, 'database_service') and current_app.database_service:
            # Create search service with database
            current_app.search_service = SearchService(current_app.excel_data, database_service=current_app.database_service)
        else:
            raise RuntimeError("Database service not available")
    return current_app.search_service


@search_bp.route('/')
def search_page():
    """Main search page."""
    try:
        search_service = get_search_service()
        
        # Get user's preferred language
        preferred_language = session.get('preferred_language', 'hebrew')
        
        # Get filter options for dropdown (with Hebrew translations)
        filter_options = search_service.get_available_filters(preferred_language)
        
        # Get popular searches
        popular_searches = search_service.get_popular_searches()
        
        return render_template('search.html', 
                             filter_options=filter_options,
                             popular_searches=popular_searches,
                             preferred_language=preferred_language)
        
    except Exception as e:
        logger.error(f"Error loading search page: {str(e)}")
        return render_template('error.html', 
                             error_message="An error occurred loading the search page."), 500


@search_bp.route('/text', methods=['POST'])
def text_search():
    """Text search endpoint."""
    try:
        # Get search parameters
        query = request.json.get('query', '').strip()
        # Normalize language to support bilingual search when omitted or set to 'both'
        language_param = request.json.get('language', None)
        language = None if (language_param is None or str(language_param).lower() == 'both') else language_param
        limit = min(request.json.get('limit', 20), 100)  # Max 100 results
        offset = request.json.get('offset', 0)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        # Perform search
        search_service = get_search_service()
        result = search_service.text_search(query, language, limit, offset)
        
        return jsonify({
            'success': True,
            'data': result.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error in text search: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Search failed'
        }), 500


@search_bp.route('/filter', methods=['POST'])
def filter_search():
    """Filtered search endpoint."""
    try:
        # Get search parameters
        filters = request.json.get('filters', {})
        limit = min(request.json.get('limit', 20), 100)  # Max 100 results
        offset = request.json.get('offset', 0)
        
        if not filters:
            return jsonify({
                'success': False,
                'error': 'Search filters are required'
            }), 400
        
        # Clean up empty filters
        clean_filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        
        # Perform search
        search_service = get_search_service()
        result = search_service.filter_search(clean_filters, limit, offset)
        
        return jsonify({
            'success': True,
            'data': result.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error in filter search: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Search failed'
        }), 500


@search_bp.route('/combined', methods=['POST'])
def combined_search():
    """Combined text and filter search endpoint."""
    try:
        # Get search parameters
        query = request.json.get('query', '').strip()
        filters = request.json.get('filters', {})
        # Normalize language to support bilingual search when omitted or set to 'both'
        language_param = request.json.get('language', None)
        language = None if (language_param is None or str(language_param).lower() == 'both') else language_param
        limit = min(request.json.get('limit', 20), 100)  # Max 100 results
        offset = request.json.get('offset', 0)
        
        if not query and not filters:
            return jsonify({
                'success': False,
                'error': 'Either search query or filters are required'
            }), 400
        
        # Clean up empty filters
        clean_filters = {k: v for k, v in filters.items() if v is not None and v != ''} if filters else None
        clean_query = query if query else None
        
        # Perform search
        search_service = get_search_service()
        result = search_service.combined_search(clean_query, clean_filters, language, limit, offset)
        
        return jsonify({
            'success': True,
            'data': result.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error in combined search: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Search failed'
        }), 500


@search_bp.route('/suggest')
def search_suggestions():
    """Get search suggestions."""
    try:
        partial_query = request.args.get('q', '').strip()
        # Normalize language to support bilingual suggestions when omitted or set to 'both'
        lang_param = request.args.get('lang', None)
        language = None if (lang_param is None or str(lang_param).lower() == 'both') else lang_param
        max_suggestions = min(int(request.args.get('limit', 5)), 10)  # Max 10 suggestions
        
        if not partial_query or len(partial_query) < 2:
            return jsonify({
                'success': True,
                'data': {'suggestions': []}
            })
        
        search_service = get_search_service()
        suggestions = search_service.get_suggestions(partial_query, language, max_suggestions)
        
        return jsonify({
            'success': True,
            'data': {'suggestions': suggestions}
        })
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get suggestions'
        }), 500


@search_bp.route('/product/<product_id>')
def product_details(product_id: str):
    """Product details page."""
    try:
        search_service = get_search_service()
        
        # Find product by Menora ID
        product = search_service.get_product_by_id(product_id)
        
        if not product:
            return render_template('404.html'), 404
        
        # Get user's preferred language
        preferred_language = session.get('preferred_language', 'hebrew')
        
        # Get related products (same type) by filtering in-memory products list
        related_products = []
        if product.specifications and product.specifications.type:
            related_products = [
                p for p in search_service.products
                if (
                    p.specifications is not None and
                    p.specifications.type == product.specifications.type and
                    p.menora_id != product.menora_id
                )
            ][:6]  # Limit to 6 related products
        
        return render_template('product_detail.html', 
                             product=product,
                             related_products=related_products,
                             preferred_language=preferred_language)
        
    except Exception as e:
        logger.error(f"Error getting product details: {str(e)}")
        return render_template('error.html', 
                             error_message="An error occurred loading the product details."), 500


@search_bp.route('/api/product/<product_id>')
def product_details_api(product_id: str):
    """Get detailed product information via API."""
    try:
        search_service = get_search_service()
        product = search_service.get_product_by_id(product_id)
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': product.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting product details: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get product details'
        }), 500


@search_bp.route('/filters')
def get_filter_options():
    """Get available filter options."""
    try:
        search_service = get_search_service()
        filter_options = search_service.get_available_filters()
        
        return jsonify({
            'success': True,
            'data': {'filters': filter_options}
        })
        
    except Exception as e:
        logger.error(f"Error getting filter options: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get filter options'
        }), 500


@search_bp.route('/popular')
def popular_searches():
    """Get popular search terms."""
    try:
        limit = min(int(request.args.get('limit', 10)), 20)  # Max 20 terms
        
        search_service = get_search_service()
        popular_terms = search_service.get_popular_searches(limit)
        
        return jsonify({
            'success': True,
            'data': {'popular_searches': popular_terms}
        })
        
    except Exception as e:
        logger.error(f"Error getting popular searches: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get popular searches'
        }), 500


@search_bp.route('/statistics')
def search_statistics():
    """Get search service statistics."""
    try:
        search_service = get_search_service()
        stats = search_service.get_statistics()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting search statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get statistics'
        }), 500