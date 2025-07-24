#!/usr/bin/env python3
"""
Simplified Mobile API for Render deployment
"""

import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import hashlib
import secrets
from datetime import datetime, timedelta
import os
import sys

# Supabase configuration
SUPABASE_URL = "https://vcmnfykughxghaqnqves.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZjbW5meWt1Z2h4Z2hhcW5xdmVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMzNTM5MTYsImV4cCI6MjA2ODkyOTkxNn0.lFiKhjwe5UzK7Ut6WQsAKs8CBU-DaRLWgbzHkwXcu50"

# Global session storage
active_sessions = {}

class SimpleMobileHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.supabase_headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json'
        }
        super().__init__(*args, **kwargs)
    
    def _verify_password(self, password_hash, password):
        """Verify password using salted SHA-256"""
        try:
            if '$' not in password_hash:
                return False
            
            salt, hash_part = password_hash.split('$', 1)
            expected_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return expected_hash == hash_part
        except:
            return False
    
    def _verify_user(self, username, password):
        """Verify user credentials against Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}&select=*"
            response = requests.get(url, headers=self.supabase_headers, timeout=10)
            
            if response.status_code == 200:
                users = response.json()
                if users:
                    user = users[0]
                    if self._verify_password(user['password_hash'], password):
                        return user
            return None
        except Exception as e:
            print(f"Error verifying user: {e}")
            return None
    
    def _serve_homepage(self):
        """Serve simple homepage"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orders Mobile App</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { color: #333; }
        .api-info { background: #f5f5f5; padding: 20px; border-radius: 10px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>💎 Orders Mobile App</h1>
        <p>Mobile API is running successfully!</p>
    </div>
    
    <div class="api-info">
        <h3>🔗 API Endpoints</h3>
        <p><a href="/api/customers">/api/customers</a> - Get all customers</p>
        <p><a href="/api/orders">/api/orders</a> - Get all orders</p>
        <p><a href="/api/items">/api/items</a> - Get all items</p>
        <p><a href="/api/products">/api/products</a> - Get all products</p>
        <p><a href="/api/employees">/api/employees</a> - Get all employees</p>
        <p><a href="/api/components">/api/components</a> - Get all components</p>
    </div>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def _serve_customers(self):
        """Serve customers data from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/customers?select=*"
            response = requests.get(url, headers=self.supabase_headers, timeout=10)
            
            if response.status_code == 200:
                customers = response.json()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(customers).encode())
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to fetch customers'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _serve_orders(self):
        """Serve orders data from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/orders?select=*"
            response = requests.get(url, headers=self.supabase_headers, timeout=10)
            
            if response.status_code == 200:
                orders = response.json()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(orders).encode())
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to fetch orders'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _serve_items(self):
        """Serve items data from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/items?select=*"
            response = requests.get(url, headers=self.supabase_headers, timeout=10)
            
            if response.status_code == 200:
                items = response.json()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(items).encode())
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to fetch items'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _serve_products(self):
        """Serve products data from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/products?select=*"
            response = requests.get(url, headers=self.supabase_headers, timeout=10)
            
            if response.status_code == 200:
                products = response.json()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(products).encode())
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to fetch products'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _serve_employees(self):
        """Serve employees data from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/employees?select=*"
            response = requests.get(url, headers=self.supabase_headers, timeout=10)
            
            if response.status_code == 200:
                employees = response.json()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(employees).encode())
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to fetch employees'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _serve_components(self):
        """Serve components data from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/components?select=*"
            response = requests.get(url, headers=self.supabase_headers, timeout=10)
            
            if response.status_code == 200:
                components = response.json()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(components).encode())
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to fetch components'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            if self.path == '/':
                self._serve_homepage()
            elif self.path == '/api/customers':
                self._serve_customers()
            elif self.path == '/api/orders':
                self._serve_orders()
            elif self.path == '/api/items':
                self._serve_items()
            elif self.path == '/api/products':
                self._serve_products()
            elif self.path == '/api/employees':
                self._serve_employees()
            elif self.path == '/api/components':
                self._serve_components()
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Not found'}).encode())
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

def run_server():
    """Run the server for Render deployment"""
    try:
        port = int(os.environ.get('PORT', 8000))
        server_address = ('0.0.0.0', port)
        httpd = HTTPServer(server_address, SimpleMobileHandler)
        print(f"🚀 Mobile API server running on port {port}")
        print(f"📱 Access at: http://localhost:{port}")
        httpd.serve_forever()
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_server() 