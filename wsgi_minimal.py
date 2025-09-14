#!/usr/bin/env python3
"""
Minimal WSGI entry point for debugging Cloud Run issues.
"""

import os
import logging
from flask import Flask

# Create minimal Flask app
app = Flask(__name__)

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health')
def health():
    return {
        'status': 'healthy', 
        'message': 'Minimal WSGI app working',
        'port': os.environ.get('PORT', 'not set')
    }

@app.route('/')
def home():
    port = os.environ.get('PORT', 'not set')
    return f'''
    <h1>Minimal Test App</h1>
    <p>Flask app is running!</p>
    <p>PORT environment variable: {port}</p>
    <p>Check <a href="/health">/health</a> endpoint</p>
    '''

# Debug environment variables at startup (for both Gunicorn and direct run)
logger.info(f"Environment variables:")
for key in ['PORT', 'FLASK_ENV', 'PYTHONPATH']:
    logger.info(f"  {key} = {os.environ.get(key, 'NOT SET')}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask app on 0.0.0.0:{port}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}")
        raise