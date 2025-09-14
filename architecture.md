# Cable Tray Online Store - System Architecture

## 1. Architecture Overview

### 1.1 High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API      │    │   PostgreSQL    │
│   (Templates)   │◄──►│   Application    │◄──►│   Database      │
│ HTML Shopping   │    │                  │    │ • Products      │
│     Lists       │    └─────────────────┘    │ • Users         │
└─────────────────┘             │             │ • Shopping Lists│
                                 ▼             │ • Sessions      │
                    ┌─────────────────────────┐ └─────────────────┘
                    │ Excel Data Loader       │
                    │ (Startup Process)       │
                    │ • Load Products to DB    │
                    │ • Update Existing        │
                    │ • Show Loading State     │
                    └─────────────────────────┘
```

### 1.2 Architecture Principles
- **Separation of Concerns**: Clear separation between presentation, business logic, and data layers
- **Scalability**: Designed to handle growing product catalogs and user base
- **Maintainability**: Modular design with well-defined interfaces
- **Performance**: Optimized for fast search and data retrieval
- **Reliability**: Error handling and data validation at all layers

## 2. System Components

### 2.1 Presentation Layer (Frontend)

#### 2.1.1 Flask Templates
- **Technology**: Jinja2 templating engine
- **Responsibilities**:
  - Render HTML pages with dynamic content
  - Handle bilingual content (Hebrew/English)
  - Provide responsive user interface
  - Client-side form validation

#### 2.1.2 Static Assets
- **CSS**: Bootstrap + custom styles for bilingual support
- **JavaScript**: jQuery for dynamic interactions, AJAX for search
- **Images**: Product images, icons, UI elements

#### 2.1.3 Key Pages
- **Home Page**: Search interface and navigation
- **Search Results**: Product listing with filtering
- **Admin Panel**: File upload and data management

### 2.2 Application Layer (Flask API)

#### 2.2.1 Route Handlers
```
app/routes/
├── main.py          # Home page and general routes
├── search.py        # Search functionality routes
├── admin.py         # Administrative routes
└── api.py           # JSON API endpoints
```

#### 2.2.2 Business Logic Services
```
app/services/
├── excel_loader.py       # Excel file loading and database population
├── database_service.py  # PostgreSQL database operations
├── search_service.py     # Search logic across PostgreSQL data
├── shopping_list_service.py # User shopping list management
├── price_calculator.py   # Pricing and calculation logic
├── user_service.py       # User code authentication and management
└── product_service.py    # Product management and queries
```

#### 2.2.3 Data Models
```
app/models/
├── product.py           # Product data model (from Excel)
├── shopping_list.py     # User shopping list model
├── shopping_item.py     # Individual shopping list item
├── user.py              # User code and session model
└── search_result.py     # Search result wrapper
```

### 2.3 Data Layer

#### 2.3.1 PostgreSQL Database
- **Primary Database**: Relational database for all application data
- **Tables**: products, users, shopping_lists, user_sessions
- **Benefits**: ACID compliance, complex queries, data integrity, scalability

#### 2.3.2 Excel Data Loading Process
- **Excel Files**: Stored as static files, read during startup
- **Database Population**: Products loaded from Excel into PostgreSQL on app startup
- **Loading State**: Application shows loading screen until data is fully loaded
- **Update Strategy**: Existing products updated with new prices/data, no duplicates created

## 3. Data Flow Architecture

### 3.1 Excel Data Loading Flow (Startup Process)
```
Excel Files → Validation → Parsing → Data Mapping → PostgreSQL Database → Search Ready
     │             │          │           │              │                    │
     ▼             ▼          ▼           ▼              ▼                    ▼
  File Access   Schema      Extract     Transform     Database              App Ready
  Check         Check       Data        to SQL       Population            (No Loading)
```

### 3.2 Search Processing Flow
```
User Query → Input Validation → Search Service → PostgreSQL Query → Result Processing → Response
     │              │               │                │                  │              │
     ▼              ▼               ▼                ▼                  ▼              ▼
  Text/Filter   Sanitization   Database Query    SQL Execution     Format Results   JSON/HTML
                                               (Fast Indexed)
```

### 3.3 Shopping List Management Flow
```
Add Item → Validation → Shopping List Update → PostgreSQL Save → HTML Generation
    │           │              │                    │                │
    ▼           ▼              ▼                    ▼                ▼
 Item Check  Quantity     User's List          Persist          Generate
            Validation    Modification         Changes         HTML Output
```

## 4. Database Design

### 4.1 Firestore Collections Structure

#### 4.1.1 Products Collection
```javascript
products/{productId}
{
  menoraId: "string",           // Menora catalog number
  supplierCode: "string",       // Supplier catalog number
  descriptions: {
    hebrew: "string",
    english: "string"
  },
  category: "string",
  specifications: {
    type: "string",
    height: "number",
    width: "number", 
    thickness: "number",
    galvanization: "string"
  },
  supplier: "reference",         // Reference to suppliers collection
  createdAt: "timestamp",
  updatedAt: "timestamp",
  active: "boolean"
}
```

#### 4.1.2 Prices Collection
```javascript
prices/{priceId}
{
  productId: "reference",        // Reference to products collection
  supplierId: "reference",       // Reference to suppliers collection
  price: "number",
  currency: "string",
  validFrom: "timestamp",
  validTo: "timestamp",
  version: "number"
}
```

#### 4.1.3 Suppliers Collection
```javascript
suppliers/{supplierId}
{
  name: "string",
  code: "string",               // HOLDEE, etc.
  contactInfo: {
    email: "string",
    phone: "string"
  },
  active: "boolean"
}
```

### 4.2 Indexing Strategy
- **Compound Indexes**: For multi-field searches (type + height + width)
- **Text Indexes**: For full-text search in descriptions
- **Range Indexes**: For numerical fields (price, dimensions)

## 5. Security Architecture

### 5.1 Authentication & Authorization
- **Admin Access**: Protected routes for file upload and data management
- **Rate Limiting**: Prevent abuse of search functionality
- **Input Validation**: Sanitize all user inputs

### 5.2 Data Security
- **Firebase Security Rules**: Control access to Firestore collections
- **File Upload Validation**: Check file types and sizes
- **SQL Injection Prevention**: Use parameterized queries

## 6. Performance Optimization

### 6.1 Caching Strategy
- **Search Results**: Cache frequent searches
- **Product Data**: Cache product information
- **Static Content**: Browser caching for assets

### 6.2 Database Optimization
- **Efficient Queries**: Use appropriate indexes
- **Pagination**: Limit result sets
- **Batch Operations**: For bulk data processing

### 6.3 Frontend Optimization
- **Lazy Loading**: Load results incrementally
- **Debounced Search**: Reduce API calls during typing
- **Compressed Assets**: Minified CSS/JS

## 7. Error Handling & Logging

### 7.1 Error Handling Layers
```
Frontend Validation → Flask Route Error Handling → Service Layer Exceptions → Database Errors
       │                        │                         │                        │
       ▼                        ▼                         ▼                        ▼
  User Messages          HTTP Error Codes           Business Logic         Connection
                                                      Exceptions              Issues
```

### 7.2 Logging Strategy
- **Application Logs**: Flask request/response logging
- **Error Logs**: Exception tracking and stack traces
- **Audit Logs**: Data modification tracking
- **Performance Logs**: Query execution times

## 8. Deployment Architecture

### 8.1 Development Environment
```
Local Development
├── Flask Development Server
├── Local Firebase Emulator
├── Excel Test Files
└── Development Database
```

### 8.2 Production Environment
```
Cloud Deployment
├── Flask Application (Cloud Run/App Engine)
├── Firebase Firestore (Production)
├── Cloud Storage (File uploads)
└── Load Balancer (if needed)
```

## 9. Integration Points

### 9.1 Firebase SDK Integration
- **Authentication**: Firebase Auth (if user accounts needed)
- **Firestore**: Database operations
- **Cloud Storage**: File uploads
- **Analytics**: Usage tracking

### 9.2 Excel Processing Integration
- **pandas**: Data manipulation and analysis
- **openpyxl**: Excel file reading/writing
- **xlrd**: Legacy Excel format support

## 10. Scalability Considerations

### 10.1 Horizontal Scaling
- **Stateless Application**: Enable multiple Flask instances
- **Database Scaling**: Firestore automatic scaling
- **Load Distribution**: Use load balancer for multiple instances

### 10.2 Performance Monitoring
- **Response Time Monitoring**: Track API response times
- **Database Performance**: Monitor query execution
- **User Analytics**: Track search patterns and usage

## 11. Backup & Recovery

### 11.1 Data Backup Strategy
- **Firestore Backup**: Automated daily backups
- **Excel File Archive**: Store original uploaded files
- **Configuration Backup**: Application settings and schemas

### 11.2 Disaster Recovery
- **Recovery Procedures**: Step-by-step restoration process
- **RTO/RPO Targets**: Recovery time and data loss objectives
- **Testing**: Regular backup restoration testing

## 12. Future Architecture Enhancements

### 12.1 Microservices Migration
- **Search Service**: Dedicated search microservice
- **File Processing Service**: Separate Excel processing
- **Authentication Service**: Centralized user management

### 12.2 Advanced Features
- **Real-time Updates**: WebSocket integration for live pricing
- **Machine Learning**: Predictive search and recommendations
- **API Gateway**: External API access with rate limiting