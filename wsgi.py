"""
WSGI entry point for production deployment.
"""

import os
from app import create_app

# Create the Flask application instance with environment
app = create_app(os.environ.get('FLASK_ENV', 'production'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)