# Cable Tray Online Store - Claude Configuration

## Project Overview
Python Flask web application for cable tray product catalog with Excel file processing, Firebase Firestore database, and bilingual (Hebrew/English) search functionality.

## Technology Stack
- **Backend**: Python Flask
- **Database**: Firebase Firestore
- **Excel Processing**: pandas, openpyxl
- **Frontend**: HTML/CSS/JavaScript (Flask templates)
- **Deployment**: TBD

## Development Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Development
```bash
flask run
# or
python app.py
```

### Testing
```bash
pytest
# or
python -m pytest tests/
```

### Linting & Type Checking
```bash
flake8 .
black .
mypy .
```

### Database Setup
```bash
# Firebase configuration will be loaded from environment variables
export GOOGLE_APPLICATION_CREDENTIALS="path/to/serviceAccount.json"
export FIREBASE_PROJECT_ID="your-project-id"
```

## File Structure
```
/
├── app/
│   ├── __init__.py
│   ├── routes/
│   ├── models/
│   ├── services/
│   └── utils/
├── data/
│   ├── excel_files/
│   └── uploads/
├── static/
├── templates/
├── tests/
├── requirements.txt
├── config.py
└── run.py
```

## Key Features
- Excel file processing with lookup functionality
- Bilingual search (Hebrew/English)
- Product catalog management
- Price calculation system
- Firebase Firestore integration
- Responsive web interface

## Environment Variables
```
FLASK_ENV=development
FLASK_APP=run.py
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
FIREBASE_PROJECT_ID=your-project-id
SECRET_KEY=your-secret-key
```