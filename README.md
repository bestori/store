# Store 🏪

A bilingual (Hebrew/English) Flask web application for cable tray product management with shopping list functionality. The application uses Excel files as a read-only database and generates HTML shopping lists for users.

## ✨ Features

- **Bilingual Support**: Complete Hebrew and English interface with RTL/LTR support
- **Excel-Based Catalog**: Uses Excel files as read-only product database
- **Smart Search**: Text search and parametric filtering by TYPE-HEIGHT-WIDTH-THICKNESS-GALVANIZATION
- **Shopping Lists**: Create, manage, and export personalized shopping lists
- **User Management**: Simple authentication with unique user codes
- **HTML Export**: Generate printable HTML shopping lists
- **Firebase Integration**: Optional cloud storage for user data
- **Responsive Design**: Bootstrap 5 with mobile-friendly interface

## 🏗️ Architecture

- **Frontend**: Bootstrap 5, vanilla JavaScript, bilingual Jinja2 templates
- **Backend**: Flask with Blueprint architecture
- **Database**: Excel files (read-only) + Firebase Firestore (user data)
- **Services**: Modular service layer for business logic
- **Caching**: In-memory Excel data caching for fast searches

## 📋 Requirements

- Python 3.8+
- Flask 2.3+
- pandas, openpyxl (Excel processing)
- firebase-admin (optional, with mock fallback)
- Bootstrap 5 (CDN)

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd solel-bone
./startup.sh
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Add Excel Data Files
Place your Excel files in the `data/` directory:
- `New shopping list.xlsx` - Product catalog
- `Vered Price Table.xlsx` - Pricing data

### 4. Run Application
```bash
python run.py
```

Visit http://localhost:5000

## 📁 Project Structure

```
solel-bone/
├── app/                    # Flask application
│   ├── __init__.py        # App factory
│   ├── models/            # Data models
│   ├── routes/            # URL routes (blueprints)
│   ├── services/          # Business logic services
│   └── templates/         # Jinja2 HTML templates
├── config/                # Configuration classes
├── data/                  # Excel data files
├── logs/                  # Application logs
├── docs/                  # Project documentation
├── requirements.txt       # Python dependencies
├── run.py                # Development server entry point
├── wsgi.py               # Production WSGI entry point
└── startup.sh            # Setup and start script
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Firebase (optional)
FIREBASE_PROJECT_ID=your-project-id
MOCK_FIREBASE=true  # Use mock Firebase for development

# Excel Files
EXCEL_SHOPPING_LIST_PATH=data/New shopping list.xlsx
EXCEL_PRICE_TABLE_PATH=data/Vered Price Table.xlsx

# Application
DEFAULT_LANGUAGE=hebrew
SESSION_TIMEOUT_HOURS=24
```

## 💾 Data Models

### Excel Files Structure

**Shopping List File**: Product catalog with columns:
- `Type` - Product type identifier
- `Hebrew Term` - Hebrew product name
- `English term` - English product name

**Price Table File**: Pricing sheets (50, 75, 100, 200) with columns:
- `TYPE` - Product type
- `גילוון` - Galvanization type
- `גובה` - Height
- `רוחב` - Width  
- `עובי` - Thickness
- `מחיר` - Price

### Firebase Collections
- `users` - User profiles and authentication
- `shopping_lists` - User shopping lists
- `user_sessions` - Active user sessions

## 🔍 API Endpoints

### Authentication
- `POST /auth/login` - User login with code
- `GET /auth/logout` - User logout
- `GET /auth/profile` - User profile page

### Search
- `GET /search` - Search page
- `POST /api/search/text` - Text search
- `POST /api/search/filter` - Parametric search
- `GET /api/search/suggestions` - Search suggestions

### Shopping Lists
- `GET /shopping-lists` - User's shopping lists
- `POST /shopping-lists/create` - Create new list
- `GET /shopping-lists/<id>` - View list details
- `PUT /shopping-lists/<id>` - Update list
- `DELETE /shopping-lists/<id>` - Delete list
- `POST /shopping-lists/<id>/add-item` - Add item to list
- `GET /shopping-lists/<id>/generate-html` - Export HTML

## 🌐 Deployment

### Docker
```bash
# Development
docker-compose up web

# Production
docker-compose up web-prod
```

### Heroku
```bash
heroku create your-app-name
git push heroku main
```

### Manual Deployment
1. Set `FLASK_ENV=production`
2. Configure Firebase credentials
3. Use `gunicorn wsgi:app`

## 🧪 Testing

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=app
```

## 📊 Features Overview

### Search System
- **Text Search**: Free text search across Hebrew/English terms
- **Filter Search**: Dropdown-based parametric filtering
- **Real-time Suggestions**: Dynamic search suggestions
- **Bilingual Results**: Results shown in user's preferred language

### Shopping Lists
- **CRUD Operations**: Create, read, update, delete lists
- **Item Management**: Add/remove/modify items with quantities
- **Price Calculations**: Automatic totals with tax and discounts
- **HTML Export**: Professional printable shopping lists

### User Experience
- **Language Toggle**: Switch between Hebrew and English
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Session Management**: Persistent user sessions
- **Error Handling**: Comprehensive error pages and messaging

## 🛠️ Development

### Adding New Features
1. Create service in `app/services/`
2. Add routes in `app/routes/`
3. Create templates in `app/templates/`
4. Update API documentation

### Code Structure
- Services handle business logic
- Routes handle HTTP requests/responses
- Models define data structures
- Templates render HTML with Jinja2

## 📝 License

This project was generated with Claude Code and is configured for a Store application.

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>