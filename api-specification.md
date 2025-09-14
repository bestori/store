# Cable Tray Online Store - API Specification

## 1. API Overview

### 1.1 Base URL
```
Development: http://localhost:5000/api/v1
Production: https://your-domain.com/api/v1
```

### 1.2 Authentication
- **User Code Based**: Users authenticate using unique codes
- **Session Management**: Server-side sessions with expiration
- **No Registration**: Simple code-based access system

### 1.3 Response Format
```json
{
  "success": true,
  "data": { ... },
  "message": "Success message",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 1.4 Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": { ... }
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 2. Authentication Endpoints

### 2.1 User Login
```http
POST /auth/login
Content-Type: application/json

{
  "userCode": "ABC123"
}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "user": {
      "userId": "user_ABC123",
      "userCode": "ABC123",
      "preferredLanguage": "hebrew",
      "activeLists": ["shopping_lists/list_001"],
      "defaultListId": "shopping_lists/list_001"
    },
    "sessionId": "sess_uuid",
    "expiresAt": "2024-01-01T12:00:00Z"
  }
}
```

### 2.2 Session Validation
```http
GET /auth/validate
Authorization: Bearer {sessionId}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "valid": true,
    "userId": "user_ABC123",
    "expiresAt": "2024-01-01T12:00:00Z"
  }
}
```

### 2.3 Logout
```http
POST /auth/logout
Authorization: Bearer {sessionId}
```

**Success Response (200)**:
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

## 3. Search Endpoints

### 3.1 Free Text Search
```http
GET /search/text?q={query}&lang={language}&limit={limit}&offset={offset}
Authorization: Bearer {sessionId}
```

**Parameters**:
- `q`: Search query (required)
- `lang`: Language preference (hebrew|english, optional)
- `limit`: Results per page (default: 20, max: 100)
- `offset`: Pagination offset (default: 0)

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "menoraId": "MEN-CT-50-200-1.5-HD",
        "supplierCode": "HOLDEE-CT50200",
        "descriptions": {
          "hebrew": "מגש כבלים 50x200x1.5 מגולוון חם",
          "english": "Cable Tray 50x200x1.5 Hot Dip Galvanized"
        },
        "specifications": {
          "type": "Cable Tray",
          "height": 50,
          "width": 200,
          "thickness": 1.5,
          "galvanization": "Hot Dip"
        },
        "price": 45.50,
        "currency": "ILS",
        "inStock": true
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 20,
      "offset": 0,
      "hasMore": true
    },
    "searchInfo": {
      "query": "cable tray 50",
      "executionTime": 0.045,
      "language": "english"
    }
  }
}
```

### 3.2 Filtered Search (Dropdown Parameters)
```http
POST /search/filter
Authorization: Bearer {sessionId}
Content-Type: application/json

{
  "filters": {
    "type": "Cable Tray",
    "height": 50,
    "width": 200,
    "thickness": 1.5,
    "galvanization": "Hot Dip"
  },
  "limit": 20,
  "offset": 0
}
```

**Success Response (200)**:
Same format as text search response.

### 3.3 Get Filter Options
```http
GET /search/filters
Authorization: Bearer {sessionId}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "type": ["Cable Tray", "Connector", "Support", "Accessory"],
    "height": [50, 75, 100, 200],
    "width": [100, 150, 200, 300, 400, 500, 600],
    "thickness": [1.0, 1.2, 1.5, 2.0, 2.5],
    "galvanization": ["Hot Dip", "Electro", "Stainless Steel", "Aluminum"]
  }
}
```

### 3.4 Search Suggestions
```http
GET /search/suggest?q={partial_query}&lang={language}
Authorization: Bearer {sessionId}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "suggestions": [
      "cable tray 50",
      "cable tray 50x200",
      "cable tray connectors"
    ]
  }
}
```

## 4. Shopping List Endpoints

### 4.1 Get User's Shopping Lists
```http
GET /shopping-lists
Authorization: Bearer {sessionId}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "lists": [
      {
        "listId": "list_001",
        "listName": "My Cable Tray Order",
        "description": "Office building project",
        "itemCount": 5,
        "totalPrice": 1250.00,
        "currency": "ILS",
        "status": "active",
        "createdAt": "2024-01-01T10:00:00Z",
        "updatedAt": "2024-01-01T11:30:00Z"
      }
    ],
    "defaultListId": "list_001"
  }
}
```

### 4.2 Get Shopping List Details
```http
GET /shopping-lists/{listId}
Authorization: Bearer {sessionId}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "listId": "list_001",
    "listName": "My Cable Tray Order",
    "description": "Office building project",
    "items": [
      {
        "itemId": "item_001",
        "menoraId": "MEN-CT-50-200-1.5-HD",
        "supplierCode": "HOLDEE-CT50200",
        "descriptions": {
          "hebrew": "מגש כבלים 50x200x1.5 מגולוון חם",
          "english": "Cable Tray 50x200x1.5 Hot Dip Galvanized"
        },
        "quantity": 10,
        "unitPrice": 45.50,
        "totalPrice": 455.00,
        "notes": "For main corridor",
        "addedAt": "2024-01-01T10:15:00Z"
      }
    ],
    "summary": {
      "totalItems": 5,
      "totalQuantity": 25,
      "totalPrice": 1250.00,
      "currency": "ILS"
    },
    "status": "active",
    "createdAt": "2024-01-01T10:00:00Z",
    "updatedAt": "2024-01-01T11:30:00Z"
  }
}
```

### 4.3 Create New Shopping List
```http
POST /shopping-lists
Authorization: Bearer {sessionId}
Content-Type: application/json

{
  "listName": "New Project List",
  "description": "Optional description"
}
```

**Success Response (201)**:
```json
{
  "success": true,
  "data": {
    "listId": "list_002",
    "listName": "New Project List",
    "description": "Optional description",
    "items": [],
    "summary": {
      "totalItems": 0,
      "totalQuantity": 0,
      "totalPrice": 0.00,
      "currency": "ILS"
    },
    "status": "active",
    "createdAt": "2024-01-01T12:00:00Z"
  }
}
```

### 4.4 Add Item to Shopping List
```http
POST /shopping-lists/{listId}/items
Authorization: Bearer {sessionId}
Content-Type: application/json

{
  "menoraId": "MEN-CT-50-200-1.5-HD",
  "quantity": 10,
  "notes": "Optional notes"
}
```

**Success Response (201)**:
```json
{
  "success": true,
  "data": {
    "itemId": "item_002",
    "menoraId": "MEN-CT-50-200-1.5-HD",
    "supplierCode": "HOLDEE-CT50200",
    "descriptions": {
      "hebrew": "מגש כבלים 50x200x1.5 מגולוון חם",
      "english": "Cable Tray 50x200x1.5 Hot Dip Galvanized"
    },
    "quantity": 10,
    "unitPrice": 45.50,
    "totalPrice": 455.00,
    "notes": "Optional notes",
    "addedAt": "2024-01-01T12:30:00Z"
  },
  "message": "Item added to shopping list successfully"
}
```

### 4.5 Update Item Quantity
```http
PATCH /shopping-lists/{listId}/items/{itemId}
Authorization: Bearer {sessionId}
Content-Type: application/json

{
  "quantity": 15,
  "notes": "Updated notes"
}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "itemId": "item_001",
    "quantity": 15,
    "unitPrice": 45.50,
    "totalPrice": 682.50,
    "notes": "Updated notes",
    "updatedAt": "2024-01-01T13:00:00Z"
  },
  "message": "Item updated successfully"
}
```

### 4.6 Remove Item from Shopping List
```http
DELETE /shopping-lists/{listId}/items/{itemId}
Authorization: Bearer {sessionId}
```

**Success Response (200)**:
```json
{
  "success": true,
  "message": "Item removed from shopping list successfully"
}
```

### 4.7 Generate HTML Shopping List
```http
POST /shopping-lists/{listId}/generate-html
Authorization: Bearer {sessionId}
Content-Type: application/json

{
  "language": "hebrew",
  "includeImages": false,
  "format": "print"
}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "htmlContent": "<html>...</html>",
    "generatedAt": "2024-01-01T14:00:00Z",
    "downloadUrl": "/downloads/shopping-list-ABC123-list001.html"
  }
}
```

### 4.8 Export Shopping List
```http
GET /shopping-lists/{listId}/export?format={format}&lang={language}
Authorization: Bearer {sessionId}
```

**Parameters**:
- `format`: Export format (html|pdf|csv)
- `lang`: Language (hebrew|english)

**Success Response (200)**:
Returns file download with appropriate Content-Type header.

## 5. Utility Endpoints

### 5.1 Get Product Details
```http
GET /products/{menoraId}
Authorization: Bearer {sessionId}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "menoraId": "MEN-CT-50-200-1.5-HD",
    "supplierCode": "HOLDEE-CT50200",
    "descriptions": {
      "hebrew": "מגש כבלים 50x200x1.5 מגולוון חם",
      "english": "Cable Tray 50x200x1.5 Hot Dip Galvanized"
    },
    "specifications": {
      "type": "Cable Tray",
      "height": 50,
      "width": 200,
      "thickness": 1.5,
      "galvanization": "Hot Dip",
      "material": "Steel"
    },
    "pricing": {
      "price": 45.50,
      "currency": "ILS",
      "bulkPricing": [
        { "minQty": 10, "price": 43.00 },
        { "minQty": 50, "price": 40.00 }
      ]
    },
    "availability": {
      "inStock": true,
      "leadTime": 7
    }
  }
}
```

### 5.2 Calculate Pricing
```http
POST /products/calculate-price
Authorization: Bearer {sessionId}
Content-Type: application/json

{
  "items": [
    {
      "menoraId": "MEN-CT-50-200-1.5-HD",
      "quantity": 10
    },
    {
      "menoraId": "MEN-CT-75-300-2.0-HD",
      "quantity": 5
    }
  ]
}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "menoraId": "MEN-CT-50-200-1.5-HD",
        "quantity": 10,
        "unitPrice": 43.00,
        "totalPrice": 430.00,
        "appliedDiscount": "bulk_10"
      },
      {
        "menoraId": "MEN-CT-75-300-2.0-HD",
        "quantity": 5,
        "unitPrice": 65.00,
        "totalPrice": 325.00,
        "appliedDiscount": null
      }
    ],
    "summary": {
      "subtotal": 755.00,
      "discount": 25.00,
      "tax": 128.35,
      "total": 883.35,
      "currency": "ILS"
    }
  }
}
```

## 6. Admin Endpoints (Optional)

### 6.1 Refresh Excel Data Cache
```http
POST /admin/refresh-data
Authorization: Bearer {adminToken}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "productsLoaded": 1250,
    "pricesLoaded": 1250,
    "loadTime": 2.34,
    "lastRefresh": "2024-01-01T15:00:00Z"
  },
  "message": "Excel data cache refreshed successfully"
}
```

### 6.2 Get System Statistics
```http
GET /admin/stats
Authorization: Bearer {adminToken}
```

**Success Response (200)**:
```json
{
  "success": true,
  "data": {
    "users": {
      "total": 150,
      "active": 45,
      "newToday": 5
    },
    "shoppingLists": {
      "total": 500,
      "active": 200,
      "completedToday": 25
    },
    "searches": {
      "totalToday": 1250,
      "averageResultTime": 0.045,
      "popularQueries": [
        "cable tray 50",
        "connectors",
        "supports"
      ]
    },
    "system": {
      "dataLastRefreshed": "2024-01-01T15:00:00Z",
      "uptime": "5 days, 12 hours",
      "memoryUsage": "45%"
    }
  }
}
```

## 7. WebSocket API (Real-time Features)

### 7.1 Shopping List Updates
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:5000/ws/shopping-list/{listId}');

// Listen for real-time updates
ws.onmessage = function(event) {
  const update = JSON.parse(event.data);
  console.log('Shopping list updated:', update);
};

// Message format
{
  "type": "item_added",
  "data": {
    "listId": "list_001",
    "item": { ... },
    "newTotal": 1705.00
  },
  "timestamp": "2024-01-01T16:00:00Z"
}
```

## 8. Error Codes

### 8.1 Authentication Errors
- `AUTH_INVALID_CODE`: Invalid user code
- `AUTH_SESSION_EXPIRED`: Session has expired
- `AUTH_SESSION_INVALID`: Invalid session token

### 8.2 Search Errors
- `SEARCH_INVALID_QUERY`: Invalid search query
- `SEARCH_NO_RESULTS`: No results found
- `SEARCH_TIMEOUT`: Search request timed out

### 8.3 Shopping List Errors
- `LIST_NOT_FOUND`: Shopping list not found
- `LIST_ITEM_NOT_FOUND`: Item not found in shopping list
- `LIST_ITEM_ALREADY_EXISTS`: Item already exists in list
- `LIST_CALCULATION_ERROR`: Error calculating prices

### 8.4 Product Errors
- `PRODUCT_NOT_FOUND`: Product not found
- `PRODUCT_PRICE_UNAVAILABLE`: Price information not available
- `PRODUCT_OUT_OF_STOCK`: Product is out of stock

### 8.5 System Errors
- `SYSTEM_ERROR`: General system error
- `DATA_REFRESH_FAILED`: Failed to refresh Excel data
- `DATABASE_ERROR`: Database operation failed
- `VALIDATION_ERROR`: Data validation failed

## 9. Rate Limiting

### 9.1 Rate Limits
- **Search API**: 100 requests per minute per user
- **Shopping List API**: 200 requests per minute per user
- **Authentication API**: 10 requests per minute per IP
- **Admin API**: 50 requests per minute per admin

### 9.2 Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## 10. API Versioning

### 10.1 Version Strategy
- **URL Versioning**: `/api/v1/`, `/api/v2/`
- **Backward Compatibility**: v1 maintained for 12 months after v2 release
- **Breaking Changes**: Only in new major versions

### 10.2 Current Version
- **Version**: 1.0
- **Release Date**: 2024-01-01
- **Support Until**: 2025-01-01 (minimum)