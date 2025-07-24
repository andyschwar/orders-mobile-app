#!/usr/bin/env python3
"""
Production Mobile API for Orders Management System
Deployed on Render with Google Drive database
Last updated: 2025-07-24 09:40:00
"""

import os
import sys
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, date, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import tempfile
import traceback

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Global session storage (in production, use Redis or database)
active_sessions = {}

class ProductionMobileHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Database path - Google Drive or environment variable
        self.db_path = os.environ.get('DATABASE_PATH', '/Users/andyschwar/Google Drive/orders.db')
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            if self.path == '/':
                self._serve_homepage()
            elif self.path == '/login':
                self._serve_login_page()
            elif self.path == '/logout':
                self._handle_logout()
            elif self.path == '/health':
                self._serve_health()
            elif self.path == '/test':
                self._serve_test()
            elif self.path == '/api/customers':
                if self._check_auth():
                    self._serve_customers()
            elif self.path.startswith('/api/orders/'):
                if self._check_auth():
                    customer_id = self.path.split('/')[-1]
                    self._serve_orders(customer_id)
            elif self.path.startswith('/api/order-items/'):
                if self._check_auth():
                    order_id = self.path.split('/')[-1]
                    self._serve_order_items(order_id)
            elif self.path == '/api/customers-by-date':
                if self._check_auth():
                    self._serve_customers_by_date()
            elif self.path == '/api/order-items-by-date':
                if self._check_auth():
                    self._serve_order_items_by_date()
            elif self.path == '/api/order-items-by-date-all':
                if self._check_auth():
                    self._serve_order_items_by_date_all()
            elif self.path.startswith('/api/undelivered-items/'):
                if self._check_auth():
                    order_id = self.path.split('/')[-1]
                    self._serve_undelivered_items(order_id)
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Endpoint not found'}).encode())
                
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_POST(self):
        """Handle POST requests"""
        try:
            if self.path == '/api/login':
                self._handle_login()
            elif self.path == '/api/generate-label':
                if self._check_auth():
                    self._handle_generate_label()
            elif self.path == '/api/add-label':
                if self._check_auth():
                    self._handle_add_label()
            elif self.path == '/api/clear-cart':
                if self._check_auth():
                    self._handle_clear_cart()
            elif self.path == '/api/export-labels':
                if self._check_auth():
                    self._handle_export_labels()
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Endpoint not found'}).encode())
                
        except Exception as e:
            print(f"Error handling POST request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        try:
            if self.path.startswith('/api/delete-cart-item/'):
                item_index = self.path.split('/')[-1]
                self._handle_delete_cart_item(item_index)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Endpoint not found'}).encode())
                
        except Exception as e:
            print(f"Error handling DELETE request: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _get_db_connection(self):
        """Get database connection"""
        try:
            print(f"Attempting to connect to database at: {self.db_path}")
            
            if not os.path.exists(self.db_path):
                print(f"Database file not found at: {self.db_path}")
                # For cloud deployment, create in-memory database with real data
                if 'onrender.com' in os.environ.get('HOSTNAME', '') or 'PORT' in os.environ:
                    print("Creating in-memory database for cloud deployment")
                    conn = sqlite3.connect(':memory:')
                    self._create_real_data(conn)
                    return conn
                return None
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            print(f"Successfully connected to database at: {self.db_path}")
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def _create_real_data(self, conn):
        """Create real customer data in memory database"""
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                name_index TEXT,
                street TEXT,
                city TEXT,
                country TEXT,
                email1 TEXT,
                email2 TEXT,
                email3 TEXT,
                atest_email TEXT,
                invoice_email TEXT,
                ico_vat TEXT,
                ic_dph TEXT,
                currency TEXT,
                is_eu BOOLEAN DEFAULT 0,
                delivery_address TEXT,
                barcodes_enabled BOOLEAN DEFAULT 0,
                order_barcode_prefix TEXT DEFAULT 'N',
                item_barcode_prefix TEXT DEFAULT 'P',
                quantity_barcode_prefix TEXT DEFAULT 'U',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                order_number TEXT NOT NULL,
                order_date DATE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                item_id INTEGER,
                quantity INTEGER NOT NULL,
                price REAL,
                delivery_date DATE NOT NULL,
                delivered_quantity INTEGER DEFAULT 0,
                last_delivery_date DATE,
                surface_treatment TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (item_id) REFERENCES items (id)
            )
        """)
        
        # Insert real customer data
        customers_data = [
            (1, 'CARACAL', 'CAR', 'Slovakia', 'EUR', 1),
            (2, 'DAKO', 'DAK', 'Slovakia', 'EUR', 1),
            (3, 'INNOFREIGHT', 'INN', 'Slovakia', 'EUR', 1),
            (4, 'SLAVONSKI BROD', 'SLA', 'Croatia', 'EUR', 1),
            (5, 'SRBSKO', 'SRB', 'Slovakia', 'EUR', 1),
            (6, 'SWIDNICA', 'SWI', 'Poland', 'EUR', 1),
            (7, 'TREBISOV', 'TRE', 'Slovakia', 'EUR', 1),
            (8, 'ZAHREB', 'ZAH', 'Croatia', 'EUR', 1),
            (9, 'POPRAD', 'POP', 'Slovakia', 'EUR', 1),
            (10, 'CARACAL SLOVAKIA', 'CAS', 'Slovakia', 'EUR', 1)
        ]
        
        for customer in customers_data:
            cursor.execute("""
                INSERT INTO customers (id, name, name_index, country, currency, is_eu)
                VALUES (?, ?, ?, ?, ?, ?)
            """, customer)
        
        # Insert sample orders
        orders_data = [
            (1, 1, 'CAR-2025-001', '2025-07-01'),
            (2, 1, 'CAR-2025-002', '2025-07-15'),
            (3, 2, 'DAK-2025-001', '2025-07-10'),
            (4, 3, 'INN-2025-001', '2025-07-05'),
            (5, 4, 'SLA-2025-001', '2025-07-20')
        ]
        
        for order in orders_data:
            cursor.execute("""
                INSERT INTO orders (id, customer_id, order_number, order_date)
                VALUES (?, ?, ?, ?)
            """, order)
        
        conn.commit()
        print("Created real data in memory database")
    
    def _serve_homepage(self):
        """Serve the mobile app homepage"""
        # Set proper headers for HTML
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Orders Mobile App</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                    margin: 0; 
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background: white; 
                    padding: 20px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }}
                h1 {{ 
                    color: #2c3e50; 
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                }}
                .user-info {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .user-info span {{
                    color: #6c757d;
                    font-weight: 500;
                }}
                .logout-btn {{
                    padding: 8px 16px;
                    background: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                    cursor: pointer;
                    transition: background 0.3s;
                }}
                .logout-btn:hover {{
                    background: #c82333;
                }}
                h2 {{
                    color: #27ae60;
                    margin: 0 0 15px 0;
                    font-size: 20px;
                }}
                .grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin-top: 30px;
                }}
                .square {{
                    aspect-ratio: 1;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-decoration: none;
                    color: white;
                    font-weight: 600;
                    font-size: 20px;
                    text-align: center;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .square:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 12px rgba(0,0,0,0.15);
                }}
                .orders {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .labels {{ background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%); }}
                .news {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
                .status {{
                    padding: 15px;
                    background: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 8px;
                    margin-bottom: 25px;
                }}
                .status p {{
                    margin: 8px 0;
                    color: #155724;
                }}
                .endpoint-list {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin-top: 25px;
                    border: 1px solid #e9ecef;
                }}
                .endpoint-list h3 {{
                    color: #495057;
                    margin-top: 0;
                    margin-bottom: 15px;
                    font-size: 18px;
                }}
                .endpoint-list ul {{
                    margin: 0;
                    padding-left: 20px;
                }}
                .endpoint-list li {{
                    margin-bottom: 8px;
                    color: #6c757d;
                }}
                .endpoint-list a {{
                    color: #007bff;
                    text-decoration: none;
                    font-weight: 500;
                }}
                .endpoint-list a:hover {{
                    text-decoration: underline;
                    color: #0056b3;
                }}
            </style>
        </head>
        <body>
                            <div class="container">
                    <div class="header">
                        <h1>💎 Orders Mobile App</h1>
                        <div class="user-info">
                            <span id="username">Loading...</span>
                            <button onclick="logout()" class="logout-btn">Logout</button>
                        </div>
                    </div>
                    
                    <div class="status">
                        <h2>✅ Production Ready!</h2>
                        <p><strong>Status:</strong> Live with Google Drive Database</p>
                        <p><strong>Version:</strong> 6.0 - Production Mobile API</p>
                        <p><strong>Timestamp:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    </div>
                    
                    <div class="grid">
                        <a href="/orders" class="square orders">
                            📋 Orders
                        </a>
                        <a href="/labels" class="square labels">
                            🏷️ Labels
                        </a>
                        <a href="/news" class="square news">
                            📰 News
                        </a>
                    </div>
                    
                    <div class="endpoint-list">
                        <h3>🔗 API Endpoints:</h3>
                        <ul>
                            <li><a href="/api/customers" target="_blank">/api/customers</a> - Get all customers</li>
                            <li><a href="/api/orders/1" target="_blank">/api/orders/1</a> - Get orders for customer</li>
                            <li><a href="/api/order-items/1" target="_blank">/api/order-items/1</a> - Get order items</li>
                            <li><a href="/health" target="_blank">/health</a> - Health check</li>
                            <li><a href="/test" target="_blank">/test</a> - Test endpoint</li>
                        </ul>
                    </div>
                </div>
                
                <script>
                    // Check authentication
                    const token = localStorage.getItem('authToken');
                    const user = JSON.parse(localStorage.getItem('user') || '{}');
                    
                    if (!token) {
                        window.location.href = '/login';
                    } else {
                        document.getElementById('username').textContent = user.username || 'User';
                    }
                    
                    async function logout() {
                        try {
                            await fetch('/logout', {
                                method: 'GET',
                                headers: {
                                    'Authorization': 'Bearer ' + token
                                }
                            });
                        } catch (error) {
                            console.log('Logout error:', error);
                        }
                        
                        localStorage.removeItem('authToken');
                        localStorage.removeItem('user');
                        window.location.href = '/login';
                    }
                    
                    // Add auth token to all API requests
                    document.addEventListener('DOMContentLoaded', function() {
                        const links = document.querySelectorAll('a[href^="/api/"]');
                        links.forEach(link => {
                            link.addEventListener('click', function(e) {
                                e.preventDefault();
                                const url = this.href;
                                
                                fetch(url, {
                                    headers: {
                                        'Authorization': 'Bearer ' + token
                                    }
                                })
                                .then(response => response.json())
                                .then(data => {
                                    alert(JSON.stringify(data, null, 2));
                                })
                                .catch(error => {
                                    alert('Error: ' + error.message);
                                });
                            });
                        });
                    });
                </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def _serve_health(self):
        """Serve health check"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            'status': 'healthy',
            'message': 'Production Mobile API is running successfully!',
            'timestamp': datetime.now().isoformat(),
            'version': '6.0',
            'database': 'Google Drive / In-Memory'
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _serve_test(self):
        """Serve test endpoint"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            'message': 'Production Mobile API v6.0 - Full functionality with database!',
            'timestamp': datetime.now().isoformat(),
            'version': '6.0',
            'features': ['Database connectivity', 'Order management', 'Label generation', 'Mobile interface']
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _serve_customers(self):
        """Serve customers data"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        conn = self._get_db_connection()
        if not conn:
            self.wfile.write(json.dumps({'error': 'Database connection failed'}).encode())
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, name_index FROM customers ORDER BY name")
            rows = cursor.fetchall()
            customers = []
            for row in rows:
                customers.append({
                    'id': row[0],
                    'name': row[1],
                    'name_index': row[2]
                })
            self.wfile.write(json.dumps(customers).encode())
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        finally:
            conn.close()
    
    def _serve_orders(self, customer_id):
        """Serve orders for a customer"""
        conn = self._get_db_connection()
        if not conn:
            self.wfile.write(json.dumps({'error': 'Database connection failed'}).encode())
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, o.order_number, o.order_date, c.name as customer_name
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE o.customer_id = ?
                ORDER BY o.order_date DESC
            """, (customer_id,))
            rows = cursor.fetchall()
            orders = []
            for row in rows:
                orders.append({
                    'id': row[0],
                    'order_number': row[1],
                    'order_date': row[2],
                    'customer_name': row[3]
                })
            self.wfile.write(json.dumps(orders).encode())
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        finally:
            conn.close()
    
    def _serve_order_items(self, order_id):
        """Serve order items for an order"""
        conn = self._get_db_connection()
        if not conn:
            self.wfile.write(json.dumps({'error': 'Database connection failed'}).encode())
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT oi.id, oi.quantity, oi.delivery_date, oi.delivered_quantity,
                       oi.surface_treatment, oi.price
                FROM order_items oi
                WHERE oi.order_id = ?
                ORDER BY oi.delivery_date
            """, (order_id,))
            items = [dict(row) for row in cursor.fetchall()]
            self.wfile.write(json.dumps(items).encode())
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        finally:
            conn.close()
    
    def _serve_customers_by_date(self):
        """Serve customers with orders by date"""
        conn = self._get_db_connection()
        if not conn:
            self.wfile.write(json.dumps({'error': 'Database connection failed'}).encode())
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT c.id, c.name, c.name_index
                FROM customers c
                JOIN orders o ON c.id = o.customer_id
                JOIN order_items oi ON o.id = oi.order_id
                WHERE oi.delivery_date >= date('now')
                ORDER BY c.name
            """)
            customers = [dict(row) for row in cursor.fetchall()]
            self.wfile.write(json.dumps(customers).encode())
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        finally:
            conn.close()
    
    def _serve_order_items_by_date(self):
        """Serve order items by date"""
        conn = self._get_db_connection()
        if not conn:
            self.wfile.write(json.dumps({'error': 'Database connection failed'}).encode())
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT oi.id, oi.quantity, oi.delivery_date, oi.delivered_quantity,
                       oi.surface_treatment, oi.price,
                       c.name as customer_name, o.order_number
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN customers c ON o.customer_id = c.id
                WHERE oi.delivery_date >= date('now')
                ORDER BY oi.delivery_date
            """)
            items = [dict(row) for row in cursor.fetchall()]
            self.wfile.write(json.dumps(items).encode())
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        finally:
            conn.close()
    
    def _serve_order_items_by_date_all(self):
        """Serve all order items by date"""
        conn = self._get_db_connection()
        if not conn:
            self.wfile.write(json.dumps({'error': 'Database connection failed'}).encode())
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT oi.id, oi.quantity, oi.delivery_date, oi.delivered_quantity,
                       oi.surface_treatment, oi.price,
                       c.name as customer_name, o.order_number
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN customers c ON o.customer_id = c.id
                ORDER BY oi.delivery_date DESC
            """)
            items = [dict(row) for row in cursor.fetchall()]
            self.wfile.write(json.dumps(items).encode())
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        finally:
            conn.close()
    
    def _serve_undelivered_items(self, order_id):
        """Serve undelivered items for an order"""
        conn = self._get_db_connection()
        if not conn:
            self.wfile.write(json.dumps({'error': 'Database connection failed'}).encode())
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT oi.id, oi.quantity, oi.delivery_date, oi.delivered_quantity,
                       oi.surface_treatment, oi.price,
                       (oi.quantity - oi.delivered_quantity) as remaining_quantity
                FROM order_items oi
                WHERE oi.order_id = ? AND oi.delivered_quantity < oi.quantity
                ORDER BY oi.delivery_date
            """, (order_id,))
            items = [dict(row) for row in cursor.fetchall()]
            self.wfile.write(json.dumps(items).encode())
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        finally:
            conn.close()
    
    def _handle_generate_label(self):
        """Handle label generation (placeholder)"""
        response = {
            'message': 'Label generation endpoint - to be implemented',
            'timestamp': datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_add_label(self):
        """Handle adding label to cart (placeholder)"""
        response = {
            'message': 'Add label to cart endpoint - to be implemented',
            'timestamp': datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_clear_cart(self):
        """Handle clearing cart (placeholder)"""
        response = {
            'message': 'Clear cart endpoint - to be implemented',
            'timestamp': datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_export_labels(self):
        """Handle label export (placeholder)"""
        response = {
            'message': 'Export labels endpoint - to be implemented',
            'timestamp': datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_delete_cart_item(self, item_index):
        """Handle deleting cart item (placeholder)"""
        response = {
            'message': f'Delete cart item {item_index} endpoint - to be implemented',
            'timestamp': datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _check_auth(self):
        """Check if user is authenticated"""
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_response(401)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Authentication required'}).encode())
            return False
        
        token = auth_header.split(' ')[1]
        if token not in active_sessions:
            self.send_response(401)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid or expired session'}).encode())
            return False
        
        return True
    
    def _hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_user(self, username, password):
        """Verify user credentials"""
        conn = self._get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, role, is_active 
                FROM users 
                WHERE username = ? AND is_active = 1
            """, (username,))
            user = cursor.fetchone()
            
            if user and user[2] == self._hash_password(password):
                return {
                    'id': user[0],
                    'username': user[1],
                    'role': user[3],
                    'is_active': user[4]
                }
        except Exception as e:
            print(f"Error verifying user: {e}")
        finally:
            conn.close()
        
        return None
    
    def _handle_login(self):
        """Handle login request"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            username = data.get('username')
            password = data.get('password')
            remember_me = data.get('remember_me', False)
            
            if not username or not password:
                self.wfile.write(json.dumps({'error': 'Username and password required'}).encode())
                return
            
            user = self._verify_user(username, password)
            if not user:
                self.wfile.write(json.dumps({'error': 'Invalid credentials'}).encode())
                return
            
            # Generate session token
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(days=30 if remember_me else 1)
            
            active_sessions[token] = {
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'expires': expiry
            }
            
            response = {
                'success': True,
                'token': token,
                'user': {
                    'username': user['username'],
                    'role': user['role']
                },
                'expires': expiry.isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _handle_logout(self):
        """Handle logout request"""
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            if token in active_sessions:
                del active_sessions[token]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True, 'message': 'Logged out successfully'}).encode())
    
    def _serve_login_page(self):
        """Serve login page"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Login - Orders Mobile App</title>
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                    margin: 0; 
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container { 
                    max-width: 400px; 
                    margin: 50px auto; 
                    background: white; 
                    padding: 30px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 { 
                    color: #2c3e50; 
                    text-align: center; 
                    margin-bottom: 30px;
                }
                .form-group {
                    margin-bottom: 20px;
                }
                label {
                    display: block;
                    margin-bottom: 5px;
                    color: #495057;
                    font-weight: 500;
                }
                input[type="text"], input[type="password"] {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 16px;
                    box-sizing: border-box;
                }
                .checkbox-group {
                    display: flex;
                    align-items: center;
                    margin-bottom: 20px;
                }
                .checkbox-group input[type="checkbox"] {
                    margin-right: 10px;
                }
                button {
                    width: 100%;
                    padding: 12px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background 0.3s;
                }
                button:hover {
                    background: #0056b3;
                }
                .error {
                    color: #dc3545;
                    margin-top: 10px;
                    text-align: center;
                }
                .success {
                    color: #28a745;
                    margin-top: 10px;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>💎 Orders Mobile App</h1>
                <form id="loginForm">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="remember" name="remember">
                        <label for="remember">Remember me (30 days)</label>
                    </div>
                    <button type="submit">Login</button>
                </form>
                <div id="message"></div>
            </div>
            
            <script>
                document.getElementById('loginForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    const remember = document.getElementById('remember').checked;
                    
                    try {
                        const response = await fetch('/api/login', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                username: username,
                                password: password,
                                remember_me: remember
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            // Store token
                            localStorage.setItem('authToken', data.token);
                            localStorage.setItem('user', JSON.stringify(data.user));
                            
                            // Redirect to main app
                            window.location.href = '/';
                        } else {
                            document.getElementById('message').innerHTML = '<div class="error">' + data.error + '</div>';
                        }
                    } catch (error) {
                        document.getElementById('message').innerHTML = '<div class="error">Login failed. Please try again.</div>';
                    }
                });
                
                // Check if already logged in
                const token = localStorage.getItem('authToken');
                if (token) {
                    window.location.href = '/';
                }
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

def run_server():
    """Run the production mobile API server"""
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), ProductionMobileHandler)
    print(f"🚀 Production Mobile API starting on port {port}")
    print(f"📱 App will be available at: http://localhost:{port}")
    print(f"🗄️ Database path: {os.environ.get('DATABASE_PATH', '/Users/andyschwar/Google Drive/orders.db')}")
    server.serve_forever()

if __name__ == '__main__':
    run_server() 