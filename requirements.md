# Cable Tray Online Store - Requirements Specification

## 1. Project Overview

### 1.1 Purpose
Build a Python Flask web application that uses Excel files as a **read-only database** for cable tray product data, providing a searchable online catalog where users can create and save personalized HTML shopping lists.

### 1.2 Scope
- Use Excel files as read-only data source (NO MODIFICATIONS, ONLY READING)
- Provide bilingual search functionality (Hebrew/English)
- Generate HTML shopping lists per user
- User identification via unique login codes
- Calculate pricing and totals for shopping lists
- Store user shopping lists in Firebase Firestore

## 2. Functional Requirements

### 2.1 Excel File Processing (Read-Only Database)

#### 2.1.1 Shopping List File ("New shopping list") - Master Database
**File Structure:**
- **Sheet: "complete cable tray lookup"** - Master lookup table with all basic item descriptions (PRIMARY DATABASE)
- **Sheet: "cat no. conversion table"** - Example conversion from supplier input (columns A-F) to:
  - Supplier code (HOLDEE)
  - English description  
  - Hebrew description

**Processing Requirements:**
- **READ-ONLY ACCESS**: Parse and load data into memory for searches (NO FILE MODIFICATIONS)
- Map supplier codes to product descriptions for search results
- Handle bilingual content (Hebrew/English) 
- Cache data in application memory for fast access

#### 2.1.2 Price Table File ("Vered Price Table") - Pricing Database
**File Structure:**
- Multiple sheets organized by tray heights: 50, 75, 100, 200
- Contains supplier data in columns A-F with pricing
- Additional sheets for connectors/supports/accessories
- Maps to complete lookup table for full product information

**Processing Requirements:**
- **READ-ONLY ACCESS**: Load pricing data into memory (NO FILE MODIFICATIONS)
- Categorize by tray height for efficient lookup
- Link to master lookup table for complete product details
- Handle accessories and connectors separately in search results

### 2.2 Search Functionality

#### 2.2.1 Free Text Search
- **Input**: Text in Hebrew or English
- **Search Fields**: 
  - Product descriptions (both languages)
  - Catalog numbers
  - Supplier codes
- **Features**:
  - Fuzzy matching capability
  - Search across all relevant fields
  - Real-time search suggestions

#### 2.2.2 Dropdown Parameter Search
**Search Parameters (TYP-H-W-T-G):**
1. **TYPE** - Product type/category
2. **HEIGHT** - Tray height (50/75/100/200)
3. **WIDTH** - Tray width
4. **THICKNESS** - Material thickness
5. **GALVANIZATION** - Galvanization type

**Search Flow:**
1. Tray type selection
2. Height selection
3. Width selection
4. Thickness selection
5. Galvanization selection

**Requirements:**
- Cascading dropdowns (each selection filters next dropdown)
- Clear selection option
- Multiple selection capability where applicable

### 2.3 Search Results & Shopping List Generation

#### 2.3.1 Search Results Display
1. **Menora catalog number** - Primary product identifier
2. **Hebrew description** - Product name in Hebrew  
3. **Supplier catalog number** - External supplier code
4. **English description** - Product name in English
5. **Quantity** - Input field for user to specify quantity
6. **Price** - Unit price (from read-only Excel data)
7. **Total price** - Calculated (Quantity × Price)
8. **Add to Shopping List** - Button to add item to user's list

#### 2.3.2 HTML Shopping List Features
- **User-specific lists**: Each user (identified by unique login code) has their own list
- **Persistent storage**: Shopping lists saved in Firebase Firestore
- **Live calculations**: Real-time price totals and overall sum
- **HTML format**: Clean, printable HTML shopping list
- **Export options**: Print-friendly, email-ready HTML format
- **List management**: Add, remove, modify quantities in saved lists

### 2.4 User Management & Data Storage

#### 2.4.1 User Authentication
- **Unique login codes**: Users enter a unique code to access their shopping lists
- **No registration required**: Simple code-based access system
- **Session management**: Track user sessions and shopping list access

#### 2.4.2 Firebase Firestore Collections
- **shopping_lists** - User shopping lists with items and calculations
- **users** - User codes and basic information
- **user_sessions** - Active user sessions
- **search_logs** - Search analytics (optional)

#### 2.4.3 Excel Data Handling
- **Read-only access**: Excel files are never modified by the application
- **In-memory caching**: Load Excel data into application memory for fast searches
- **Periodic refresh**: Reload Excel data if files are updated (manual trigger)

## 3. Non-Functional Requirements

### 3.1 Performance
- Search response time < 2 seconds
- Excel file processing < 30 seconds for typical files
- Support up to 10,000 products
- Concurrent user support (up to 50 users)

### 3.2 Usability
- Responsive design (mobile-friendly)
- Intuitive bilingual interface
- Error handling with user-friendly messages
- Keyboard navigation support

### 3.3 Reliability
- 99% uptime availability
- Data integrity validation
- Graceful error handling
- Automatic backup procedures

### 3.4 Security
- Secure file upload validation
- Input sanitization
- Rate limiting for searches
- Access logging

## 4. User Interface Requirements

### 4.1 Login Page
- Simple user code input field
- Access to existing shopping lists
- Create new shopping list option

### 4.2 Main Search Page
- Search interface (both text and dropdown)
- User's current shopping list summary
- Recent searches for this user

### 4.3 Search Results Page
- Results table with "Add to Shopping List" buttons
- Real-time search without page refresh
- Filtering and sorting controls

### 4.4 Shopping List Management Page
- View current HTML shopping list
- Modify quantities and remove items
- Print/export HTML shopping list
- Calculate totals and overall sum

### 4.5 Admin Interface (Optional)
- Monitor user activity
- Refresh Excel data cache
- System statistics

## 5. Technical Constraints

### 5.1 Technology Stack
- **Backend**: Python Flask
- **Database**: Firebase Firestore
- **Excel Processing**: pandas, openpyxl
- **Frontend**: HTML/CSS/JavaScript (Flask templates)
- **Hosting**: Cloud platform (Firebase Hosting or similar)

### 5.2 Data Formats
- Excel files (.xlsx, .xls)
- UTF-8 encoding for Hebrew text
- JSON for API responses
- CSV export capability

## 6. Integration Requirements

### 6.1 Firebase Integration
- Authentication (if required)
- Firestore database operations
- Cloud Storage for file uploads
- Analytics tracking

### 6.2 External APIs
- Currency conversion (if multi-currency support needed)
- Email notifications
- PDF generation service

## 7. Acceptance Criteria

### 7.1 Excel Processing
- ✅ Successfully parse both Excel file types
- ✅ Maintain data relationships between lookup and price tables
- ✅ Handle Hebrew/English text correctly
- ✅ Validate data integrity

### 7.2 Search Functionality
- ✅ Free text search returns relevant results
- ✅ Dropdown search works with cascading filters
- ✅ Results display all required columns
- ✅ Quantity and price calculations are accurate

### 7.3 System Performance
- ✅ Search completes within 2 seconds
- ✅ Handles expected user load
- ✅ Data persists correctly in Firestore
- ✅ Interface is responsive and user-friendly

## 8. Future Enhancements

### 8.1 Phase 2 Features
- User accounts and saved searches
- Shopping cart and order processing
- Email quotations
- Multi-supplier price comparison

### 8.2 Phase 3 Features
- Mobile application
- API for external integrations
- Advanced analytics dashboard
- Automated price updates