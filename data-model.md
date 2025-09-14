# Cable Tray Online Store - Data Model Specification

## 1. Excel File Data Models (Read-Only Database)

### 1.1 Shopping List File ("New shopping list.xlsx") - PRIMARY DATABASE

#### 1.1.1 Sheet: "complete cable tray lookup" - MASTER PRODUCT DATABASE
**Purpose**: Master lookup table containing all basic item descriptions for the cable tray system.
**Access Mode**: READ-ONLY - Never modified, only loaded into memory for searches.

**Expected Structure**:
```
Column A: Product Type (TYPE)
Column B: Height (H)
Column C: Width (W) 
Column D: Thickness (T)
Column E: Galvanization (G)
Column F: Menora Catalog Number
Column G: Hebrew Description
Column H: English Description
Column I: Supplier Code (HOLDEE)
Column J: Additional Specifications
```

**Data Types**:
- **Product Type**: String (Cable Tray, Connector, Support, etc.)
- **Height**: Number (50, 75, 100, 200)
- **Width**: Number (various widths in mm)
- **Thickness**: Number (material thickness in mm)
- **Galvanization**: String (Hot Dip, Electro, None, etc.)
- **Catalog Numbers**: String (alphanumeric codes)
- **Descriptions**: String (UTF-8 for Hebrew support)

#### 1.1.2 Sheet: "cat no. conversion table" (Example/Demo)
**Purpose**: Demonstrates conversion from supplier input to standardized format.

**Input Format (Columns A-F)**:
```
Column A: Supplier Part Number
Column B: Supplier Description
Column C: Dimensions
Column D: Material Info
Column E: Additional Specs
Column F: Supplier Notes
```

**Output Format**:
```
Supplier Code: HOLDEE (standardized supplier identifier)
English Description: Standardized English product name
Hebrew Description: Standardized Hebrew product name
```

### 1.2 Price Table File ("Vered Price Table.xlsx") - PRICING DATABASE

#### 1.2.1 Main Price Sheets (by Height) - READ-ONLY PRICING DATA
**Sheet Names**: "Height_50", "Height_75", "Height_100", "Height_200"
**Access Mode**: READ-ONLY - Price data loaded into memory, never modified

**Expected Structure (Columns A-F)**:
```
Column A: Supplier Part Number
Column B: Width (mm)
Column C: Thickness (mm)
Column D: Galvanization Type
Column E: Unit Price
Column F: Supplier Notes/Specifications
```

**Additional Columns (Generated)**:
```
Column G: Menora Catalog Number (from lookup)
Column H: Hebrew Description (from lookup)
Column I: English Description (from lookup)
Column J: Category/Type (from lookup)
```

#### 1.2.2 Accessory Sheets
**Expected Sheets**:
- "Connectors"
- "Supports" 
- "Accessories"
- "Fittings"

**Structure Similar to Main Sheets**:
```
Column A: Supplier Part Number
Column B: Product Specifications
Column C: Material/Finish
Column D: Unit Price
Column E: Compatibility Notes
Column F: Additional Info
```

## 2. Firebase Firestore Data Models (User Data Only)

### 2.1 Shopping Lists Collection (`shopping_lists`)
```javascript
shopping_lists/{listId}
{
  // User Information
  userId: "user_ABC123",                  // User's unique login code
  userCode: "ABC123",                     // Display-friendly user code
  
  // List Information
  listName: "My Cable Tray Order",        // User-defined list name
  description: "Office building project", // Optional description
  
  // Shopping Items
  items: [
    {
      // Product Identifiers (from Excel data)
      menoraId: "MEN-CT-50-200-1.5-HD",
      supplierCode: "HOLDEE-CT50200",
      
      // Product Details (cached from Excel for fast display)
      descriptions: {
        hebrew: "מגש כבלים 50x200x1.5 מגולוון חם",
        english: "Cable Tray 50x200x1.5 Hot Dip Galvanized"
      },
      
      // Order Details
      quantity: 10,                       // User-specified quantity
      unitPrice: 45.50,                   // Price from Excel pricing data
      totalPrice: 455.00,                 // Calculated: quantity × unitPrice
      
      // Item Metadata
      addedAt: Timestamp,                 // When item was added to list
      notes: "For main corridor"          // Optional user notes
    }
  ],
  
  // List Totals
  summary: {
    totalItems: 5,                        // Count of different items
    totalQuantity: 25,                    // Sum of all quantities
    totalPrice: 1250.00,                  // Sum of all totalPrices
    currency: "ILS"                       // Currency
  },
  
  // List Status
  status: "active",                       // active, completed, archived
  
  // HTML Output
  htmlGenerated: true,                    // Whether HTML version exists
  lastHtmlGeneration: Timestamp,          // When HTML was last generated
  
  // Metadata
  createdAt: Timestamp,
  updatedAt: Timestamp,
  version: 1                             // List version for optimistic locking
}
```

### 2.2 Users Collection (`users`)
```javascript
users/{userId}
{
  // User Identification
  userCode: "ABC123",                    // User's unique login code
  displayName: "ABC123",                 // Display name (same as code)
  
  // User Preferences
  preferredLanguage: "hebrew",           // hebrew, english
  defaultCurrency: "ILS",                // Default currency
  
  // Shopping Lists References
  activeLists: [                         // References to active shopping lists
    "shopping_lists/list_001",
    "shopping_lists/list_002"
  ],
  defaultListId: "shopping_lists/list_001", // Default/current shopping list
  
  // Usage Statistics
  stats: {
    totalLists: 5,                      // Total lists created
    totalItems: 150,                    // Total items ever added
    lastLoginAt: Timestamp,             // Last access time
    createdAt: Timestamp                // Account creation
  },
  
  // Session Management
  currentSession: "session_xyz",         // Current session ID
  sessionExpiry: Timestamp,              // When session expires
  
  // Metadata
  active: true,                          // User account status
  createdAt: Timestamp,
  updatedAt: Timestamp
}
```

### 2.3 User Sessions Collection (`user_sessions`)
```javascript
user_sessions/{sessionId}
{
  // User Reference
  userId: "users/user_ABC123",           // Reference to user document
  userCode: "ABC123",                    // Quick lookup for user code
  
  // Session Information
  sessionId: "sess_uuid",                // Unique session identifier
  ipAddress: "192.168.1.1",              // User's IP address
  userAgent: "Mozilla/5.0...",           // Browser user agent
  
  // Current Shopping Context
  currentListId: "shopping_lists/list_001", // Currently active shopping list
  
  // Session Activity
  searches: [                            // Recent searches in this session
    {
      query: "cable tray 50",
      type: "text",                      // text, filter
      results: 25,
      timestamp: Timestamp
    }
  ],
  
  // Session Management
  createdAt: Timestamp,                  // Session start time
  lastActivity: Timestamp,               // Last user activity
  expiresAt: Timestamp,                  // When session expires
  active: true                           // Session status
}
```

### 2.4 Categories Collection (`categories`)
```javascript
categories/{categoryId}
{
  // Basic Information
  name: {
    hebrew: "מגשי כבלים",
    english: "Cable Trays"
  },
  code: "cable_tray",                    // Unique category code
  
  // Hierarchy
  parentCategory: null,                  // Reference to parent category
  subcategories: [                       // Array of subcategory references
    "categories/cable_tray_standard",
    "categories/cable_tray_perforated"
  ],
  level: 1,                             // Category level (1 = top level)
  
  // Search Configuration
  searchable: true,
  displayOrder: 1,                      // Display order in UI
  
  // Specifications Template
  specificationFields: [                // Available specification fields for this category
    {
      name: "height",
      type: "number",
      required: true,
      unit: "mm",
      displayName: { hebrew: "גובה", english: "Height" }
    },
    {
      name: "width", 
      type: "number",
      required: true,
      unit: "mm",
      displayName: { hebrew: "רוחב", english: "Width" }
    }
  ],
  
  // Metadata
  active: true,
  createdAt: Timestamp,
  updatedAt: Timestamp
}
```

### 2.5 Search Index Collection (`search_index`)
```javascript
search_index/{indexId}
{
  // Product Reference
  productId: "products/prod_123",
  menoraId: "MEN-CT-50-200-1.5-HD",
  
  // Searchable Content
  content: {
    hebrew: "מגש כבלים 50x200x1.5 מגולוון חם",
    english: "Cable Tray 50x200x1.5 Hot Dip Galvanized",
    combined: "cable tray 50 200 1.5 hot dip galvanized מגש כבלים מגולוון חם"
  },
  
  // Search Tokens (for better matching)
  tokens: [
    "cable", "tray", "50", "200", "1.5", "hot", "dip", "galvanized",
    "מגש", "כבלים", "מגולוון", "חם"
  ],
  
  // Faceted Search Fields
  facets: {
    category: "cable_tray",
    height: 50,
    width: 200,
    thickness: 1.5,
    galvanization: "hot_dip",
    material: "steel"
  },
  
  // Ranking/Scoring
  popularity: 0,                        // Search result popularity
  lastSearched: Timestamp,
  
  // Metadata
  updatedAt: Timestamp
}
```

### 2.6 User Sessions Collection (`user_sessions`) - Future Enhancement
```javascript
user_sessions/{sessionId}
{
  // Session Information
  sessionId: "sess_uuid",
  ipAddress: "192.168.1.1",
  userAgent: "Mozilla/5.0...",
  
  // Shopping Cart
  cart: [
    {
      productId: "products/prod_123",
      quantity: 5,
      unitPrice: 45.50,
      totalPrice: 227.50,
      addedAt: Timestamp
    }
  ],
  
  // Search History
  searches: [
    {
      query: "cable tray 50",
      type: "text",                      // text, filter
      results: 25,
      timestamp: Timestamp
    }
  ],
  
  // Metadata
  createdAt: Timestamp,
  lastActivity: Timestamp,
  expired: false
}
```

## 3. Data Relationships

### 3.1 Core Relationships
```
Products ←→ Prices (1:many)
Products ←→ Suppliers (many:1)
Products ←→ Categories (many:1)
Products ←→ Search Index (1:1)
Suppliers ←→ Prices (1:many)
```

### 3.2 Lookup Relationships
```
Excel Lookup Table → Products (source data)
Supplier Codes → Products (via supplier reference)
Menora IDs → Products (unique identifier)
Category Codes → Products (classification)
```

## 4. Data Validation Rules

### 4.1 Product Validation
- **menoraId**: Required, unique, alphanumeric
- **specifications.height**: Required, positive number, valid values [50,75,100,200]
- **specifications.width**: Required, positive number
- **descriptions**: Both Hebrew and English required, non-empty
- **category**: Required, must exist in categories collection

### 4.2 Price Validation  
- **price**: Required, positive number, max 2 decimal places
- **currency**: Required, valid ISO currency code
- **validFrom**: Required, cannot be in the past (for new prices)
- **productId**: Required, must reference existing product

### 4.3 Supplier Validation
- **code**: Required, unique, uppercase alphanumeric
- **name**: Required, non-empty string
- **contactInfo.email**: Optional, valid email format if provided

## 5. Index Strategy

### 5.1 Firestore Indexes
```
// Compound Indexes for Search
products: [category, active], [specifications.height, specifications.width], [searchTerms.combined]

// Compound Indexes for Filtering  
products: [category, specifications.type, active]
products: [specifications.height, specifications.width, specifications.thickness]

// Price Queries
prices: [productId, active, validFrom], [supplierId, active]

// Search Optimization
search_index: [facets.category, facets.height], [tokens array]
```

### 5.2 Search Optimization
- **Full-text search**: Use search_index collection with tokenized content
- **Faceted search**: Pre-computed facet values for filtering
- **Autocomplete**: Token-based matching for search suggestions

## 6. Data Migration Strategy

### 6.1 Excel to Firestore Migration
```
1. Parse Excel files → Validate data → Transform to Firestore format
2. Create/update products → Create/update prices → Update search index
3. Validate relationships → Generate reports → Commit changes
```

### 6.2 Data Versioning
- Track data versions for audit trails
- Maintain previous versions for rollback capability
- Log all data modification operations

## 7. Performance Considerations

### 7.1 Query Optimization
- Use composite indexes for multi-field searches
- Implement pagination for large result sets
- Cache frequently accessed data

### 7.2 Data Structure Optimization
- Denormalize frequently accessed fields
- Pre-compute search tokens and facets
- Use array fields for tags and search terms