#!/usr/bin/env python3
"""
Minimal HTTP server using only Python built-in libraries
"""

import os
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        if path == '/':
            # Home page
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Orders Mobile App</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .status {{ padding: 10px; background: #e8f5e8; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🚀 Orders Mobile App</h1>
                    <div class="status">
                        <h2>✅ Deployment Successful!</h2>
                        <p>Your mobile app is now running on Render.</p>
                        <p><strong>Status:</strong> Live</p>
                        <p><strong>Timestamp:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
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
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
            
        elif path == '/health':
            # Health check
            response = {
                'status': 'healthy',
                'message': 'Orders Mobile App is running successfully!',
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif path == '/api/customers':
            # Sample customers
            response = [
                {'id': 1, 'name': 'Test Customer 1', 'name_index': 'TC1'},
                {'id': 2, 'name': 'Test Customer 2', 'name_index': 'TC2'},
                {'id': 3, 'name': 'Test Customer 3', 'name_index': 'TC3'}
            ]
            self.wfile.write(json.dumps(response).encode())
            
        else:
            # 404
            response = {'error': 'Not found'}
            self.send_response(404)
            self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server():
    """Run the HTTP server"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"Server running on port {port}")
    server.serve_forever()

if __name__ == '__main__':
    run_server()
# Updated Thu Jul 24 08:40:58 CEST 2025
