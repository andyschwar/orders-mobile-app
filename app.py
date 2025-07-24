#!/usr/bin/env python3
"""
Mobile API using Supabase REST API - Render Deployment Version
"""

import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import hashlib
import secrets
from datetime import datetime, timedelta
import os

# Supabase configuration
SUPABASE_URL = "https://vcmnfykughxghaqnqves.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZjbW5meWt1Z2h4Z2hhcW5xdmVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMzNTM5MTYsImV4cCI6MjA2ODkyOTkxNn0.lFiKhjwe5UzK7Ut6WQsAKs8CBU-DaRLWgbzHkwXcu50"

# Global session storage
active_sessions = {}

class SupabaseMobileHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.supabase_headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json'
        }
        super().__init__(*args, **kwargs)
    
    def _check_auth(self):
        """Check if user is authenticated"""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        if token in active_sessions:
            session = active_sessions[token]
            if datetime.now() < session['expires']:
                return session['user']
        
        return None
    
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
            response = requests.get(url, headers=self.supabase_headers)
            
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
    
    def _handle_login(self):
        """Handle login POST request"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        username = data.get('username', '')
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        user = self._verify_user(username, password)
        if user:
            # Generate session token
            token = secrets.token_urlsafe(32)
            expiry_days = 30 if remember_me else 1
            expires = datetime.now() + timedelta(days=expiry_days)
            
            active_sessions[token] = {
                'user': user,
                'expires': expires
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'success': True,
                'token': token,
                'user': {
                    'username': user['username'],
                    'role': user['role']
                }
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(401)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid credentials'}).encode())
    
    def _handle_logout(self):
        """Handle logout GET request"""
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            if token in active_sessions:
                del active_sessions[token]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def _serve_login_page(self):
        """Serve login page"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Orders Mobile App</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-container {{
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }}
        .logo {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo h1 {{
            color: #333;
            margin: 0;
            font-size: 28px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }}
        input {{
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 16px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }}
        input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .checkbox-group {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }}
        .checkbox-group input {{
            width: auto;
            margin-right: 10px;
        }}
        button {{
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        button:hover {{
            transform: translateY(-2px);
        }}
        .error {{
            color: #e74c3c;
            text-align: center;
            margin-top: 10px;
            display: none;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>💎 Orders Mobile App</h1>
        </div>
        <form id="loginForm">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <div class="checkbox-group">
                <input type="checkbox" id="remember" name="remember_me">
                <label for="remember">Remember me</label>
            </div>
            <button type="submit">Login</button>
        </form>
        <div id="error" class="error"></div>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const rememberMe = document.getElementById('remember').checked;
            
            try {{
                const response = await fetch('/login', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        username: username,
                        password: password,
                        remember_me: rememberMe
                    }})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    window.location.href = '/';
                }} else {{
                    document.getElementById('error').textContent = data.error || 'Login failed';
                    document.getElementById('error').style.display = 'block';
                }}
            }} catch (error) {{
                document.getElementById('error').textContent = 'Network error';
                document.getElementById('error').style.display = 'block';
            }}
        }});
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def _serve_homepage(self):
        """Serve homepage"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orders Mobile App</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            color: white;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .logout-btn {{
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .tile {{
            background: white;
            padding: 30px 20px;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s;
            cursor: pointer;
            text-decoration: none;
            color: #333;
        }}
        .tile:hover {{
            transform: translateY(-5px);
        }}
        .tile h3 {{
            margin: 0 0 10px 0;
            font-size: 20px;
        }}
        .tile p {{
            margin: 0;
            color: #666;
            font-size: 14px;
        }}
        .orders {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
        .labels {{ background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%); }}
        .news {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; }}
        .api-info {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            color: white;
            margin-top: 30px;
        }}
        .api-info h3 {{
            margin-top: 0;
        }}
        .api-info a {{
            color: #fff;
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>💎 Orders Mobile App</h1>
        <button class="logout-btn" onclick="logout()">Logout</button>
    </div>
    
    <div class="grid">
        <a href="#" class="tile orders" onclick="showOrders()">
            <h3>📋 Orders</h3>
            <p>View and manage orders</p>
        </a>
        <a href="#" class="tile labels" onclick="showLabels()">
            <h3>🏷️ Labels</h3>
            <p>Generate labels</p>
        </a>
        <a href="#" class="tile news" onclick="showNews()">
            <h3>📰 News</h3>
            <p>Latest updates</p>
        </a>
    </div>
    
    <div class="api-info">
        <h3>🔗 API Endpoints</h3>
        <p><a href="/api/customers" target="_blank">/api/customers</a> - Get all customers</p>
        <p><a href="/api/orders" target="_blank">/api/orders</a> - Get all orders</p>
        <p><a href="/api/order-items" target="_blank">/api/order-items</a> - Get all order items</p>
        <p><a href="/api/items" target="_blank">/api/items</a> - Get all items</p>
        <p><a href="/api/products" target="_blank">/api/products</a> - Get all products</p>
        <p><a href="/api/employees" target="_blank">/api/employees</a> - Get all employees</p>
        <p><a href="/api/components" target="_blank">/api/components</a> - Get all components</p>
    </div>

    <script>
        // Check authentication
        const token = localStorage.getItem('token');
        const user = JSON.parse(localStorage.getItem('user') || '{{}}');
        
        if (!token) {{
            window.location.href = '/login';
        }}
        
        function logout() {{
            fetch('/logout', {{
                method: 'GET',
                headers: {{
                    'Authorization': `Bearer ${{token}}`
                }}
            }}).then(() => {{
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                window.location.href = '/login';
            }});
        }}
        
        function showOrders() {{
            alert('Orders feature coming soon!');
        }}
        
        function showLabels() {{
            alert('Labels feature coming soon!');
        }}
        
        function showNews() {{
            alert('News feature coming soon!');
        }}
    </script>
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
            response = requests.get(url, headers=self.supabase_headers)
            
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
            response = requests.get(url, headers=self.supabase_headers)
            
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
    
    def _serve_order_items(self):
        """Serve order items data from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/order_items?select=*"
            response = requests.get(url, headers=self.supabase_headers)
            
            if response.status_code == 200:
                order_items = response.json()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(order_items).encode())
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Failed to fetch order items'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _serve_items(self):
        """Serve items data from Supabase"""
        try:
            url = f"{SUPABASE_URL}/rest/v1/items?select=*"
            response = requests.get(url, headers=self.supabase_headers)
            
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
            response = requests.get(url, headers=self.supabase_headers)
            
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
            response = requests.get(url, headers=self.supabase_headers)
            
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
            response = requests.get(url, headers=self.supabase_headers)
            
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
        if self.path == '/':
            self._serve_homepage()
        elif self.path == '/login':
            self._serve_login_page()
        elif self.path == '/logout':
            self._handle_logout()
        elif self.path == '/api/customers':
            user = self._check_auth()
            if user:
                self._serve_customers()
            else:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
        elif self.path == '/api/orders':
            user = self._check_auth()
            if user:
                self._serve_orders()
            else:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
        elif self.path == '/api/order-items':
            user = self._check_auth()
            if user:
                self._serve_order_items()
            else:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
        elif self.path == '/api/items':
            user = self._check_auth()
            if user:
                self._serve_items()
            else:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
        elif self.path == '/api/products':
            user = self._check_auth()
            if user:
                self._serve_products()
            else:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
        elif self.path == '/api/employees':
            user = self._check_auth()
            if user:
                self._serve_employees()
            else:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
        elif self.path == '/api/components':
            user = self._check_auth()
            if user:
                self._serve_components()
            else:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/login':
            self._handle_login()
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

def run_server():
    """Run the server for Render deployment"""
    port = int(os.environ.get('PORT', 8000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SupabaseMobileHandler)
    print(f"🚀 Mobile API server running on port {port}")
    print(f"📱 Access at: http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server() 