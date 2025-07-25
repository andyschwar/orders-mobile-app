#!/usr/bin/env python3
"""
Enhanced Web Application for Orders Management System
Builds upon the mobile API with additional features
"""

import os
import sys
import json
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, request, send_file, render_template_string, session, redirect, url_for
from flask_cors import CORS
import tempfile
import traceback
from sqlalchemy import create_engine, func, and_, or_, text
from sqlalchemy.orm import sessionmaker
from functools import wraps

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Check for Supabase URL environment variable
if not os.environ.get('SUPABASE_URL'):
    print("⚠️  WARNING: SUPABASE_URL environment variable not set!")
    print("Please set the SUPABASE_URL environment variable in your deployment platform.")
    print("For local development, you can set it in your environment or use SQLite.")

from models.database import (
    Order, Customer, OrderItem, Item, Product, Delivery, DeliveryTerm,
    ProductionPlan, Employee, Component, ProductComponent, User, UserRole,
    get_database_path, init_db
)
from utils.label_generator import LabelGenerator
from utils.auth import authenticate_user, hash_password, verify_password, get_role_display_name, create_default_users

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
CORS(app)

# Initialize database connection
try:
    print("Initializing database...")
    engine = init_db()
    Session = sessionmaker(bind=engine)
    print("Database initialized successfully!")
except Exception as e:
    print(f"Error initializing database: {e}")
    import traceback
    traceback.print_exc()
    raise

def get_session():
    return Session()

# Create default users if they don't exist
try:
    print("Creating default users...")
    db_session = get_session()
    create_default_users(db_session)
    db_session.close()
    print("Default users created successfully!")
except Exception as e:
    print(f"Warning: Could not create default users: {e}")
    import traceback
    traceback.print_exc()

# Global storage for label cart (from mobile API)
label_cart = []

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        db_session = get_session()
        user = db_session.query(User).filter(User.id == session['user_id']).first()
        if not user or user.role != UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Create a fake order item class that matches the expected structure
class FakeOrderItem:
    def __init__(self, order_data, item_data, quantity, delivery_date=None):
        # Create fake order
        self.order = type('FakeOrder', (), {
            'order_number': order_data['order_number'],
            'customer': type('FakeCustomer', (), {
                'name': order_data['customer_name'],
                'name_index': order_data['customer_name_index']
            })()
        })()
        
        # Create fake item
        self.item = type('FakeItem', (), {
            'customer_item_name': item_data.get('customer_item_name'),
            'customer_code': item_data['customer_code'],
            'product': type('FakeProduct', (), {
                'name': item_data['product_name'],
                'weight_per_unit': item_data.get('weight_per_unit', 0)
            })()
        })()
        
        self.quantity = quantity
        self.delivery_date = delivery_date

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'GET':
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Login - Orders Management System</title>
            <style>
                * { box-sizing: border-box; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                    margin: 0; 
                    padding: 0;
                    background: #f8f9fa;
                    color: #333;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }
                .login-container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 400px;
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .header h1 {
                    margin: 0;
                    color: #333;
                    font-size: 1.8rem;
                    font-weight: 300;
                }
                .form-group {
                    margin-bottom: 20px;
                }
                label {
                    display: block;
                    margin-bottom: 5px;
                    color: #555;
                    font-weight: 500;
                }
                input[type="text"], input[type="password"] {
                    width: 100%;
                    padding: 12px;
                    border: 2px solid #e1e5e9;
                    border-radius: 6px;
                    font-size: 16px;
                    transition: border-color 0.3s;
                }
                input[type="text"]:focus, input[type="password"]:focus {
                    outline: none;
                    border-color: #667eea;
                }
                .btn {
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                .btn:hover {
                    transform: translateY(-1px);
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
            <div class="login-container">
                <div class="header">
                    <h1>Orders Management System</h1>
                    <p>Please log in to continue</p>
                </div>
                <form method="POST" id="loginForm">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn">Login</button>
                    <div id="message"></div>
                </form>
            </div>
            <script>
                document.getElementById('loginForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    const response = await fetch('/login', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    const messageDiv = document.getElementById('message');
                    
                    if (result.success) {
                        messageDiv.className = 'success';
                        messageDiv.textContent = 'Login successful! Redirecting...';
                        setTimeout(() => {
                            window.location.href = '/';
                        }, 1000);
                    } else {
                        messageDiv.className = 'error';
                        messageDiv.textContent = result.error || 'Login failed';
                    }
                });
            </script>
        </body>
        </html>
        """
        return html
    
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'})
        
        db_session = get_session()
        user = authenticate_user(db_session, username, password)
        
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role.value
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'error': 'Invalid username or password'})

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users (admin only)"""
    try:
        db_session = get_session()
        users = db_session.query(User).all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'role_display': get_role_display_name(user.role),
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            })
        
        return jsonify({
            'success': True,
            'users': users_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    """Create a new user (admin only)"""
    try:
        data = request.json
        db_session = get_session()
        
        # Check if user already exists
        existing_user = db_session.query(User).filter(User.username == data['username']).first()
        if existing_user:
            return jsonify({'success': False, 'error': 'Username already exists'})
        
        # Create new user
        new_user = User(
            username=data['username'],
            password_hash=hash_password(data['password']),
            email=data.get('email'),
            role=UserRole(data['role']),
            is_active=data.get('is_active', True)
        )
        
        db_session.add(new_user)
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user_id': new_user.id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user (admin only)"""
    try:
        data = request.json
        db_session = get_session()
        
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Update fields
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = UserRole(data['role'])
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data and data['password']:
            user.password_hash = hash_password(data['password'])
        
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete user (admin only)"""
    try:
        db_session = get_session()
        user = db_session.query(User).filter(User.id == user_id).first()
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Don't allow deleting the current user
        if user.id == session.get('user_id'):
            return jsonify({'success': False, 'error': 'Cannot delete your own account'})
        
        db_session.delete(user)
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
@login_required
def index():
    """Mobile app home screen with 3 tiles"""
    try:
        # Get user info for display
        db_session = get_session()
        user = db_session.query(User).filter(User.id == session['user_id']).first()
        
        if not user:
            return redirect(url_for('login'))
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Orders Mobile</title>
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                    margin: 0; 
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container { 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background: white; 
                    padding: 20px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 { 
                    color: #333; 
                    text-align: center; 
                    margin-bottom: 30px;
                }
                .grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin-top: 30px;
                }
                .square {
                    aspect-ratio: 1;
                    border-radius: 15px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                    text-align: center;
                    text-decoration: none;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    transition: transform 0.2s, box-shadow 0.2s;
                }
                .square:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                }
                .square:active {
                    transform: translateY(0);
                }
                .labels { background: linear-gradient(135deg, #007AFF, #0056CC); }
                .orders { background: linear-gradient(135deg, #34C759, #28A745); }
                .news { background: linear-gradient(135deg, #FF6B35, #E55A2B); }
                .user-info {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding: 10px;
                    background: #f8f9fa;
                    border-radius: 8px;
                }
                .user-role {
                    background: #007AFF;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: bold;
                }
                .logout-btn {
                    padding: 6px 12px;
                    background: #dc3545;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-size: 12px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="user-info">
                    <div>
                        <span>Welcome, <strong>{{ session.get('username', 'User') }}</strong></span>
                        <span class="user-role">{{ get_role_display_name(user_role) }}</span>
                    </div>
                    <a href="/logout" class="logout-btn">Logout</a>
                </div>
                
                <h1>💎 Orders Mobile</h1>
                
                <div class="grid">
                    <a href="/orders" class="square orders">
                        📋<br>Orders
                    </a>
                    <a href="/labels" class="square labels">
                        🏷️<br>Labels
                    </a>
                    <a href="/news" class="square news">
                        📰<br>News
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html, session=session, get_role_display_name=get_role_display_name, user_role=user.role)
    except Exception as e:
        print(f"Error in mobile home route: {e}")
        import traceback
        traceback.print_exc()
        return f"Internal Server Error: {str(e)}", 500

@app.route('/api/dashboard-metrics')
def dashboard_metrics():
    """Get dashboard metrics"""
    try:
        db_session = get_session()
        
        # Total orders
        total_orders = db_session.query(Order).count()
        
        # Active customers this month
        this_month = datetime.now().replace(day=1)
        active_customers = db_session.query(Order.customer_id).filter(
            Order.order_date >= this_month
        ).distinct().count()
        
        # Pending deliveries this week
        this_week = datetime.now().date() - timedelta(days=7)
        pending_deliveries = db_session.query(OrderItem).filter(
            and_(
                OrderItem.delivery_date >= this_week,
                OrderItem.delivered_quantity < OrderItem.quantity
            )
        ).count()
        
        # Active employees
        active_employees = db_session.query(Employee).filter(
            Employee.is_active == True
        ).count()
        
        return jsonify({
            'success': True,
            'metrics': {
                'total_orders': total_orders,
                'active_customers': active_customers,
                'pending_deliveries': pending_deliveries,
                'active_employees': active_employees
            }
        })
        
    except Exception as e:
        print(f"Error in dashboard metrics: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/orders')
@login_required
def orders_page():
    """Mobile orders page with filtering support"""
    from flask import request
    
    # Get filter parameters from URL
    filter_type = request.args.get('filter', '')
    filter_value = request.args.get('value', '')
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Order Items - Orders Mobile</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                padding: 20px;
                background: #f5f5f5;
            }
            .container { 
                max-width: 600px; 
                margin: 0 auto; 
                background: white; 
                padding: 20px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { 
                color: #333; 
                text-align: center; 
                margin-bottom: 30px;
            }
            .back-btn {
                display: inline-block;
                padding: 10px 20px;
                background: #6C757D;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 20px;
                font-weight: bold;
            }
            .back-btn:hover {
                background: #5A6268;
            }
            select { 
                width: 100%; 
                padding: 12px; 
                margin: 10px 0; 
                border: 1px solid #ddd; 
                border-radius: 5px; 
                font-size: 16px;
            }
            select:disabled { 
                background: #f5f5f5; 
                color: #999;
            }
            .order-item {
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                border-left: 4px solid #28A745;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .order-item.delivered {
                border-left-color: #28A745;
            }
            .order-item.partial {
                border-left-color: #FD7E14;
            }
            .order-item.undelivered {
                border-left-color: #DC3545;
            }
            
            .order-item h3 {
                margin: 0 0 10px 0;
                color: #333;
            }
            
            .order-item p {
                margin: 5px 0;
                color: #666;
            }
            
            .status-delivered {
                color: #28A745;
                font-weight: bold;
            }
            
            .status-undelivered {
                color: #DC3545;
                font-weight: bold;
            }
            
            .loading {
                text-align: center;
                color: #666;
                font-style: italic;
                padding: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Home</a>
            <h1>📋 Order Items</h1>
            <div id="filter-status" style="display: none; background: #e3f2fd; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #2196F3;">
                <strong>🔍 Auto-filtering...</strong> <span id="filter-message"></span>
            </div>
            
            <label for="customers">Customer:</label>
            <select id="customers" onchange="loadOrders()">
                <option value="">Select customer...</option>
            </select>
            
            <label for="orders">Order:</label>
            <select id="orders" onchange="loadOrderItems()" disabled>
                <option value="">Select order...</option>
            </select>
            
            <label for="filter">Filter:</label>
            <select id="filter" onchange="loadOrderItems()">
                <option value="all">All Items</option>
                <option value="undelivered">Not Yet Delivered</option>
            </select>
            
            <div id="order-items"></div>
        </div>

        <script>
            // Load customers on page load
            window.onload = function() {
                loadCustomers();
            };

            async function loadCustomers() {
                try {
                    const response = await fetch('/api/customers');
                    const customers = await response.json();
                    
                    const select = document.getElementById('customers');
                    select.innerHTML = '<option value="">Select customer...</option>';
                    
                    customers.forEach(customer => {
                        const option = document.createElement('option');
                        option.value = customer.id;
                        option.textContent = customer.display_name || customer.name_index || customer.name;
                        select.appendChild(option);
                    });
                } catch (error) {
                    console.error('Error loading customers:', error);
                }
            }

            async function loadOrders() {
                const customerId = document.getElementById('customers').value;
                const ordersSelect = document.getElementById('orders');
                const orderItemsDiv = document.getElementById('order-items');
                
                if (!customerId) {
                    ordersSelect.innerHTML = '<option value="">Select order...</option>';
                    ordersSelect.disabled = true;
                    orderItemsDiv.innerHTML = '';
                    return;
                }

                try {
                    const response = await fetch(`/api/orders/${customerId}`);
                    const orders = await response.json();
                    
                    ordersSelect.innerHTML = '<option value="">Select order...</option>';
                    orders.forEach(order => {
                        const option = document.createElement('option');
                        option.value = order.id;
                        option.textContent = order.order_number;
                        ordersSelect.appendChild(option);
                    });
                    ordersSelect.disabled = false;
                    
                    // Clear order items
                    orderItemsDiv.innerHTML = '';
                    
                    return orders; // Return orders for external use
                } catch (error) {
                    console.error('Error loading orders:', error);
                    return [];
                }
            }

            async function loadOrderItems() {
                const orderId = document.getElementById('orders').value;
                const filterValue = document.getElementById('filter').value;
                const orderItemsDiv = document.getElementById('order-items');
                
                if (!orderId) {
                    orderItemsDiv.innerHTML = '';
                    return;
                }

                orderItemsDiv.innerHTML = '<div class="loading">Loading order items...</div>';

                try {
                    const response = await fetch(`/api/order-items/${orderId}`);
                    const orderItems = await response.json();
                    
                    if (orderItems.length === 0) {
                        orderItemsDiv.innerHTML = '<p>No items found for this order.</p>';
                        return;
                    }
                    
                    // Filter items based on selection
                    let filteredItems = orderItems;
                    if (filterValue === 'undelivered') {
                        filteredItems = orderItems.filter(item => {
                            const delivered = item.delivered_quantity;
                            const total = item.quantity;
                            return delivered < total; // Show only items that are not fully delivered
                        });
                    }
                    
                    if (filteredItems.length === 0) {
                        orderItemsDiv.innerHTML = '<p>No items match the selected filter.</p>';
                        return;
                    }
                    
                    let html = '';
                    filteredItems.forEach(item => {
                        const delivered = item.delivered_quantity;
                        const total = item.quantity;
                        const undelivered = total - delivered;
                        let statusClass = '';
                        let statusText = '';
                        if (delivered >= total) {
                            statusClass = 'delivered';
                            statusText = 'Delivered';
                        } else if (delivered === 0) {
                            statusClass = 'undelivered';
                            statusText = `0/${total} delivered`;
                        } else {
                            statusClass = 'partial';
                            statusText = `${delivered}/${total} delivered`;
                        }
                        html += `
                            <div class="order-item ${statusClass}">
                                <h3>${item.item_name} (${item.customer_code})</h3>
                                <p><strong>Product:</strong> ${item.product_name}</p>
                                <p><strong>Quantity:</strong> ${total}</p>
                                <p><strong>Delivered:</strong> ${delivered}</p>
                                <p><strong>Remaining:</strong> ${undelivered}</p>
                                <p class="status-${statusClass}"><strong>Status:</strong> ${statusText}</p>
                                ${item.delivery_date ? `<p><strong>Delivery Date:</strong> ${item.delivery_date}</p>` : ''}
                            </div>
                        `;
                    });
                    
                    orderItemsDiv.innerHTML = html;
                } catch (error) {
                    console.error('Error loading order items:', error);
                    orderItemsDiv.innerHTML = '<p>Error loading order items.</p>';
                }
            }
            
            // Handle URL parameters for filtering
            async function handleUrlParameters() {
                const urlParams = new URLSearchParams(window.location.search);
                const filterType = urlParams.get('filter');
                const filterValue = urlParams.get('value');
                
                if (filterType === 'order' && filterValue) {
                    console.log('Auto-filtering for order:', filterValue);
                    
                    // Show status message
                    const statusDiv = document.getElementById('filter-status');
                    const messageSpan = document.getElementById('filter-message');
                    statusDiv.style.display = 'block';
                    messageSpan.textContent = `Looking for order: ${filterValue}`;
                    
                    try {
                        // First, we need to find which customer has this order
                        const customersResponse = await fetch('/api/customers');
                        const customers = await customersResponse.json();
                        
                        messageSpan.textContent = `Searching through ${customers.length} customers...`;
                        
                        // Search through each customer's orders to find the target order
                        for (const customer of customers) {
                            const ordersResponse = await fetch(`/api/orders/${customer.id}`);
                            const orders = await ordersResponse.json();
                            
                            const targetOrder = orders.find(order => order.order_number === filterValue);
                            if (targetOrder) {
                                console.log('Found order in customer:', customer.name);
                                messageSpan.textContent = `Found order in customer: ${customer.name}`;
                                
                                // Set the customer dropdown
                                const customerSelect = document.getElementById('customers');
                                customerSelect.value = customer.id;
                                
                                // Trigger order loading
                                await loadOrders();
                                
                                // Wait a bit for orders to load, then select the target order
                                setTimeout(() => {
                                    const ordersSelect = document.getElementById('orders');
                                    if (ordersSelect) {
                                        for (let i = 0; i < ordersSelect.options.length; i++) {
                                            if (ordersSelect.options[i].textContent === filterValue) {
                                                ordersSelect.selectedIndex = i;
                                                ordersSelect.dispatchEvent(new Event('change'));
                                                console.log('Order selected:', filterValue);
                                                messageSpan.textContent = `Order selected: ${filterValue}`;
                                                
                                                // Hide status after a delay
                                                setTimeout(() => {
                                                    statusDiv.style.display = 'none';
                                                }, 2000);
                                                break;
                                            }
                                        }
                                    }
                                }, 500);
                                
                                break;
                            }
                        }
                    } catch (error) {
                        console.error('Error auto-filtering:', error);
                        messageSpan.textContent = `Error: ${error.message}`;
                    }
                }
            }
            
            // Load initial data and handle URL parameters
            handleUrlParameters();
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/news')
@login_required
def news_page():
    """News page showing recent order activity"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>News - Orders Mobile</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                padding: 20px;
                background: #f5f5f5;
            }
            .container { 
                max-width: 600px; 
                margin: 0 auto; 
                background: white; 
                padding: 20px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { 
                color: #333; 
                text-align: center; 
                margin-bottom: 30px;
            }
            .back-btn {
                display: inline-block;
                padding: 10px 20px;
                background: #6C757D;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 20px;
                font-weight: bold;
            }
            .back-btn:hover {
                background: #5A6268;
            }
            .news-item {
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                border-left: 4px solid #FF6B35;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .news-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            .news-item.created {
                border-left-color: #28A745;
            }
            .news-item.updated {
                border-left-color: #007AFF;
            }
            .news-item.delivery {
                border-left-color: #6F42C1;
            }
            .news-item.deleted {
                border-left-color: #DC3545;
            }
            .news-time {
                color: #666;
                font-size: 12px;
                margin-bottom: 5px;
            }
            .news-title {
                font-weight: bold;
                margin-bottom: 5px;
                color: #333;
            }
            .news-details {
                color: #666;
                font-size: 14px;
            }
            .loading {
                text-align: center;
                color: #666;
                font-style: italic;
                padding: 20px;
            }
            .refresh-btn {
                background: #FF6B35;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin-bottom: 20px;
            }
            .refresh-btn:hover {
                background: #E55A2B;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Home</a>
            <h1>📰 Recent Activity</h1>
            
            <button onclick="loadNews()" class="refresh-btn">🔄 Refresh</button>
            
            <div id="news-content">
                <div class="loading">Loading recent activity...</div>
            </div>
        </div>

        <script>
            function loadNews() {
                document.getElementById('news-content').innerHTML = '<div class="loading">Loading recent activity...</div>';
                
                fetch('/api/news')
                    .then(response => response.json())
                    .then(data => {
                        const newsContent = document.getElementById('news-content');
                        
                        if (data.length === 0) {
                            newsContent.innerHTML = '<div class="loading">No recent activity found in the last 24 hours.</div>';
                            return;
                        }
                        
                        let html = '';
                        data.forEach(item => {
                            const timeAgo = getTimeAgo(new Date(item.timestamp));
                            const actionClass = item.action.toLowerCase();
                            const clickHandler = item.link ? `onclick="navigateToOrder('${item.link}')"` : '';
                            
                            html += `
                                <div class="news-item ${actionClass}" ${clickHandler}>
                                    <div class="news-time">${timeAgo}</div>
                                    <div class="news-title">${item.title}</div>
                                    <div class="news-details">${item.details}</div>
                                </div>
                            `;
                        });
                        
                        newsContent.innerHTML = html;
                    })
                    .catch(error => {
                        console.error('Error loading news:', error);
                        document.getElementById('news-content').innerHTML = '<div class="loading">Error loading recent activity.</div>';
                    });
            }
            
            function getTimeAgo(date) {
                const now = new Date();
                const diffMs = now - date;
                const diffMins = Math.floor(diffMs / 60000);
                const diffHours = Math.floor(diffMs / 3600000);
                const diffDays = Math.floor(diffMs / 86400000);
                
                if (diffMins < 1) return 'Just now';
                if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
                if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
                return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
            }
            
            // Load news when page loads
            loadNews();
            
            function navigateToOrder(link) {
                // Navigate to the orders page with the filter
                window.location.href = link;
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/all-orders')
def get_all_orders():
    """Get all orders with items"""
    try:
        db_session = get_session()
        
        orders = db_session.query(Order).all()
        orders_data = []
        
        for order in orders:
            items = []
            for order_item in order.items:
                delivered_qty = order_item.delivered_quantity or 0
                total_qty = order_item.quantity
                
                # Determine status
                if delivered_qty == 0:
                    status = 'pending'
                elif delivered_qty < total_qty:
                    status = 'partial'
                else:
                    status = 'complete'
                
                items.append({
                    'id': order_item.id,
                    'product_name': order_item.item.product.name,
                    'customer_code': order_item.item.customer_code,
                    'quantity': total_qty,
                    'delivered_quantity': delivered_qty,
                    'delivery_date': order_item.delivery_date.isoformat() if order_item.delivery_date else None
                })
            
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'order_date': order.order_date.isoformat(),
                'customer_id': order.customer_id,
                'customer_name': order.customer.name,
                'customer_index': order.customer.name_index,
                'items': items,
                'status': 'complete' if all(item['delivered_quantity'] >= item['quantity'] for item in items) else 'partial' if any(item['delivered_quantity'] > 0 for item in items) else 'pending'
            })
        
        return jsonify({
            'success': True,
            'orders': orders_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Include all the existing mobile API routes
@app.route('/labels')
@login_required
def labels_page():
    """Mobile label generation page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Labels - Orders Mobile</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                padding: 20px;
                background: #f5f5f5;
            }
            .container { 
                max-width: 600px; 
                margin: 0 auto; 
                background: white; 
                padding: 20px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { 
                color: #333; 
                text-align: center; 
                margin-bottom: 30px;
            }
            .back-btn {
                display: inline-block;
                padding: 10px 20px;
                background: #6C757D;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 20px;
                font-weight: bold;
            }
            .back-btn:hover {
                background: #5A6268;
            }
            select, button, input { 
                width: 100%; 
                padding: 12px; 
                margin: 10px 0; 
                border: 1px solid #ddd; 
                border-radius: 5px; 
                font-size: 16px;
            }
            select:disabled { 
                background: #f5f5f5; 
                color: #999;
            }
            button { 
                background: #007AFF; 
                color: white; 
                border: none; 
                cursor: pointer;
            }
            button:hover { 
                background: #0056CC;
            }
            button:disabled { 
                background: #ccc; 
                cursor: not-allowed;
            }
            .label-preview { 
                margin-top: 20px; 
                padding: 15px; 
                background: #f9f9f9; 
                border-radius: 5px; 
                border: 1px solid #ddd;
            }
            .loading { 
                text-align: center; 
                color: #666; 
                font-style: italic;
            }
            .button-group {
                display: flex;
                gap: 10px;
                margin: 20px 0;
            }
            
            .cart-section {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
            }
            
            .cart-info {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }
            
            .cart-items {
                max-height: 300px;
                overflow-y: auto;
            }
            
            .cart-item {
                background: white;
                padding: 10px;
                margin: 5px 0;
                border-radius: 5px;
                border-left: 4px solid #007bff;
            }
            
            .cart-list {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Home</a>
            <h1>🏷️ Labels</h1>
            
            <label for="customers">Customer:</label>
            <select id="customers" onchange="loadOrders()">
                <option value="">Select customer...</option>
            </select>
            
            <label for="orders">Order:</label>
            <select id="orders" onchange="loadItems()" disabled>
                <option value="">Select order...</option>
            </select>
            
            <label for="items">Item:</label>
            <select id="items" onchange="updateLabelPreview()" disabled>
                <option value="">Select item...</option>
            </select>
            
            <div class="form-group">
                <label for="quantity">Quantity:</label>
                <input type="number" id="quantity" min="1" value="1" class="form-control">
            </div>
            
            <div class="form-group">
                <label for="delivery_date">Delivery Date:</label>
                <select id="delivery_date" class="form-control" disabled>
                    <option value="">Select delivery date...</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="layout">Label Layout:</label>
                <select id="layout" class="form-control">
                    <option value="2x3">6 labels per page (2x3)</option>
                    <option value="2x2">4 labels per page (2x2)</option>
                </select>
            </div>
            
            <div class="button-group">
                <button onclick="addToCart()" class="btn btn-primary">Add to Cart</button>
                <button id="generateBtn" onclick="generateLabel()" class="btn btn-success">Generate Single Label</button>
            </div>
            
            <div class="cart-section">
                <h3>Label Cart</h3>
                <div class="cart-info">
                    <span id="cart-count">0</span> labels in cart
                    <button onclick="viewCart()" class="btn btn-info btn-sm">View Cart</button>
                    <button onclick="clearCart()" class="btn btn-warning btn-sm">Clear Cart</button>
                    <button onclick="exportLabels()" class="btn btn-success btn-sm">Export All Labels</button>
                </div>
                <div id="cart-items" class="cart-items"></div>
            </div>
            
            <div id="preview" class="preview-section" style="display: none;">
                <h3>Label Preview</h3>
                <div id="preview-content"></div>
            </div>
        </div>

        <script>
            // Load customers on page load
            window.onload = function() {
                loadCustomers();
            };

            async function loadCustomers() {
                try {
                    console.log('Loading customers...');
                    const response = await fetch('/api/customers');
                    console.log('Response status:', response.status);
                    console.log('Response headers:', response.headers);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const customers = await response.json();
                    console.log('Customers data:', customers);
                    
                    if (!Array.isArray(customers)) {
                        console.error('Customers is not an array:', customers);
                        alert('Error: Customers data is not in expected format');
                        return;
                    }
                    
                    const select = document.getElementById('customers');
                    select.innerHTML = '<option value="">Select customer...</option>';
                    
                    customers.forEach(customer => {
                        const option = document.createElement('option');
                        option.value = customer.id;
                        option.textContent = customer.display_name || customer.name_index || customer.name;
                        select.appendChild(option);
                    });
                    console.log('Customers loaded successfully. Total customers:', customers.length);
                } catch (error) {
                    console.error('Error loading customers:', error);
                    alert('Error loading customers: ' + error.message);
                }
            }

            async function loadOrders() {
                const customerId = document.getElementById('customers').value;
                const ordersSelect = document.getElementById('orders');
                const itemsSelect = document.getElementById('items');
                
                if (!customerId) {
                    ordersSelect.innerHTML = '<option value="">Select order...</option>';
                    ordersSelect.disabled = true;
                    itemsSelect.innerHTML = '<option value="">Select item...</option>';
                    itemsSelect.disabled = true;
                    return;
                }

                try {
                    const response = await fetch(`/api/orders/${customerId}`);
                    const orders = await response.json();
                    
                    ordersSelect.innerHTML = '<option value="">Select order...</option>';
                    orders.forEach(order => {
                        const option = document.createElement('option');
                        option.value = order.id;
                        option.textContent = order.order_number;
                        ordersSelect.appendChild(option);
                    });
                    ordersSelect.disabled = false;
                    
                    // Reset items
                    itemsSelect.innerHTML = '<option value="">Select item...</option>';
                    itemsSelect.disabled = true;
                } catch (error) {
                    console.error('Error loading orders:', error);
                }
            }

            async function loadItems() {
                const orderId = document.getElementById('orders').value;
                const itemsSelect = document.getElementById('items');
                const quantityInput = document.getElementById('quantity');
                const deliveryDateSelect = document.getElementById('delivery_date');
                
                if (!orderId) {
                    itemsSelect.innerHTML = '<option value="">Select item...</option>';
                    itemsSelect.disabled = true;
                    quantityInput.disabled = true;
                    deliveryDateSelect.innerHTML = '<option value="">Select delivery date...</option>';
                    deliveryDateSelect.disabled = true;
                    return;
                }

                try {
                    const response = await fetch(`/api/undelivered-items/${orderId}`);
                    const items = await response.json();
                    
                    itemsSelect.innerHTML = '<option value="">Select item...</option>';
                    items.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item.customer_code; // Use customer_code as value
                        option.textContent = `${item.customer_item_name} (${item.customer_code}) - ${item.total_undelivered} remaining`;
                        option.dataset.remaining = item.total_undelivered;
                        option.dataset.itemName = item.customer_item_name;
                        option.dataset.itemCode = item.customer_code;
                        option.dataset.orderItems = JSON.stringify(item.order_items);
                        itemsSelect.appendChild(option);
                    });
                    itemsSelect.disabled = false;
                } catch (error) {
                    console.error('Error loading items:', error);
                }
            }

            function updateLabelPreview() {
                const itemSelect = document.getElementById('items');
                const quantityInput = document.getElementById('quantity');
                const deliveryDateSelect = document.getElementById('delivery_date');
                const selectedOption = itemSelect.options[itemSelect.selectedIndex];
                const preview = document.getElementById('preview');
                const content = document.getElementById('preview-content');
                const generateBtn = document.getElementById('generateBtn');
                
                if (itemSelect.value) {
                    const customerSelect = document.getElementById('customers');
                    const orderSelect = document.getElementById('orders');
                    const customerText = customerSelect.options[customerSelect.selectedIndex].text;
                    const orderText = orderSelect.options[orderSelect.selectedIndex].text;
                    
                    // Enable quantity input and set max value
                    quantityInput.disabled = false;
                    quantityInput.max = selectedOption.dataset.remaining;
                    quantityInput.value = Math.min(quantityInput.value, selectedOption.dataset.remaining);
                    
                    // Populate delivery date dropdown
                    deliveryDateSelect.innerHTML = '<option value="">Select delivery date...</option>';
                    if (selectedOption.dataset.orderItems) {
                        const orderItems = JSON.parse(selectedOption.dataset.orderItems);
                        const uniqueDates = new Set();
                        
                        orderItems.forEach(item => {
                            if (item.delivery_date) {
                                const date = new Date(item.delivery_date);
                                const formattedDate = date.toISOString().split('T')[0]; // YYYY-MM-DD format
                                uniqueDates.add(formattedDate);
                            }
                        });
                        
                        // Sort dates and add to dropdown
                        Array.from(uniqueDates).sort().forEach(date => {
                            const option = document.createElement('option');
                            option.value = date;
                            option.textContent = date;
                            deliveryDateSelect.appendChild(option);
                        });
                    }
                    deliveryDateSelect.disabled = false;
                    
                    const quantity = quantityInput.value;
                    
                    content.innerHTML = `
                        <p><strong>Customer:</strong> ${customerText}</p>
                        <p><strong>Order:</strong> ${orderText}</p>
                        <p><strong>Item:</strong> ${selectedOption.dataset.itemName} (${selectedOption.dataset.itemCode})</p>
                        <p><strong>Quantity:</strong> ${quantity} of ${selectedOption.dataset.remaining} remaining</p>
                    `;
                    preview.style.display = 'block';
                    generateBtn.disabled = false;
                } else {
                    quantityInput.disabled = true;
                    deliveryDateSelect.innerHTML = '<option value="">Select delivery date...</option>';
                    deliveryDateSelect.disabled = true;
                    preview.style.display = 'none';
                    generateBtn.disabled = true;
                }
            }

            async function generateLabel() {
                const customerId = document.getElementById('customers').value;
                const orderId = document.getElementById('orders').value;
                const itemCode = document.getElementById('items').value; // Use itemCode as value
                const quantity = document.getElementById('quantity').value;
                const deliveryDate = document.getElementById('delivery_date').value;
                const layout = document.getElementById('layout').value;
                
                if (!customerId || !orderId || !itemCode || !quantity || !deliveryDate) {
                    alert('Please select customer, order, item, delivery date and set quantity');
                    return;
                }

                // Get username from prompt or use default
                const username = prompt('Enter your name (optional):') || 'mobile_user';

                try {
                    const response = await fetch('/api/generate-label', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            customer_id: customerId,
                            order_id: orderId,
                            item_code: itemCode,
                            quantity: parseInt(quantity),
                            delivery_date: deliveryDate,
                            layout: layout,
                            username: username
                        })
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        alert(result.message);
                        // Try to download the label PDF with fallback
                        tryDownload(result.filename);
                    } else {
                        alert('Error generating label: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error generating label:', error);
                    alert('Error generating label');
                }
            }

            function tryDownload(filename) {
                // Try automatic download first
                const downloadUrl = `/api/download/${filename}`;
                
                // Create a temporary link element
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = filename;
                link.target = '_blank';
                
                // Try to trigger download
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                // Fallback: show manual download link
                setTimeout(() => {
                    const manualDownload = confirm(
                        "If the file didn't download automatically, click OK to open it in a new tab.\\nYou can then save it manually from your browser."
                    );
                    if (manualDownload) {
                        window.open(downloadUrl, '_blank');
                    }
                }, 1000);
            }

            async function addToCart() {
                const customerId = document.getElementById('customers').value;
                const orderId = document.getElementById('orders').value;
                const itemCode = document.getElementById('items').value;
                const quantity = document.getElementById('quantity').value;
                const deliveryDate = document.getElementById('delivery_date').value;
                const layout = document.getElementById('layout').value;
                
                if (!customerId || !orderId || !itemCode || !quantity || !deliveryDate) {
                    alert('Please select customer, order, item, delivery date and set quantity');
                    return;
                }

                try {
                    const response = await fetch('/api/add-to-cart', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            customer_id: customerId,
                            order_id: orderId,
                            item_code: itemCode,
                            quantity: parseInt(quantity),
                            delivery_date: deliveryDate,
                            layout: layout
                        })
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        alert(result.message);
                        document.getElementById('cart-count').textContent = result.cart_count;
                        // Clear form for next label
                        document.getElementById('quantity').value = '1';
                    } else {
                        alert('Error adding label: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error adding label:', error);
                    alert('Error adding label');
                }
            }

            async function viewCart() {
                try {
                    const response = await fetch('/api/cart');
                    const result = await response.json();
                    
                    if (result.success) {
                        const cartItems = document.getElementById('cart-items');
                        if (result.items.length === 0) {
                            cartItems.innerHTML = '<p>Cart is empty</p>';
                        } else {
                            let html = '<div class="cart-list">';
                            result.items.forEach((item, index) => {
                                html += `
                                    <div class="cart-item">
                                        <div style="display: flex; justify-content: space-between; align-items: start;">
                                            <div style="flex: 1;">
                                                <strong>${item.customer}</strong><br>
                                                Order: ${item.order} | Item: ${item.item}<br>
                                                Code: ${item.code} | Qty: ${item.quantity}
                                            </div>
                                            <button onclick="deleteCartItem(${index})" style="background: #DC3545; color: white; border: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;">×</button>
                                        </div>
                                    </div>
                                `;
                            });
                            html += '</div>';
                            cartItems.innerHTML = html;
                        }
                    } else {
                        alert('Error loading cart: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error loading cart:', error);
                    alert('Error loading cart');
                }
            }

            async function deleteCartItem(index) {
                if (!confirm('Are you sure you want to remove this item from the cart?')) {
                    return;
                }

                try {
                    const response = await fetch(`/api/delete-cart-item/${index}`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        alert(result.message);
                        document.getElementById('cart-count').textContent = result.cart_count;
                        viewCart(); // Refresh the cart display
                    } else {
                        alert('Error deleting item: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error deleting item:', error);
                    alert('Error deleting item');
                }
            }

            async function clearCart() {
                if (!confirm('Are you sure you want to clear the cart?')) {
                    return;
                }

                try {
                    const response = await fetch('/api/cart/clear', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        alert(result.message);
                        document.getElementById('cart-count').textContent = '0';
                        document.getElementById('cart-items').innerHTML = '';
                    } else {
                        alert('Error clearing cart: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error clearing cart:', error);
                    alert('Error clearing cart');
                }
            }

            async function exportLabels() {
                // Get username from prompt or use default
                const username = prompt('Enter your name (optional):') || 'mobile_user';
                const layout = document.getElementById('layout').value;
                
                try {
                    const response = await fetch('/api/cart/generate-labels', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            username: username,
                            layout: layout
                        })
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        alert(result.message);
                        // Update cart count
                        document.getElementById('cart-count').textContent = result.cart_count;
                        // Clear cart display
                        document.getElementById('cart-items').innerHTML = '';
                        // Try to download the labels PDF with fallback
                        tryDownload(result.filename);
                    } else {
                        alert('Error exporting labels: ' + result.error);
                    }
                } catch (error) {
                    console.error('Error exporting labels:', error);
                    alert('Error exporting labels');
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/production')
@login_required
def production_page():
    """Production planning page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Production Planning</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                padding: 20px;
                background: #f8f9fa;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            }
            .header {
                display: flex;
                align-items: center;
                gap: 20px;
                margin-bottom: 30px;
            }
            .back-btn {
                padding: 10px 20px;
                background: #6c757d;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
            }
            h1 { 
                margin: 0;
                color: #2c3e50;
            }
            .filters {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            select, input { 
                width: 100%; 
                padding: 12px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                font-size: 16px;
            }
            .plans-grid {
                display: grid;
                gap: 20px;
            }
            .plan-card {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                border-left: 4px solid #4facfe;
            }
            .plan-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            .plan-type {
                font-weight: bold;
                font-size: 1.1rem;
                color: #2c3e50;
            }
            .plan-date {
                color: #6c757d;
                font-size: 0.9rem;
            }
            .customer-name {
                font-weight: 600;
                color: #495057;
                margin-bottom: 10px;
            }
            .loading {
                text-align: center;
                padding: 40px;
                color: #6c757d;
            }
            .add-plan-btn {
                background: #4facfe;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                margin-bottom: 20px;
            }
            .add-plan-btn:hover {
                background: #3a8bfd;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/" class="back-btn">← Back</a>
                <h1>🏭 Production Planning</h1>
            </div>
            
            <button class="add-plan-btn" onclick="showAddPlanForm()">+ Add Production Plan</button>
            
            <div class="filters">
                <select id="plan-type-filter">
                    <option value="">All Plan Types</option>
                    <option value="type1">Type 1</option>
                    <option value="type2">Type 2</option>
                    <option value="type3">Type 3</option>
                </select>
                <select id="customer-filter">
                    <option value="">All Customers</option>
                </select>
                <input type="date" id="date-filter" placeholder="Filter by date">
            </div>
            
            <div id="plans-container">
                <div class="loading">Loading production plans...</div>
            </div>
        </div>
        
        <script>
            let allPlans = [];
            
            async function loadCustomers() {
                try {
                    const response = await fetch('/api/customers');
                    const data = await response.json();
                    
                    if (data.success) {
                        const select = document.getElementById('customer-filter');
                        data.customers.forEach(customer => {
                            const option = document.createElement('option');
                            option.value = customer.id;
                            option.textContent = `${customer.name_index} - ${customer.name}`;
                            select.appendChild(option);
                        });
                    }
                } catch (error) {
                    console.error('Error loading customers:', error);
                }
            }
            
            async function loadProductionPlans() {
                try {
                    const response = await fetch('/api/production-plans');
                    const data = await response.json();
                    
                    if (data.success) {
                        allPlans = data.plans;
                        displayPlans(allPlans);
                    }
                } catch (error) {
                    console.error('Error loading production plans:', error);
                }
            }
            
            function displayPlans(plans) {
                const container = document.getElementById('plans-container');
                
                if (plans.length === 0) {
                    container.innerHTML = '<div class="loading">No production plans found</div>';
                    return;
                }
                
                container.innerHTML = plans.map(plan => `
                    <div class="plan-card">
                        <div class="plan-header">
                            <div>
                                <div class="plan-type">${plan.plan_type.toUpperCase()}</div>
                                <div class="plan-date">${plan.delivery_date ? new Date(plan.delivery_date).toLocaleDateString() : 'No date'}</div>
                            </div>
                            <div class="plan-status">${plan.customer_name || 'No customer'}</div>
                        </div>
                        <div class="customer-name">
                            ${plan.customer_name ? `${plan.customer_name}` : 'No customer assigned'}
                        </div>
                        ${plan.product_name ? `<div>Product: ${plan.product_name}</div>` : ''}
                        ${plan.surface_treatment ? `<div>Surface Treatment: ${plan.surface_treatment}</div>` : ''}
                    </div>
                `).join('');
            }
            
            function showAddPlanForm() {
                // Simple form for adding production plans
                const form = prompt('Enter production plan details (JSON format):', '{"plan_type": "type1", "customer_id": 1, "delivery_date": "2025-01-15"}');
                if (form) {
                    try {
                        const planData = JSON.parse(form);
                        addProductionPlan(planData);
                    } catch (error) {
                        alert('Invalid JSON format');
                    }
                }
            }
            
            async function addProductionPlan(planData) {
                try {
                    const response = await fetch('/api/production-plans', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(planData)
                    });
                    
                    const data = await response.json();
                    if (data.success) {
                        alert('Production plan added successfully');
                        loadProductionPlans();
                    } else {
                        alert('Error adding production plan: ' + data.error);
                    }
                } catch (error) {
                    alert('Error adding production plan: ' + error);
                }
            }
            
            // Filter functionality
            document.getElementById('plan-type-filter').addEventListener('change', filterPlans);
            document.getElementById('customer-filter').addEventListener('change', filterPlans);
            document.getElementById('date-filter').addEventListener('change', filterPlans);
            
            function filterPlans() {
                const planType = document.getElementById('plan-type-filter').value;
                const customerId = document.getElementById('customer-filter').value;
                const dateFilter = document.getElementById('date-filter').value;
                
                let filtered = allPlans;
                
                if (planType) {
                    filtered = filtered.filter(plan => plan.plan_type === planType);
                }
                
                if (customerId) {
                    filtered = filtered.filter(plan => plan.customer_id == customerId);
                }
                
                if (dateFilter) {
                    filtered = filtered.filter(plan => plan.delivery_date && plan.delivery_date.startsWith(dateFilter));
                }
                
                displayPlans(filtered);
            }
            
            // Load data on page load
            loadCustomers();
            loadProductionPlans();
        </script>
    </body>
    </html>
    """
    return render_template_string(html, session=session, get_role_display_name=get_role_display_name)

@app.route('/mobile')
@login_required
def mobile_interface():
    """Redirect to mobile interface"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Mobile Interface</title>
        <style>
            body { font-family: -apple-system, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .back-btn { display: inline-block; padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 8px; margin-bottom: 20px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 30px; }
            .square { aspect-ratio: 1; border-radius: 15px; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; font-weight: bold; text-align: center; text-decoration: none; box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: transform 0.2s; }
            .square:hover { transform: translateY(-2px); }
            .labels { background: linear-gradient(135deg, #007AFF, #0056CC); }
            .orders { background: linear-gradient(135deg, #34C759, #28A745); }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Dashboard</a>
            <h1>📱 Mobile Interface</h1>
            <p>Access the mobile-optimized interface for label generation and order management.</p>
            
            <div class="grid">
                <a href="/labels" class="square labels">🏷️<br>Labels</a>
                <a href="/orders" class="square orders">📋<br>Orders</a>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, session=session, get_role_display_name=get_role_display_name)

# Include all the existing API routes from mobile_api.py
@app.route('/api/generate-label', methods=['POST'])
@login_required
def generate_label():
    """Generate a label for an order item"""
    try:
        data = request.json
        db_session = get_session()
        
        # Get order item
        order_item = db_session.query(OrderItem).filter(OrderItem.id == data['order_item_id']).first()
        if not order_item:
            return jsonify({'error': 'Order item not found'}), 404
        
        # Create fake order item for label generation
        fake_order_item = FakeOrderItem(
            order_data={
                'order_number': order_item.order.order_number,
                'customer_name': order_item.order.customer.name,
                'customer_name_index': order_item.order.customer.name_index
            },
            item_data={
                'customer_item_name': order_item.item.customer_item_name,
                'customer_code': order_item.item.customer_code,
                'product_name': order_item.item.product.name,
                'weight_per_unit': order_item.item.product.weight_per_unit
            },
            quantity=data.get('quantity', 1),
            delivery_date=order_item.delivery_date
        )
        
        # Generate label
        label_generator = LabelGenerator()
        pdf_path = label_generator.generate_label(fake_order_item)
        
        # Return the PDF file
        return send_file(pdf_path, as_attachment=True, download_name=f"label_{order_item.order.order_number}_{order_item.item.customer_code}.pdf")
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    """Add an order item to the label cart"""
    try:
        data = request.json
        db_session = get_session()
        
        # Get the order and item based on the provided data
        order = db_session.query(Order).filter(Order.id == data['order_id']).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Find the order item by customer_code
        order_item = db_session.query(OrderItem).join(Item).filter(
            and_(
                OrderItem.order_id == data['order_id'],
                Item.customer_code == data['item_code']
            )
        ).first()
        
        if not order_item:
            return jsonify({'error': 'Order item not found'}), 404
        
        # Create fake order item for cart
        fake_order_item = FakeOrderItem(
            order_data={
                'order_number': order.order_number,
                'customer_name': order.customer.name,
                'customer_name_index': order.customer.name_index
            },
            item_data={
                'customer_item_name': order_item.item.customer_item_name,
                'customer_code': order_item.item.customer_code,
                'product_name': order_item.item.product.name,
                'weight_per_unit': order_item.item.product.weight_per_unit
            },
            quantity=data.get('quantity', 1),
            delivery_date=datetime.strptime(data['delivery_date'], '%Y-%m-%d').date() if data.get('delivery_date') else None
        )
        
        # Add to cart
        label_cart.append(fake_order_item)
        
        return jsonify({
            'success': True,
            'message': 'Added to cart',
            'cart_count': len(label_cart)
        })
        
    except Exception as e:
        print(f"Error in add_to_cart: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    """Get current cart contents"""
    try:
        cart_items = []
        for item in label_cart:
            cart_items.append({
                'order': item.order.order_number,
                'customer': item.order.customer.name,
                'item': item.item.customer_item_name,
                'code': item.item.customer_code,
                'quantity': item.quantity,
                'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None
            })
        
        return jsonify({
            'success': True,
            'items': cart_items,
            'cart_count': len(label_cart)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """Clear the label cart"""
    try:
        label_cart.clear()
        return jsonify({
            'success': True,
            'message': 'Cart cleared'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cart/generate-labels', methods=['POST'])
@login_required
def generate_cart_labels():
    """Generate labels for all items in cart"""
    try:
        if not label_cart:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Generate labels for all items in cart
        label_generator = LabelGenerator()
        pdf_path = label_generator.generate_multiple_labels(label_cart)
        
        # Clear cart after generation
        label_cart.clear()
        
        # Return the PDF file
        return send_file(pdf_path, as_attachment=True, download_name=f"labels_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-cart-item/<int:index>', methods=['DELETE'])
@login_required
def delete_cart_item(index):
    """Delete an item from the cart by index"""
    try:
        if 0 <= index < len(label_cart):
            label_cart.pop(index)
            return jsonify({
                'success': True,
                'message': 'Item removed from cart',
                'cart_count': len(label_cart)
            })
        else:
            return jsonify({'error': 'Invalid index'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Get all customers"""
    try:
        print("🔍 Fetching customers from database...")
        db_session = get_session()
        
        # Try to get total count first
        total_count = db_session.query(Customer).count()
        print(f"📊 Total customers in database: {total_count}")
        
        customers = db_session.query(Customer).order_by(Customer.name_index).all()
        print(f"📋 Retrieved {len(customers)} customers")
        
        customers_data = []
        for customer in customers:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'name_index': customer.name_index,
                'display_name': f"{customer.name_index} ({customer.name})" if customer.name_index else customer.name,
                'city': customer.city,
                'country': customer.country
            })
        
        print(f"✅ Returning {len(customers_data)} customers")
        return jsonify(customers_data)
        
    except Exception as e:
        print(f"❌ Error in get_customers: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:customer_id>', methods=['GET'])
def get_orders(customer_id):
    """Get orders for a specific customer"""
    try:
        db_session = get_session()
        orders = db_session.query(Order).filter(Order.customer_id == customer_id).all()
        
        orders_data = []
        for order in orders:
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'order_date': order.order_date.isoformat(),
                'customer_name': order.customer.name
            })
        
        return jsonify(orders_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/undelivered-items/<int:order_id>', methods=['GET'])
def get_undelivered_items(order_id):
    """Get undelivered items for an order"""
    try:
        db_session = get_session()
        order_items = db_session.query(OrderItem).filter(
            and_(
                OrderItem.order_id == order_id,
                OrderItem.delivered_quantity < OrderItem.quantity
            )
        ).all()
        
        # Group by unique items like in mobile_api.py
        unique_items = {}
        for item in order_items:
            key = item.item.customer_code
            if key not in unique_items:
                unique_items[key] = {
                    'customer_code': item.item.customer_code,
                    'customer_item_name': item.item.customer_item_name or item.item.product.name,
                    'product_name': item.item.product.name,
                    'weight_per_unit': item.item.product.weight_per_unit or 0,
                    'total_undelivered': 0,
                    'order_items': []
                }
            undelivered = item.quantity - (item.delivered_quantity or 0)
            unique_items[key]['total_undelivered'] += undelivered
            unique_items[key]['order_items'].append({
                'id': item.id,
                'quantity': undelivered,
                'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None
            })
        
        return jsonify(list(unique_items.values()))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/order-items/<int:order_id>', methods=['GET'])
def get_order_items(order_id):
    """Get all items for an order"""
    try:
        db_session = get_session()
        order_items = db_session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        
        items_data = []
        for item in order_items:
            items_data.append({
                'id': item.id,
                'customer_code': item.item.customer_code,
                'item_name': item.item.customer_item_name or item.item.product.name,
                'product_name': item.item.product.name,
                'quantity': item.quantity,
                'delivered_quantity': item.delivered_quantity or 0,
                'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None
            })
        
        return jsonify(items_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/production-plans', methods=['GET'])
def get_production_plans():
    """Get all production plans"""
    try:
        db_session = get_session()
        plans = db_session.query(ProductionPlan).all()
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                'id': plan.id,
                'plan_type': plan.plan_type,
                'customer_id': plan.customer_id,
                'customer_name': plan.customer.name if plan.customer else None,
                'order_id': plan.order_id,
                'delivery_date': plan.delivery_date.isoformat() if plan.delivery_date else None,
                'order_date': plan.order_date.isoformat() if plan.order_date else None,
                'product_id': plan.product_id,
                'product_name': plan.product.name if plan.product else None,
                'surface_treatment': plan.surface_treatment
            })
        
        return jsonify({
            'success': True,
            'plans': plans_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/production-plans', methods=['POST'])
def create_production_plan():
    """Create a new production plan"""
    try:
        data = request.json
        db_session = get_session()
        
        # Parse dates
        delivery_date = None
        if data.get('delivery_date'):
            delivery_date = datetime.strptime(data['delivery_date'], '%Y-%m-%d').date()
        
        order_date = None
        if data.get('order_date'):
            order_date = datetime.strptime(data['order_date'], '%Y-%m-%d').date()
        
        # Create new production plan
        new_plan = ProductionPlan(
            plan_type=data['plan_type'],
            customer_id=data.get('customer_id'),
            order_id=data.get('order_id'),
            delivery_date=delivery_date,
            order_date=order_date,
            product_id=data.get('product_id'),
            surface_treatment=data.get('surface_treatment')
        )
        
        db_session.add(new_plan)
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Production plan created successfully',
            'plan_id': new_plan.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/employees')
@login_required
def employees_page():
    """Employee management page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Employee Management</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                padding: 20px;
                background: #f8f9fa;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            }
            .header {
                display: flex;
                align-items: center;
                gap: 20px;
                margin-bottom: 30px;
            }
            .back-btn {
                padding: 10px 20px;
                background: #6c757d;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
            }
            h1 { 
                margin: 0;
                color: #2c3e50;
            }
            .filters {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            select, input { 
                width: 100%; 
                padding: 12px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                font-size: 16px;
            }
            .employees-grid {
                display: grid;
                gap: 20px;
            }
            .employee-card {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                border-left: 4px solid #43e97b;
            }
            .employee-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            .employee-name {
                font-weight: bold;
                font-size: 1.1rem;
                color: #2c3e50;
            }
            .employee-status {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: bold;
            }
            .status-active {
                background: #28a745;
                color: white;
            }
            .status-inactive {
                background: #6c757d;
                color: white;
            }
            .employee-details {
                color: #495057;
                margin-bottom: 10px;
            }
            .loading {
                text-align: center;
                padding: 40px;
                color: #6c757d;
            }
            .add-employee-btn {
                background: #43e97b;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                margin-bottom: 20px;
            }
            .add-employee-btn:hover {
                background: #38d16a;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/" class="back-btn">← Back</a>
                <h1>👥 Employee Management</h1>
            </div>
            
            <button class="add-employee-btn" onclick="showAddEmployeeForm()">+ Add Employee</button>
            
            <div class="filters">
                <select id="status-filter">
                    <option value="">All Status</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                </select>
                <input type="text" id="search-filter" placeholder="Search by name...">
            </div>
            
            <div id="employees-container">
                <div class="loading">Loading employees...</div>
            </div>
        </div>
        
        <script>
            let allEmployees = [];
            
            async function loadEmployees() {
                try {
                    const response = await fetch('/api/employees');
                    const data = await response.json();
                    
                    if (data.success) {
                        allEmployees = data.employees;
                        displayEmployees(allEmployees);
                    }
                } catch (error) {
                    console.error('Error loading employees:', error);
                }
            }
            
            function displayEmployees(employees) {
                const container = document.getElementById('employees-container');
                
                if (employees.length === 0) {
                    container.innerHTML = '<div class="loading">No employees found</div>';
                    return;
                }
                
                container.innerHTML = employees.map(employee => `
                    <div class="employee-card">
                        <div class="employee-header">
                            <div class="employee-name">${employee.name}</div>
                            <div class="employee-status ${employee.is_active ? 'status-active' : 'status-inactive'}">
                                ${employee.is_active ? 'Active' : 'Inactive'}
                            </div>
                        </div>
                        <div class="employee-details">
                            ${employee.email ? `<div>📧 ${employee.email}</div>` : ''}
                            ${employee.phone ? `<div>📞 ${employee.phone}</div>` : ''}
                            ${employee.address ? `<div>📍 ${employee.address}</div>` : ''}
                            ${employee.birthday ? `<div>🎂 Birthday: ${new Date(employee.birthday).toLocaleDateString()}</div>` : ''}
                            ${employee.name_day ? `<div>📅 Name Day: ${employee.name_day}</div>` : ''}
                            ${employee.employment_start ? `<div>📅 Started: ${new Date(employee.employment_start).toLocaleDateString()}</div>` : ''}
                            ${employee.employment_type ? `<div>💼 Type: ${employee.employment_type}</div>` : ''}
                        </div>
                    </div>
                `).join('');
            }
            
            function showAddEmployeeForm() {
                // Simple form for adding employees
                const form = prompt('Enter employee details (JSON format):', '{"name": "John Doe", "email": "john@example.com", "phone": "+1234567890", "employment_type": "Full-time"}');
                if (form) {
                    try {
                        const employeeData = JSON.parse(form);
                        addEmployee(employeeData);
                    } catch (error) {
                        alert('Invalid JSON format');
                    }
                }
            }
            
            async function addEmployee(employeeData) {
                try {
                    const response = await fetch('/api/employees', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(employeeData)
                    });
                    
                    const data = await response.json();
                    if (data.success) {
                        alert('Employee added successfully');
                        loadEmployees();
                    } else {
                        alert('Error adding employee: ' + data.error);
                    }
                } catch (error) {
                    alert('Error adding employee: ' + error);
                }
            }
            
            // Filter functionality
            document.getElementById('status-filter').addEventListener('change', filterEmployees);
            document.getElementById('search-filter').addEventListener('input', filterEmployees);
            
            function filterEmployees() {
                const statusFilter = document.getElementById('status-filter').value;
                const searchFilter = document.getElementById('search-filter').value.toLowerCase();
                
                let filtered = allEmployees;
                
                if (statusFilter) {
                    const isActive = statusFilter === 'active';
                    filtered = filtered.filter(employee => employee.is_active === isActive);
                }
                
                if (searchFilter) {
                    filtered = filtered.filter(employee => 
                        employee.name.toLowerCase().includes(searchFilter) ||
                        (employee.email && employee.email.toLowerCase().includes(searchFilter))
                    );
                }
                
                displayEmployees(filtered);
            }
            
            // Load data on page load
            loadEmployees();
        </script>
    </body>
    </html>
    """
    return render_template_string(html, session=session, get_role_display_name=get_role_display_name)

@app.route('/users')
@admin_required
def users_page():
    """User management page (admin only)"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>User Management</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                padding: 20px;
                background: #f8f9fa;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            }
            .header {
                display: flex;
                align-items: center;
                gap: 20px;
                margin-bottom: 30px;
            }
            .back-btn {
                padding: 10px 20px;
                background: #6c757d;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
            }
            h1 { 
                margin: 0;
                color: #2c3e50;
            }
            .user-form {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
            }
            .form-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 15px;
            }
            input, select { 
                width: 100%; 
                padding: 12px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                font-size: 16px;
            }
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                margin-right: 10px;
            }
            .btn-primary {
                background: #007AFF;
                color: white;
            }
            .btn-danger {
                background: #dc3545;
                color: white;
            }
            .btn-warning {
                background: #ffc107;
                color: #212529;
            }
            .users-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            .users-table th, .users-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            .users-table th {
                background: #f8f9fa;
                font-weight: bold;
            }
            .status-active {
                color: #28a745;
                font-weight: bold;
            }
            .status-inactive {
                color: #6c757d;
                font-weight: bold;
            }
            .message {
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .message.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .message.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1>👥 User Management</h1>
            </div>
            
            <div id="message"></div>
            
            <div class="user-form">
                <h3>Add New User</h3>
                <form id="addUserForm">
                    <div class="form-row">
                        <input type="text" id="username" name="username" placeholder="Username" required>
                        <input type="email" id="email" name="email" placeholder="Email">
                        <input type="password" id="password" name="password" placeholder="Password" required>
                    </div>
                    <div class="form-row">
                        <select id="role" name="role" required>
                            <option value="">Select Role</option>
                            <option value="admin">Administrator</option>
                            <option value="manager">Manager</option>
                            <option value="user">User</option>
                            <option value="viewer">Viewer</option>
                        </select>
                        <label>
                            <input type="checkbox" id="is_active" name="is_active" checked>
                            Active
                        </label>
                    </div>
                    <button type="submit" class="btn btn-primary">Add User</button>
                </form>
            </div>
            
            <h3>Existing Users</h3>
            <table class="users-table">
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Last Login</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="usersTableBody">
                    <!-- Users will be loaded here -->
                </tbody>
            </table>
        </div>
        
        <script>
            // Load users on page load
            loadUsers();
            
            // Add user form submission
            document.getElementById('addUserForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const data = {
                    username: formData.get('username'),
                    email: formData.get('email'),
                    password: formData.get('password'),
                    role: formData.get('role'),
                    is_active: formData.get('is_active') === 'on'
                };
                
                try {
                    const response = await fetch('/api/users', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showMessage('User created successfully!', 'success');
                        this.reset();
                        loadUsers();
                    } else {
                        showMessage(result.error || 'Failed to create user', 'error');
                    }
                } catch (error) {
                    showMessage('Error creating user: ' + error.message, 'error');
                }
            });
            
            async function loadUsers() {
                try {
                    const response = await fetch('/api/users');
                    const result = await response.json();
                    
                    if (result.success) {
                        const tbody = document.getElementById('usersTableBody');
                        tbody.innerHTML = '';
                        
                        result.users.forEach(user => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${user.username}</td>
                                <td>${user.email || '-'}</td>
                                <td>${user.role_display}</td>
                                <td class="${user.is_active ? 'status-active' : 'status-inactive'}">
                                    ${user.is_active ? 'Active' : 'Inactive'}
                                </td>
                                <td>${user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</td>
                                <td>
                                    <button class="btn btn-warning" onclick="editUser(${user.id})">Edit</button>
                                    <button class="btn btn-danger" onclick="deleteUser(${user.id})">Delete</button>
                                </td>
                            `;
                            tbody.appendChild(row);
                        });
                    }
                } catch (error) {
                    showMessage('Error loading users: ' + error.message, 'error');
                }
            }
            
            async function deleteUser(userId) {
                if (!confirm('Are you sure you want to delete this user?')) {
                    return;
                }
                
                try {
                    const response = await fetch(`/api/users/${userId}`, {
                        method: 'DELETE'
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showMessage('User deleted successfully!', 'success');
                        loadUsers();
                    } else {
                        showMessage(result.error || 'Failed to delete user', 'error');
                    }
                } catch (error) {
                    showMessage('Error deleting user: ' + error.message, 'error');
                }
            }
            
            function showMessage(message, type) {
                const messageDiv = document.getElementById('message');
                messageDiv.textContent = message;
                messageDiv.className = `message ${type}`;
                
                setTimeout(() => {
                    messageDiv.textContent = '';
                    messageDiv.className = '';
                }, 5000);
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html, session=session, get_role_display_name=get_role_display_name)

@app.route('/api/employees', methods=['GET'])
def get_employees():
    """Get all employees"""
    try:
        db_session = get_session()
        employees = db_session.query(Employee).all()
        
        employees_data = []
        for employee in employees:
            employees_data.append({
                'id': employee.id,
                'name': employee.name,
                'email': employee.email,
                'phone': employee.phone,
                'address': employee.address,
                'birthday': employee.birthday.isoformat() if employee.birthday else None,
                'name_day': employee.name_day,
                'employment_start': employee.employment_start.isoformat() if employee.employment_start else None,
                'employment_end': employee.employment_end.isoformat() if employee.employment_end else None,
                'employment_type': employee.employment_type,
                'is_active': employee.is_active,
                'documents_path': employee.documents_path
            })
        
        return jsonify({
            'success': True,
            'employees': employees_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/employees', methods=['POST'])
def create_employee():
    """Create a new employee"""
    try:
        data = request.json
        db_session = get_session()
        
        # Parse dates
        birthday = None
        if data.get('birthday'):
            birthday = datetime.strptime(data['birthday'], '%Y-%m-%d').date()
        
        employment_start = None
        if data.get('employment_start'):
            employment_start = datetime.strptime(data['employment_start'], '%Y-%m-%d').date()
        
        employment_end = None
        if data.get('employment_end'):
            employment_end = datetime.strptime(data['employment_end'], '%Y-%m-%d').date()
        
        # Create new employee
        new_employee = Employee(
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            birthday=birthday,
            name_day=data.get('name_day'),
            employment_start=employment_start,
            employment_end=employment_end,
            employment_type=data.get('employment_type'),
            is_active=data.get('is_active', True)
        )
        
        db_session.add(new_employee)
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Employee created successfully',
            'employee_id': new_employee.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Include all other existing routes from mobile_api.py
# (generate_label, add_label, cart management, etc.)

@app.route('/api/news', methods=['GET'])
def get_news():
    """Get recent order activity from the last 24 hours with priority for order changes"""
    try:
        db_session = get_session()
        from datetime import datetime, timedelta
        
        # Get timestamp from 24 hours ago
        yesterday = datetime.now() - timedelta(hours=24)
        
        news_items = []
        
        # PRIORITY 1: Get recent order CREATIONS (HIGHEST PRIORITY)
        recent_orders_created = db_session.query(Order).filter(
            Order.created_at >= yesterday
        ).order_by(Order.created_at.desc()).limit(10).all()
        
        for order in recent_orders_created:
            customer_name = order.customer.name if order.customer else "Unknown Customer"
            news_items.append({
                'timestamp': order.created_at.isoformat(),
                'action': 'created',
                'title': f'🆕 New Order Created',
                'details': f'Order {order.order_number} for {customer_name}',
                'priority': 1,  # Highest priority
                'order_id': order.id,
                'order_number': order.order_number,
                'link': f'/orders?filter=order&value={order.order_number}'
            })
        
        # PRIORITY 2: Get recent order MODIFICATIONS (HIGH PRIORITY)
        recent_orders_updated = db_session.query(Order).filter(
            Order.updated_at >= yesterday,
            Order.updated_at != Order.created_at  # Only actual updates, not creation
        ).order_by(Order.updated_at.desc()).limit(10).all()
        
        for order in recent_orders_updated:
            customer_name = order.customer.name if order.customer else "Unknown Customer"
            news_items.append({
                'timestamp': order.updated_at.isoformat(),
                'action': 'updated',
                'title': f'✏️ Order Modified',
                'details': f'Order {order.order_number} for {customer_name} was updated',
                'priority': 2,  # High priority
                'order_id': order.id,
                'order_number': order.order_number,
                'link': f'/orders?filter=order&value={order.order_number}'
            })
        
        # PRIORITY 3: Get recent DELIVERIES (LOWER PRIORITY)
        recent_deliveries = db_session.query(OrderItem).filter(
            OrderItem.delivered_quantity > 0,
            OrderItem.updated_at >= yesterday
        ).order_by(OrderItem.updated_at.desc()).limit(15).all()
        
        for item in recent_deliveries:
            order = item.order
            customer_name = order.customer.name if order.customer else "Unknown Customer"
            item_name = item.item.customer_item_name if item.item else "Unknown Item"
            
            # Calculate how much was delivered in this update
            delivered_change = item.delivered_quantity
            
            news_items.append({
                'timestamp': item.updated_at.isoformat() if item.updated_at else item.created_at.isoformat(),
                'action': 'delivery',
                'title': f'📦 Delivery Updated',
                'details': f'{delivered_change} units delivered for {item_name} (Order {order.order_number})',
                'priority': 3,  # Lower priority
                'order_id': order.id,
                'order_number': order.order_number,
                'link': f'/orders?filter=order&value={order.order_number}'
            })
        
        # PRIORITY 4: Get recent DELIVERY RECORDS (LOWEST PRIORITY)
        from models.database import Delivery
        recent_delivery_records = db_session.query(Delivery).filter(
            Delivery.created_at >= yesterday
        ).order_by(Delivery.created_at.desc()).limit(10).all()
        
        for delivery in recent_delivery_records:
            order_item = delivery.order_item
            order = order_item.order
            customer_name = order.customer.name if order.customer else "Unknown Customer"
            item_name = order_item.item.customer_item_name if order_item.item else "Unknown Item"
            
            news_items.append({
                'timestamp': delivery.created_at.isoformat(),
                'action': 'delivery_record',
                'title': f'📋 Delivery Record Added',
                'details': f'{delivery.quantity} units delivered on {delivery.delivery_date.strftime("%Y-%m-%d")} for {item_name} (Order {order.order_number})',
                'priority': 4,  # Lowest priority
                'order_id': order.id,
                'order_number': order.order_number,
                'link': f'/orders?filter=order&value={order.order_number}'
            })
        
        # Sort by priority first (1=highest, 4=lowest), then by timestamp (most recent first)
        # For same priority, most recent first
        news_items.sort(key=lambda x: (x['priority'], x['timestamp']), reverse=False)
        
        # Limit to 20 most recent items
        news_items = news_items[:20]
        
        # Remove priority field from response
        for item in news_items:
            item.pop('priority', None)
        
        return jsonify(news_items)
        
    except Exception as e:
        print(f"Error in get_news: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Test route to check database status
@app.route('/api/test-db')
def test_database():
    """Test database connectivity and table status"""
    try:
        print("🔍 Testing database connection...")
        db_session = get_session()
        
        # Test basic queries
        user_count = db_session.query(User).count()
        print(f"📊 Users count: {user_count}")
        
        order_count = db_session.query(Order).count()
        print(f"📊 Orders count: {order_count}")
        
        customer_count = db_session.query(Customer).count()
        print(f"📊 Customers count: {customer_count}")
        
        # Try to get a sample customer to test the model
        sample_customer = db_session.query(Customer).first()
        if sample_customer:
            print(f"✅ Sample customer found: {sample_customer.name} (ID: {sample_customer.id})")
        else:
            print("❌ No customers found in database")
        
        return jsonify({
            'success': True,
            'database_status': 'connected',
            'table_counts': {
                'users': user_count,
                'orders': order_count,
                'customers': customer_count
            },
            'sample_customer': {
                'id': sample_customer.id,
                'name': sample_customer.name,
                'name_index': sample_customer.name_index
            } if sample_customer else None
        })
        
    except Exception as e:
        print(f"❌ Database test error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test-customers-sql')
def test_customers_sql():
    """Test customers table with raw SQL"""
    try:
        print("🔍 Testing customers table with raw SQL...")
        db_session = get_session()
        
        # Try raw SQL query
        from sqlalchemy import text
        result = db_session.execute(text("SELECT COUNT(*) FROM public.customers"))
        count = result.scalar()
        print(f"📊 Raw SQL customers count: {count}")
        
        # Try to get a sample customer with raw SQL
        result = db_session.execute(text("SELECT id, name, name_index FROM public.customers LIMIT 1"))
        sample = result.fetchone()
        
        if sample:
            print(f"✅ Raw SQL sample customer: {sample}")
            return jsonify({
                'success': True,
                'raw_sql_count': count,
                'sample_customer': {
                    'id': sample[0],
                    'name': sample[1],
                    'name_index': sample[2]
                }
            })
        else:
            print("❌ No customers found with raw SQL")
            return jsonify({
                'success': True,
                'raw_sql_count': count,
                'sample_customer': None
            })
        
    except Exception as e:
        print(f"❌ Raw SQL test error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    try:
        print("Starting enhanced web application...")
        print("Available endpoints:")
        print("  GET  /login               - Login page")
        print("  POST /login               - Login authentication")
        print("  GET  /logout              - Logout")
        print("  GET  /                    - Dashboard (requires login)")
        print("  GET  /orders              - Orders Management (requires login)")
        print("  GET  /production          - Production Planning (requires login)")
        print("  GET  /employees           - Employee Management (requires login)")
        print("  GET  /labels              - Label Generation (requires login)")
        print("  GET  /mobile              - Mobile Interface (requires login)")
        print("  GET  /users               - User Management (admin only)")
        print("  GET  /api/dashboard-metrics")
        print("  GET  /api/all-orders")
        print("  GET  /api/customers")
        print("  GET  /api/orders/<customer_id>")
        print("  GET  /api/undelivered-items/<order_id>")
        print("  GET  /api/production-plans")
        print("  POST /api/production-plans")
        print("  GET  /api/employees")
        print("  POST /api/employees")
        print("  GET  /api/users           - Get all users (admin only)")
        print("  POST /api/users           - Create user (admin only)")
        print("  PUT  /api/users/<id>      - Update user (admin only)")
        print("  DELETE /api/users/<id>    - Delete user (admin only)")
        print("  POST /api/generate-label  - Generate single label")
        print("  POST /api/add-to-cart     - Add item to label cart")
        print("  GET  /api/cart            - Get cart contents")
        print("  POST /api/cart/clear      - Clear cart")
        print("  POST /api/cart/generate-labels - Generate batch labels")
        
        # Use PORT environment variable for Render deployment
        port = int(os.environ.get('PORT', 5002))
        print(f"\nServer will be available at: http://localhost:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        raise