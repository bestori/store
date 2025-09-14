"""
Security service for input validation, sanitization, and security checks.
"""

import re
import logging
import html
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import hashlib
import secrets

logger = logging.getLogger(__name__)


class SecurityService:
    """Service for handling security-related functionality."""
    
    # Validation patterns
    USER_CODE_PATTERN = re.compile(r'^[A-Za-z0-9]{3,20}$')
    MENORA_ID_PATTERN = re.compile(r'^[A-Za-z0-9\-]{2,50}$')
    LIST_NAME_PATTERN = re.compile(r'^.{1,100}$', re.DOTALL)
    DESCRIPTION_PATTERN = re.compile(r'^.{0,500}$', re.DOTALL)
    QUANTITY_PATTERN = re.compile(r'^\d{1,4}$')
    SEARCH_QUERY_PATTERN = re.compile(r'^.{1,200}$')
    
    # Language validation
    VALID_LANGUAGES = {'hebrew', 'english'}
    
    # Currency validation
    VALID_CURRENCIES = {'ILS', 'USD', 'EUR'}
    
    # Status validation
    VALID_LIST_STATUSES = {'active', 'completed', 'archived'}
    
    # Activity types validation
    VALID_ACTIVITY_TYPES = {
        'login', 'logout', 'search', 'list_created', 'list_updated', 
        'list_deleted', 'item_added', 'item_removed', 'item_updated',
        'list_exported', 'profile_updated'
    }
    
    @classmethod
    def validate_user_code(cls, user_code: str) -> bool:
        """
        Validate user code format.
        
        Args:
            user_code: User code to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not user_code or not isinstance(user_code, str):
            return False
        
        # Check pattern and length
        return bool(cls.USER_CODE_PATTERN.match(user_code.strip()))
    
    @classmethod
    def validate_menora_id(cls, menora_id: str) -> bool:
        """
        Validate Menora ID format.
        
        Args:
            menora_id: Menora ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not menora_id or not isinstance(menora_id, str):
            return False
        
        return bool(cls.MENORA_ID_PATTERN.match(menora_id.strip()))
    
    @classmethod
    def validate_list_name(cls, list_name: str) -> bool:
        """
        Validate shopping list name.
        
        Args:
            list_name: List name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not list_name or not isinstance(list_name, str):
            return False
        
        sanitized = cls.sanitize_text(list_name)
        return bool(cls.LIST_NAME_PATTERN.match(sanitized))
    
    @classmethod
    def validate_description(cls, description: Optional[str]) -> bool:
        """
        Validate description text.
        
        Args:
            description: Description to validate
            
        Returns:
            True if valid, False otherwise
        """
        if description is None:
            return True
        
        if not isinstance(description, str):
            return False
        
        sanitized = cls.sanitize_text(description)
        return bool(cls.DESCRIPTION_PATTERN.match(sanitized))
    
    @classmethod
    def validate_quantity(cls, quantity: Union[str, int]) -> bool:
        """
        Validate quantity value.
        
        Args:
            quantity: Quantity to validate
            
        Returns:
            True if valid, False otherwise
        """
        if isinstance(quantity, int):
            return 1 <= quantity <= 9999
        
        if isinstance(quantity, str) and cls.QUANTITY_PATTERN.match(quantity.strip()):
            try:
                qty = int(quantity.strip())
                return 1 <= qty <= 9999
            except ValueError:
                return False
        
        return False
    
    @classmethod
    def validate_search_query(cls, query: str) -> bool:
        """
        Validate search query.
        
        Args:
            query: Search query to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not query or not isinstance(query, str):
            return False
        
        sanitized = cls.sanitize_text(query)
        return bool(cls.SEARCH_QUERY_PATTERN.match(sanitized))
    
    @classmethod
    def validate_language(cls, language: str) -> bool:
        """
        Validate language preference.
        
        Args:
            language: Language to validate
            
        Returns:
            True if valid, False otherwise
        """
        return isinstance(language, str) and language.lower() in cls.VALID_LANGUAGES
    
    @classmethod
    def validate_currency(cls, currency: str) -> bool:
        """
        Validate currency code.
        
        Args:
            currency: Currency to validate
            
        Returns:
            True if valid, False otherwise
        """
        return isinstance(currency, str) and currency.upper() in cls.VALID_CURRENCIES
    
    @classmethod
    def validate_list_status(cls, status: str) -> bool:
        """
        Validate list status.
        
        Args:
            status: Status to validate
            
        Returns:
            True if valid, False otherwise
        """
        return isinstance(status, str) and status.lower() in cls.VALID_LIST_STATUSES
    
    @classmethod
    def validate_activity_type(cls, activity_type: str) -> bool:
        """
        Validate activity type.
        
        Args:
            activity_type: Activity type to validate
            
        Returns:
            True if valid, False otherwise
        """
        return isinstance(activity_type, str) and activity_type.lower() in cls.VALID_ACTIVITY_TYPES
    
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize text input to prevent XSS and other issues.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        if not isinstance(text, str):
            return ""
        
        # Remove null bytes and normalize
        sanitized = text.replace('\x00', '').strip()
        
        # HTML escape
        sanitized = html.escape(sanitized, quote=True)
        
        return sanitized
    
    @classmethod
    def validate_json_data(cls, data: Dict[str, Any], required_fields: List[str], 
                          optional_fields: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Validate JSON data structure and fields.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
            optional_fields: List of optional field names
            
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        if not isinstance(data, dict):
            errors.append("Invalid data format - expected JSON object")
            return {'errors': errors, 'warnings': warnings}
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif data[field] is None:
                errors.append(f"Field '{field}' cannot be null")
        
        # Check for unexpected fields
        allowed_fields = set(required_fields)
        if optional_fields:
            allowed_fields.update(optional_fields)
        
        for field in data:
            if field not in allowed_fields:
                warnings.append(f"Unexpected field: {field}")
        
        return {'errors': errors, 'warnings': warnings}
    
    @classmethod
    def validate_shopping_list_data(cls, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate shopping list creation/update data.
        
        Args:
            data: Shopping list data to validate
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        # Validate list name
        list_name = data.get('list_name')
        if not list_name:
            errors.append("List name is required")
        elif not cls.validate_list_name(list_name):
            errors.append("Invalid list name format (1-100 characters)")
        
        # Validate description (optional)
        description = data.get('description')
        if description is not None and not cls.validate_description(description):
            errors.append("Invalid description format (max 500 characters)")
        
        # Validate status (optional)
        status = data.get('status')
        if status is not None and not cls.validate_list_status(status):
            errors.append(f"Invalid status. Must be one of: {', '.join(cls.VALID_LIST_STATUSES)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    @classmethod
    def validate_shopping_item_data(cls, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate shopping item data.
        
        Args:
            data: Shopping item data to validate
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        # Validate Menora ID
        menora_id = data.get('menora_id')
        if not menora_id:
            errors.append("Product ID (Menora ID) is required")
        elif not cls.validate_menora_id(menora_id):
            errors.append("Invalid product ID format")
        
        # Validate quantity
        quantity = data.get('quantity')
        if quantity is None:
            errors.append("Quantity is required")
        elif not cls.validate_quantity(quantity):
            errors.append("Invalid quantity (must be 1-9999)")
        
        # Validate notes (optional)
        notes = data.get('notes')
        if notes is not None and not cls.validate_description(notes):
            errors.append("Invalid notes format (max 500 characters)")
        
        return {'errors': errors, 'warnings': warnings}
    
    @classmethod
    def check_rate_limit_headers(cls, request_headers: Dict[str, str]) -> bool:
        """
        Check for suspicious headers that might indicate abuse.
        
        Args:
            request_headers: HTTP headers from request
            
        Returns:
            True if headers look suspicious, False otherwise
        """
        suspicious_headers = [
            'x-forwarded-for',
            'x-real-ip',
            'x-cluster-client-ip',
            'cf-connecting-ip'
        ]
        
        # Check for multiple IPs (potential proxy abuse)
        for header in suspicious_headers:
            if header in request_headers:
                ip_value = request_headers[header]
                if ',' in ip_value:  # Multiple IPs
                    logger.warning(f"Multiple IPs detected in header {header}: {ip_value}")
                    return True
        
        return False
    
    @classmethod
    def generate_session_token(cls) -> str:
        """
        Generate a secure session token.
        
        Returns:
            Secure random token
        """
        return secrets.token_urlsafe(32)
    
    @classmethod
    def hash_user_code(cls, user_code: str) -> str:
        """
        Create a hash of user code for logging (privacy protection).
        
        Args:
            user_code: User code to hash
            
        Returns:
            Hashed user code
        """
        return hashlib.sha256(user_code.encode()).hexdigest()[:8]
    
    @classmethod
    def validate_filter_params(cls, params: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate search filter parameters.
        
        Args:
            params: Filter parameters to validate
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        valid_filters = {
            'type', 'height', 'width', 'thickness', 'galvanization'
        }
        
        for key, value in params.items():
            if key not in valid_filters:
                warnings.append(f"Unknown filter parameter: {key}")
                continue
            
            if not isinstance(value, (str, int, float)):
                errors.append(f"Invalid value type for filter '{key}'")
                continue
            
            # Convert to string and validate
            str_value = str(value).strip()
            if not str_value:
                warnings.append(f"Empty value for filter '{key}'")
                continue
            
            # Basic validation - no dangerous characters
            if re.search(r'[<>"\'\x00-\x1f]', str_value):
                errors.append(f"Invalid characters in filter '{key}'")
        
        return {'errors': errors, 'warnings': warnings}
    
    @classmethod
    def log_security_event(cls, event_type: str, user_code: Optional[str] = None, 
                          details: Optional[Dict[str, Any]] = None, severity: str = 'INFO'):
        """
        Log security-related events.
        
        Args:
            event_type: Type of security event
            user_code: User code involved (will be hashed)
            details: Additional details
            severity: Log severity level
        """
        log_data = {
            'event_type': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'severity': severity
        }
        
        if user_code:
            log_data['user_hash'] = cls.hash_user_code(user_code)
        
        if details:
            log_data['details'] = details
        
        log_level = getattr(logging, severity.upper(), logging.INFO)
        logger.log(log_level, f"Security event: {log_data}")


# Validation decorators
def validate_json(required_fields: List[str], optional_fields: Optional[List[str]] = None):
    """Decorator for validating JSON request data."""
    def decorator(f):
        from functools import wraps
        from flask import request, jsonify
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False, 
                        'error': 'Invalid JSON data'
                    }), 400
                
                validation_result = SecurityService.validate_json_data(
                    data, required_fields, optional_fields
                )
                
                if validation_result['errors']:
                    return jsonify({
                        'success': False,
                        'error': 'Validation failed',
                        'details': validation_result['errors']
                    }), 400
                
                # Attach validated data to request
                request.validated_data = data
                
                # Log warnings if any
                if validation_result['warnings']:
                    logger.warning(f"Validation warnings: {validation_result['warnings']}")
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Validation error: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': 'Validation error'
                }), 400
        
        return decorated_function
    return decorator