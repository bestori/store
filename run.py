#!/usr/bin/env python3
"""
Main entry point for the Cable Tray Online Store application.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app import create_app

# Create Flask application
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Run the development server
    debug_mode = app.config.get('DEBUG', False)
    
    # Use 0.0.0.0 for Cloud Run compatibility, 127.0.0.1 for local development
    host = '0.0.0.0' if os.environ.get('FLASK_ENV') == 'production' else '127.0.0.1'
    
    app.run(
        debug=debug_mode,
        host=host,
        port=int(os.environ.get('PORT', 5000))
    )