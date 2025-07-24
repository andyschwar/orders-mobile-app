#!/usr/bin/env python3
"""
Minimal Mobile API for Render deployment
"""

import os
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class MinimalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        if self.path == '/':
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
                        <p><strong>Version:</strong> 5.1 - Deployment Test</p>
                    </div>
                    <h3>Available Endpoints:</h3>
                    <ul>
                        <li><a href="/health">/health</a> - Health check</li>
                        <li><a href="/api/customers">/api/customers</a> - Real customers</li>
                        <li><a href="/test">/test</a> - Test endpoint</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
            
        elif self.path == '/health':
            response = {
                'status': 'healthy',
                'message': 'Orders Mobile App is running successfully!',
                'timestamp': datetime.now().isoformat(),
                'version': '5.0'
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/test':
            response = {
                'message': 'This is Version 5.2 - Real deployment with your customers!',
                'timestamp': datetime.now().isoformat(),
                'version': '5.0'
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/simple':
            response = {
                'message': 'SIMPLE TEST - Deployment is working!',
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/newtest':
            response = {
                'message': 'NEW TEST ENDPOINT - This should work!',
                'timestamp': datetime.now().isoformat(),
                'version': '5.0'
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/api/customers':
            # Return real customer data
            response = [
                {'id': 1, 'name': 'CARACAL', 'name_index': 'CAR'},
                {'id': 2, 'name': 'DAKO', 'name_index': 'DAK'},
                {'id': 3, 'name': 'INNOFREIGHT', 'name_index': 'INN'},
                {'id': 4, 'name': 'SLAVONSKI BROD', 'name_index': 'SLA'},
                {'id': 5, 'name': 'SRBSKO', 'name_index': 'SRB'},
                {'id': 6, 'name': 'SWIDNICA', 'name_index': 'SWI'},
                {'id': 7, 'name': 'TREBISOV', 'name_index': 'TRE'},
                {'id': 8, 'name': 'ZAHREB', 'name_index': 'ZAH'},
                {'id': 9, 'name': 'POPRAD', 'name_index': 'POP'},
                {'id': 10, 'name': 'CARACAL SLOVAKIA', 'name_index': 'CAS'}
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
    server = HTTPServer(('0.0.0.0', port), MinimalHandler)
    print(f"Server running on port {port}")
    print("Version 5.0 - Minimal deployment")
    print(f"Environment: PORT={os.environ.get('PORT', '10000')}")
    print(f"Server binding to: 0.0.0.0:{port}")
    server.serve_forever()

if __name__ == '__main__':
    run_server() 