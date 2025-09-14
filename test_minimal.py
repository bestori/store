#!/usr/bin/env python3
"""
Minimal test Flask app for Cloud Run debugging.
"""

import os
from flask import Flask

# Create minimal Flask app
app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'healthy', 'message': 'Minimal test app working'}

@app.route('/')
def home():
    return '<h1>Minimal Test App</h1><p>If you see this, the container is working!</p>'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)