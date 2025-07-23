#!/usr/bin/env python3
"""
Minimal Flask app for Render deployment
"""

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """Home page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Orders Mobile App</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 600px; margin: 0 auto; }
            .status { padding: 10px; background: #e8f5e8; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Orders Mobile App</h1>
            <div class="status">
                <h2>✅ Deployment Successful!</h2>
                <p>Your mobile app is now running on Render.</p>
                <p><strong>Status:</strong> Live</p>
                <p><strong>Timestamp:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </div>
            <h3>Available Endpoints:</h3>
            <ul>
                <li><a href="/health">/health</a> - Health check</li>
                <li><a href="/api/customers">/api/customers</a> - Sample customers</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Orders Mobile App is running successfully!',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/customers')
def get_customers():
    """Sample customers endpoint"""
    return jsonify([
        {'id': 1, 'name': 'Test Customer 1', 'name_index': 'TC1'},
        {'id': 2, 'name': 'Test Customer 2', 'name_index': 'TC2'},
        {'id': 3, 'name': 'Test Customer 3', 'name_index': 'TC3'}
    ])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
