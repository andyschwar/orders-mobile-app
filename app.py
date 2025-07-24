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
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker
from functools import wraps

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.database import (
    Order, Customer, OrderItem, Item, Product, Delivery, DeliveryTerm,
    ProductionPlan, Employee, Component, ProductComponent, User, UserRole,
    get_database_path, init_db
)
from utils.label_generator import LabelGenerator
from utils.auth import authenticate_user, hash_password, verify_password, get_role_display_name

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
CORS(app)

# Initialize database connection
engine = init_db()
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

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
    """Enhanced Dashboard - Home screen"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Orders Management System</title>
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                margin: 0; 
                padding: 0;
                background: #f8f9fa;
                color: #333;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .header h1 {
                margin: 0;
                font-size: 2rem;
                font-weight: 300;
            }
            .user-info {
                position: absolute;
                top: 20px;
                right: 20px;
                color: white;
                font-size: 0.9rem;
            }
            .logout-btn {
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
                margin-left: 10px;
            }
            .logout-btn:hover {
                background: rgba(255,255,255,0.3);
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.07);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            }
            .card h3 {
                margin: 0 0 15px 0;
                color: #2c3e50;
                font-size: 1.2rem;
                font-weight: 600;
            }
            .metric {
                font-size: 2.5rem;
                font-weight: 700;
                color: #667eea;
                margin: 10px 0;
            }
            .metric-label {
                color: #6c757d;
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .nav-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-top: 30px;
            }
            .nav-item {
                background: white;
                border-radius: 12px;
                padding: 25px;
                text-decoration: none;
                color: #333;
                display: flex;
                align-items: center;
                gap: 15px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                transition: all 0.2s;
                border: 2px solid transparent;
            }
            .nav-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                border-color: #667eea;
                text-decoration: none;
                color: #333;
            }
            .nav-icon {
                width: 50px;
                height: 50px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                color: white;
                font-weight: bold;
            }
            .nav-text h4 {
                margin: 0 0 5px 0;
                font-size: 1.1rem;
                font-weight: 600;
            }
            .nav-text p {
                margin: 0;
                color: #6c757d;
                font-size: 0.9rem;
            }
            .orders-icon { background: linear-gradient(135deg, #667eea, #764ba2); }
            .labels-icon { background: linear-gradient(135deg, #f093fb, #f5576c); }
            .production-icon { background: linear-gradient(135deg, #4facfe, #00f2fe); }
            .employees-icon { background: linear-gradient(135deg, #43e97b, #38f9d7); }
            .components-icon { background: linear-gradient(135deg, #fa709a, #fee140); }
            .reports-icon { background: linear-gradient(135deg, #a8edea, #fed6e3); }
            .mobile-icon { background: linear-gradient(135deg, #ffecd2, #fcb69f); }
            
            .status-indicator {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-active { background: #28a745; }
            .status-pending { background: #ffc107; }
            .status-complete { background: #6c757d; }
            
            @media (max-width: 768px) {
                .container { padding: 15px; }
                .dashboard-grid { grid-template-columns: 1fr; }
                .nav-grid { grid-template-columns: 1fr; }
                .header h1 { font-size: 1.5rem; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Orders Management Dashboard</h1>
            <p>Comprehensive web interface for managing orders, production, and employees</p>
            <div class="user-info">
                Logged in as: {{ session['username'] }} ({{ get_role_display_name(session['role']) }})
                <a href="/logout" class="logout-btn">Logout</a>
            </div>
        </div>
        
        <div class="container">
            <div class="dashboard-grid">
                <div class="card">
                    <h3>📈 Key Metrics</h3>
                    <div class="metric" id="total-orders">-</div>
                    <div class="metric-label">Total Orders</div>
                </div>
                <div class="card">
                    <h3>👥 Active Customers</h3>
                    <div class="metric" id="active-customers">-</div>
                    <div class="metric-label">This Month</div>
                </div>
                <div class="card">
                    <h3>📦 Pending Deliveries</h3>
                    <div class="metric" id="pending-deliveries">-</div>
                    <div class="metric-label">This Week</div>
                </div>
                <div class="card">
                    <h3>👨‍💼 Active Employees</h3>
                    <div class="metric" id="active-employees">-</div>
                    <div class="metric-label">Currently Employed</div>
                </div>
            </div>
            
            <div class="nav-grid">
                <a href="/orders" class="nav-item">
                    <div class="nav-icon orders-icon">📋</div>
                    <div class="nav-text">
                        <h4>Orders Management</h4>
                        <p>View and manage customer orders</p>
                    </div>
                </a>
                
                <a href="/labels" class="nav-item">
                    <div class="nav-icon labels-icon">🏷️</div>
                    <div class="nav-text">
                        <h4>Label Generation</h4>
                        <p>Create and print product labels</p>
                    </div>
                </a>
                
                <a href="/production" class="nav-item">
                    <div class="nav-icon production-icon">🏭</div>
                    <div class="nav-text">
                        <h4>Production Planning</h4>
                        <p>Manage production schedules</p>
                    </div>
                </a>
                
                <a href="/employees" class="nav-item">
                    <div class="nav-icon employees-icon">👥</div>
                    <div class="nav-text">
                        <h4>Employee Management</h4>
                        <p>Manage employee records and contracts</p>
                    </div>
                </a>
                
                <a href="/components" class="nav-item">
                    <div class="nav-icon components-icon">🔧</div>
                    <div class="nav-text">
                        <h4>Components & Products</h4>
                        <p>Manage BOM and product components</p>
                    </div>
                </a>
                
                <a href="/reports" class="nav-item">
                    <div class="nav-icon reports-icon">📊</div>
                    <div class="nav-text">
                        <h4>Reports & Analytics</h4>
                        <p>Generate reports and view analytics</p>
                    </div>
                </a>
                
                <a href="/mobile" class="nav-item">
                    <div class="nav-icon mobile-icon">📱</div>
                    <div class="nav-text">
                        <h4>Mobile Interface</h4>
                        <p>Access mobile-optimized interface</p>
                    </div>
                </a>
                
                {% if session['role'] == 'admin' %}
                <a href="/users" class="nav-item">
                    <div class="nav-icon" style="background: linear-gradient(135deg, #ff6b6b, #ee5a24);">👥</div>
                    <div class="nav-text">
                        <h4>User Management</h4>
                        <p>Manage system users and permissions</p>
                    </div>
                </a>
                {% endif %}
            </div>
        </div>
        
        <script>
            // Load dashboard metrics
            async function loadMetrics() {
                try {
                    const response = await fetch('/api/dashboard-metrics');
                    const data = await response.json();
                    
                    if (data.success) {
                        document.getElementById('total-orders').textContent = data.metrics.total_orders;
                        document.getElementById('active-customers').textContent = data.metrics.active_customers;
                        document.getElementById('pending-deliveries').textContent = data.metrics.pending_deliveries;
                        document.getElementById('active-employees').textContent = data.metrics.active_employees;
                    }
                } catch (error) {
                    console.error('Error loading metrics:', error);
                }
            }
            
            // Load metrics on page load
            loadMetrics();
        </script>
    </body>
    </html>
    """
    return render_template_string(html, session=session, get_role_display_name=get_role_display_name)

@app.route('/api/dashboard-metrics')
def dashboard_metrics():
    """Get dashboard metrics"""
    try:
        session = get_session()
        
        # Total orders
        total_orders = session.query(Order).count()
        
        # Active customers this month
        this_month = datetime.now().replace(day=1)
        active_customers = session.query(Order.customer_id).filter(
            Order.order_date >= this_month
        ).distinct().count()
        
        # Pending deliveries this week
        this_week = datetime.now().date() - timedelta(days=7)
        pending_deliveries = session.query(OrderItem).filter(
            and_(
                OrderItem.delivery_date >= this_week,
                OrderItem.delivered_quantity < OrderItem.quantity
            )
        ).count()
        
        # Active employees
        active_employees = session.query(Employee).filter(
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
        return jsonify({'error': str(e)}), 500

@app.route('/orders')
@login_required
def orders_page():
    """Orders management page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Orders Management</title>
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
            .orders-grid {
                display: grid;
                gap: 15px;
            }
            .order-card {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                border-left: 4px solid #667eea;
            }
            .order-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            .order-number {
                font-weight: bold;
                font-size: 1.1rem;
                color: #2c3e50;
            }
            .order-date {
                color: #6c757d;
                font-size: 0.9rem;
            }
            .customer-name {
                font-weight: 600;
                color: #495057;
                margin-bottom: 10px;
            }
            .items-list {
                margin-top: 15px;
            }
            .item-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #e9ecef;
            }
            .item-row:last-child {
                border-bottom: none;
            }
            .loading {
                text-align: center;
                padding: 40px;
                color: #6c757d;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/" class="back-btn">← Back</a>
                <h1>📋 Orders Management</h1>
            </div>
            
            <div class="filters">
                <select id="customer-filter">
                    <option value="">All Customers</option>
                </select>
                <input type="date" id="date-filter" placeholder="Filter by date">
                <select id="status-filter">
                    <option value="">All Status</option>
                    <option value="pending">Pending</option>
                    <option value="partial">Partially Delivered</option>
                    <option value="complete">Complete</option>
                </select>
            </div>
            
            <div id="orders-container">
                <div class="loading">Loading orders...</div>
            </div>
        </div>
        
        <script>
            let allOrders = [];
            
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
            
            async function loadOrders() {
                try {
                    const response = await fetch('/api/all-orders');
                    const data = await response.json();
                    
                    if (data.success) {
                        allOrders = data.orders;
                        displayOrders(allOrders);
                    }
                } catch (error) {
                    console.error('Error loading orders:', error);
                }
            }
            
            function displayOrders(orders) {
                const container = document.getElementById('orders-container');
                
                if (orders.length === 0) {
                    container.innerHTML = '<div class="loading">No orders found</div>';
                    return;
                }
                
                container.innerHTML = orders.map(order => `
                    <div class="order-card">
                        <div class="order-header">
                            <div>
                                <div class="order-number">${order.order_number}</div>
                                <div class="order-date">${new Date(order.order_date).toLocaleDateString()}</div>
                            </div>
                            <div class="order-status">${getStatusBadge(order.status)}</div>
                        </div>
                        <div class="customer-name">${order.customer_name}</div>
                        <div class="items-list">
                            ${order.items.map(item => `
                                <div class="item-row">
                                    <div>
                                        <strong>${item.product_name}</strong>
                                        <br><small>${item.customer_code}</small>
                                    </div>
                                    <div>
                                        ${item.delivered_quantity}/${item.quantity} delivered
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('');
            }
            
            function getStatusBadge(status) {
                const badges = {
                    'pending': '<span style="background: #ffc107; color: #000; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">Pending</span>',
                    'partial': '<span style="background: #17a2b8; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">Partial</span>',
                    'complete': '<span style="background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">Complete</span>'
                };
                return badges[status] || badges['pending'];
            }
            
            // Filter functionality
            document.getElementById('customer-filter').addEventListener('change', filterOrders);
            document.getElementById('date-filter').addEventListener('change', filterOrders);
            document.getElementById('status-filter').addEventListener('change', filterOrders);
            
            function filterOrders() {
                const customerId = document.getElementById('customer-filter').value;
                const dateFilter = document.getElementById('date-filter').value;
                const statusFilter = document.getElementById('status-filter').value;
                
                let filtered = allOrders;
                
                if (customerId) {
                    filtered = filtered.filter(order => order.customer_id == customerId);
                }
                
                if (dateFilter) {
                    filtered = filtered.filter(order => order.order_date.startsWith(dateFilter));
                }
                
                if (statusFilter) {
                    filtered = filtered.filter(order => order.status === statusFilter);
                }
                
                displayOrders(filtered);
            }
            
            // Load data on page load
            loadCustomers();
            loadOrders();
        </script>
    </body>
    </html>
    """
    return render_template_string(html, session=session, get_role_display_name=get_role_display_name)

@app.route('/api/all-orders')
def get_all_orders():
    """Get all orders with items"""
    try:
        session = get_session()
        
        orders = session.query(Order).all()
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
    # This would be the existing labels page from mobile_api.py
    # For now, redirect to mobile interface
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Label Generation</title>
        <style>
            body { font-family: -apple-system, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; }
            .back-btn { display: inline-block; padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 8px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Dashboard</a>
            <h1>🏷️ Label Generation</h1>
            <p>This feature is available in the mobile interface.</p>
            <a href="/mobile" style="background: #007AFF; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 20px;">Go to Mobile Interface</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, session=session, get_role_display_name=get_role_display_name)

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
        session = get_session()
        
        # Get order item
        order_item = session.query(OrderItem).filter(OrderItem.id == data['order_item_id']).first()
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
        session = get_session()
        
        # Get order item
        order_item = session.query(OrderItem).filter(OrderItem.id == data['order_item_id']).first()
        if not order_item:
            return jsonify({'error': 'Order item not found'}), 404
        
        # Create fake order item for cart
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
        
        # Add to cart
        label_cart.append(fake_order_item)
        
        return jsonify({
            'success': True,
            'message': 'Added to cart',
            'cart_count': len(label_cart)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    """Get current cart contents"""
    try:
        cart_items = []
        for item in label_cart:
            cart_items.append({
                'order_number': item.order.order_number,
                'customer_name': item.order.customer.name,
                'customer_code': item.item.customer_code,
                'product_name': item.item.product.name,
                'quantity': item.quantity,
                'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None
            })
        
        return jsonify({
            'success': True,
            'cart': cart_items,
            'count': len(label_cart)
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

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Get all customers"""
    try:
        session = get_session()
        customers = session.query(Customer).order_by(Customer.name_index).all()
        
        customers_data = []
        for customer in customers:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'name_index': customer.name_index,
                'city': customer.city,
                'country': customer.country
            })
        
        return jsonify({
            'success': True,
            'customers': customers_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:customer_id>', methods=['GET'])
def get_orders(customer_id):
    """Get orders for a specific customer"""
    try:
        session = get_session()
        orders = session.query(Order).filter(Order.customer_id == customer_id).all()
        
        orders_data = []
        for order in orders:
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'order_date': order.order_date.isoformat(),
                'customer_name': order.customer.name
            })
        
        return jsonify({
            'success': True,
            'orders': orders_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/undelivered-items/<int:order_id>', methods=['GET'])
def get_undelivered_items(order_id):
    """Get undelivered items for an order"""
    try:
        session = get_session()
        order_items = session.query(OrderItem).filter(
            and_(
                OrderItem.order_id == order_id,
                OrderItem.delivered_quantity < OrderItem.quantity
            )
        ).all()
        
        items_data = []
        for item in order_items:
            remaining = item.quantity - (item.delivered_quantity or 0)
            items_data.append({
                'id': item.id,
                'customer_code': item.item.customer_code,
                'customer_item_name': item.item.customer_item_name,
                'product_name': item.item.product.name,
                'quantity': item.quantity,
                'delivered_quantity': item.delivered_quantity or 0,
                'remaining': remaining,
                'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None
            })
        
        return jsonify({
            'success': True,
            'items': items_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/order-items/<int:order_id>', methods=['GET'])
def get_order_items(order_id):
    """Get all items for an order"""
    try:
        session = get_session()
        order_items = session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        
        items_data = []
        for item in order_items:
            items_data.append({
                'id': item.id,
                'customer_code': item.item.customer_code,
                'customer_item_name': item.item.customer_item_name,
                'product_name': item.item.product.name,
                'quantity': item.quantity,
                'delivered_quantity': item.delivered_quantity or 0,
                'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None
            })
        
        return jsonify({
            'success': True,
            'items': items_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/production-plans', methods=['GET'])
def get_production_plans():
    """Get all production plans"""
    try:
        session = get_session()
        plans = session.query(ProductionPlan).all()
        
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
        session = get_session()
        
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
        
        session.add(new_plan)
        session.commit()
        
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
        session = get_session()
        employees = session.query(Employee).all()
        
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
        session = get_session()
        
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
        
        session.add(new_employee)
        session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Employee created successfully',
            'employee_id': new_employee.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Include all other existing routes from mobile_api.py
# (generate_label, add_label, cart management, etc.)

if __name__ == '__main__':
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