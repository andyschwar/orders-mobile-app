from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, DateTime, Boolean, Enum, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os
import logging
import json
import enum
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

Base = declarative_base()

# Global engine and session factory
_engine = None
_Session = None

def get_session_factory():
    """Get or create session factory with retry logic"""
    global _engine, _Session
    
    if _Session is None:
        _engine = init_db()
        _Session = sessionmaker(bind=_engine)
    
    return _Session

@contextmanager
def get_session_with_retry(max_retries=3, retry_delay=1):
    """Get database session with retry logic for connection drops"""
    Session = get_session_factory()
    session = None
    
    for attempt in range(max_retries):
        try:
            session = Session()
            yield session
            session.commit()
            break
        except Exception as e:
            if session:
                try:
                    session.rollback()
                except Exception as rollback_error:
                    # Ignore rollback errors during shutdown
                    pass
            
            if "server closed the connection" in str(e) or "connection" in str(e).lower():
                logger.warning(f"Database connection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    # Recreate engine and session factory
                    global _engine, _Session
                    _engine = None
                    _Session = None
                    continue
                else:
                    logger.error(f"Max retries reached for database connection: {e}")
                    raise
            else:
                # Non-connection error, don't retry
                raise
        finally:
            if session:
                try:
                    session.close()
                except Exception as close_error:
                    # Ignore close errors during shutdown
                    pass

def execute_with_retry(func, *args, **kwargs):
    """Execute a function with database retry logic"""
    with get_session_with_retry() as session:
        return func(session, *args, **kwargs)

def cleanup_database_connections():
    """Clean up database connections gracefully"""
    global _engine, _Session
    
    try:
        if _engine:
            _engine.dispose()
            _engine = None
            _Session = None
    except Exception as e:
        pass

class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name_index = Column(String(20))  # Index for sorting/reference
    name = Column(String(100), nullable=False)
    street = Column(String(100))
    city = Column(String(100))
    country = Column(String(100))
    email1 = Column(String(100))
    email2 = Column(String(100))
    email3 = Column(String(100))
    atest_email = Column(String(100))
    invoice_email = Column(String(100))
    ico_vat = Column(String(20))  # VAT identification number
    ic_dph = Column(String(20))   # Tax identification number
    currency = Column(String(3))   # e.g., EUR, USD
    is_eu = Column(Boolean, default=False)  # 1 for EU, 0 for non-EU
    delivery_address = Column(Text)
    
    # Barcode settings
    barcodes_enabled = Column(Boolean, default=False)  # Whether barcodes are enabled for this customer
    order_barcode_prefix = Column(String(10), default='N')  # Prefix for order number barcodes
    item_barcode_prefix = Column(String(10), default='P')   # Prefix for item code barcodes
    quantity_barcode_prefix = Column(String(10), default='U')  # Prefix for quantity barcodes
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    items = relationship("Item", back_populates="customer")
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    weight_per_unit = Column(Float)  # Weight in kg
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    items = relationship("Item", back_populates="product")
    components = relationship("ProductComponent", back_populates="product")
    
    def calculate_total_cost(self, quantity=1):
        """Calculate total cost of all components for this product"""
        total_cost = 0.0
        for component_rel in self.components:
            component = component_rel.component
            component_cost = component.unit_cost * component_rel.quantity * quantity
            total_cost += component_cost
        return total_cost
    
    def calculate_profit_margin(self, selling_price, quantity=1):
        """Calculate profit margin percentage"""
        total_cost = self.calculate_total_cost(quantity)
        if selling_price <= 0:
            return 0.0
        profit = selling_price - total_cost
        return (profit / selling_price) * 100
    
    def calculate_profit_amount(self, selling_price, quantity=1):
        """Calculate absolute profit amount"""
        total_cost = self.calculate_total_cost(quantity)
        return selling_price - total_cost

class Item(Base):
    __tablename__ = 'items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    customer_code = Column(String(50), nullable=False)
    customer_item_name = Column(String(100))
    item_type = Column(String(50))
    similar_item = Column(String(100))  # Reference to another product name for weight lookup
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    customer = relationship("Customer", back_populates="items")
    product = relationship("Product", back_populates="items")
    order_items = relationship("OrderItem", back_populates="item")

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    order_number = Column(String(50), nullable=False, unique=True)
    order_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    item_id = Column(Integer, ForeignKey('items.id'))
    quantity = Column(Integer, nullable=False)
    price = Column(Float)
    delivery_date = Column(Date, nullable=False)
    delivered_quantity = Column(Integer, default=0)
    last_delivery_date = Column(Date)
    surface_treatment = Column(String(20))  # New column
    notes = Column(Text)  # Notes field for each order item
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    order = relationship("Order", back_populates="items")
    item = relationship("Item", back_populates="order_items")
    deliveries = relationship("Delivery", back_populates="order_item", cascade="all, delete-orphan")
    delivery_terms = relationship("DeliveryTerm", back_populates="order_item", cascade="all, delete-orphan")
    label_logs = relationship("LabelLog", back_populates="order_item", cascade="all, delete-orphan")
    
    def calculate_surface_treatment(self):
        """Calculate surface treatment based on item name and customer index"""
        if not self.item or not self.item.customer:
            return "KATAFOREZA"  # Default value
            
        # List of customer indices that use FOSFAT
        fosfat_customers = [
            "ARAD", "DROBETA", "CARACAL", "POPRAD", 
            "TREBIŠOV", "TLMAČE", "DAKO"
        ]
        
        customer_name = self.item.customer.name_index
        item_name = self.item.customer_item_name or ""
        
        # Check if item name contains 'kataf' (highest priority)
        if item_name and "kataf" in item_name.lower():
            return "KATAFOREZA"
            
        # Check if item name contains 'zinek' or 'zn' (second priority)
        if item_name and ("zinek" in item_name.lower() or "zn" in item_name.lower()):
            return "ZINEK"
            
        # Check if customer index is in fosfat list (only if no KATAF or Zn/zinek in item name)
        if customer_name in fosfat_customers:
            return "FOSFAT"
            
        # Default case
        return "KATAFOREZA"
    
    def before_insert(self):
        """Calculate surface treatment before inserting"""
        if not self.surface_treatment:
            self.surface_treatment = self.calculate_surface_treatment()

# SQLAlchemy event listeners for OrderItem
@event.listens_for(OrderItem, 'before_insert')
def before_insert_order_item(mapper, connection, target):
    """Automatically calculate surface treatment before inserting OrderItem"""
    target.before_insert()

@event.listens_for(OrderItem, 'before_update')
def before_update_order_item(mapper, connection, target):
    """Recalculate surface treatment before updating OrderItem if item_id changed"""
    # Check if the item_id has changed
    state = target._sa_instance_state
    if state.has_identity and state.attrs.item_id.history.has_changes():
        # Get the original values
        original_item_id = state.attrs.item_id.history.deleted[0] if state.attrs.item_id.history.deleted else None
        if original_item_id != target.item_id:
            # Only recalculate if item_id actually changed (not for price, quantity, etc.)
            target.surface_treatment = target.calculate_surface_treatment()

class DeliveryTerm(Base):
    """Represents a planned delivery term for an order item"""
    __tablename__ = 'delivery_terms'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_item_id = Column(Integer, ForeignKey('order_items.id'))
    term_name = Column(String(50), nullable=False)  # e.g., "May", "June", "July"
    planned_quantity = Column(Integer, nullable=False)
    planned_date = Column(Date, nullable=False)  # Planned delivery date
    delivered_quantity = Column(Integer, default=0)  # How much has been delivered for this term
    is_complete = Column(Boolean, default=False)  # Whether this term is fully delivered
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    order_item = relationship("OrderItem", back_populates="delivery_terms")
    deliveries = relationship("Delivery", back_populates="delivery_term")

class Delivery(Base):
    __tablename__ = 'deliveries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_item_id = Column(Integer, ForeignKey('order_items.id'))
    delivery_term_id = Column(Integer, ForeignKey('delivery_terms.id'), nullable=True)  # Which term this delivery fulfills
    quantity = Column(Integer, nullable=False)
    delivery_date = Column(Date, nullable=False)  # Actual delivery date
    notes = Column(Text)  # Optional notes about the delivery
    created_at = Column(DateTime, default=datetime.now)
    
    order_item = relationship("OrderItem", back_populates="deliveries")
    delivery_term = relationship("DeliveryTerm", back_populates="deliveries")

class ProductionPlan(Base):
    __tablename__ = 'production_plans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_type = Column(String(50), nullable=False)  # 'type1', 'type2', 'type3'
    customer_id = Column(Integer, ForeignKey('customers.id'))
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    delivery_date = Column(Date, nullable=True)
    order_date = Column(Date, nullable=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    surface_treatment = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    customer = relationship("Customer")
    order = relationship("Order")
    product = relationship("Product")

class Employee(Base):
    __tablename__ = 'employees'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(100))
    birthday = Column(Date)
    name_day = Column(String(5))  # Store as MM-DD string
    documents_path = Column(String(500))  # Path to employee documents on NAS
    employment_start = Column(Date)  # Start date of employment
    employment_end = Column(Date)  # End date of employment (null for indefinite)
    employment_type = Column(String(50))  # Type of employment (e.g., "Fixed-term", "Indefinite", "Part-time", "Full-time")
    contract_renewal_1 = Column(Date)  # First contract renewal date (after 1 year)
    contract_renewal_2 = Column(Date)  # Second contract renewal date (after 2 years)
    contract_renewal_3 = Column(Date)  # Third contract renewal date (after 3 years - becomes indefinite)
    last_contract_renewal = Column(Date)  # Most recent contract renewal date
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.name}')>"

class Component(Base):
    __tablename__ = 'components'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    category = Column(String(50))  # Component category
    
    # Detailed price breakdown
    buy_price = Column(Float, default=0.0)  # Purchase price
    material_price = Column(Float, default=0.0)  # Material cost
    manufacturing_price = Column(Float, default=0.0)  # Manufacturing cost
    surface_treatment_price = Column(Float, default=0.0)  # Surface treatment cost
    
    # Legacy field for backward compatibility
    unit_cost = Column(Float, default=0.0)  # Total cost per unit (calculated)
    cost_currency = Column(String(3), default='CZK')  # Currency for cost (now defaults to CZK)
    supplier = Column(String(100))  # Supplier name
    component_type = Column(String(20), default='bought')  # manufactured, bought, outsourced
    
    # EUR conversion fields
    buy_price_eur = Column(Float, default=0.0)  # Buy price in EUR
    material_price_eur = Column(Float, default=0.0)  # Material price in EUR
    manufacturing_price_eur = Column(Float, default=0.0)  # Manufacturing price in EUR
    surface_treatment_price_eur = Column(Float, default=0.0)  # Surface treatment price in EUR
    unit_cost_eur = Column(Float, default=0.0)  # Total cost in EUR
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    product_components = relationship("ProductComponent", back_populates="component")
    stock = relationship("ComponentStock", back_populates="component", uselist=False)
    materials = relationship("ComponentMaterial", back_populates="component")
    
    def calculate_total_unit_cost(self):
        """Calculate total unit cost as sum of all price components"""
        return (self.buy_price or 0.0) + (self.material_price or 0.0) + \
               (self.manufacturing_price or 0.0) + (self.surface_treatment_price or 0.0)
    
    def update_unit_cost(self):
        """Update the unit_cost field with calculated total"""
        self.unit_cost = self.calculate_total_unit_cost()
        self.update_eur_conversion()
    
    def update_eur_conversion(self, exchange_rate=0.041):  # Default CZK to EUR rate (1 EUR = ~24.4 CZK)
        """Update EUR conversion fields based on current CZK prices"""
        self.buy_price_eur = self.buy_price * exchange_rate
        self.material_price_eur = self.material_price * exchange_rate
        self.manufacturing_price_eur = self.manufacturing_price * exchange_rate
        self.surface_treatment_price_eur = self.surface_treatment_price * exchange_rate
        self.unit_cost_eur = self.unit_cost * exchange_rate
    
    def get_total_cost_for_product(self, product_id, quantity=1):
        """Calculate total cost for this component in a specific product"""
        from sqlalchemy.orm import Session
        session = Session.object_session(self)
        if session:
            product_component = session.query(ProductComponent).filter(
                ProductComponent.product_id == product_id,
                ProductComponent.component_id == self.id
            ).first()
            if product_component:
                return self.unit_cost * product_component.quantity * quantity
        return 0.0

class ProductComponent(Base):
    __tablename__ = 'product_components'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    component_id = Column(Integer, ForeignKey('components.id'))
    quantity = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    product = relationship("Product", back_populates="components")
    component = relationship("Component", back_populates="product_components")

class UserRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role.value}')>"
    
    @property
    def permissions(self):
        """Return list of permissions based on role"""
        if self.role == UserRole.ADMIN:
            return [
                'view_orders', 'create_orders', 'edit_orders', 'delete_orders',
                'view_customers', 'create_customers', 'edit_customers', 'delete_customers',
                'view_employees', 'create_employees', 'edit_employees', 'delete_employees',
                'view_products', 'create_products', 'edit_products', 'delete_products',
                'view_items', 'create_items', 'edit_items', 'delete_items',
                'view_labels', 'create_labels', 'print_labels',
                'view_import', 'import_data',
                'view_settings', 'edit_settings',
                'manage_users', 'view_reports'
            ]
        elif self.role == UserRole.MANAGER:
            return [
                'view_orders', 'create_orders', 'edit_orders', 'delete_orders',
                'view_customers', 'create_customers', 'edit_customers', 'delete_customers',
                'view_employees', 'create_employees', 'edit_employees', 'delete_employees',
                'view_products', 'create_products', 'edit_products', 'delete_products',
                'view_items', 'create_items', 'edit_items', 'delete_items',
                'view_labels', 'create_labels', 'print_labels',
                'view_import', 'import_data',
                'view_settings'
            ]
        elif self.role == UserRole.USER:
            return [
                'view_orders', 'create_orders', 'edit_orders',
                'view_customers', 'create_customers', 'edit_customers',
                'view_employees', 'view_products', 'view_items',
                'view_labels', 'create_labels', 'print_labels',
                'view_import'
            ]
        else:  # VIEWER
            return [
                'view_orders', 'view_customers', 'view_employees', 
                'view_products', 'view_items', 'view_labels'
            ]
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        from src.utils.permissions import get_permissions_manager
        pm = get_permissions_manager()
        
        # Check if it's a module.permission format
        if '.' in permission:
            module, perm = permission.split('.', 1)
            return pm.has_permission(self, module, perm)
        else:
            # For backward compatibility, check users module
            return pm.has_permission(self, 'users', permission)
    
    def can_access_tab(self, tab_name):
        """Check if user can access specific tab"""
        from utils.permissions import get_permissions_manager
        pm = get_permissions_manager()
        return pm.can_access_tab(self, tab_name)

class Material(Base):
    """Materials used in manufacturing"""
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    unit_of_measure = Column(String(20), default='kg')  # kg, m, pcs, etc.
    cost_per_unit = Column(Float, default=0.0)
    currency = Column(String(3), default='EUR')
    supplier = Column(String(100))
    supplier_code = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Additional columns that exist in the actual database
    material_type = Column(String(50))
    shape = Column(String(50))
    size = Column(String(50))
    length = Column(Float)
    price_per_kg = Column(Float)
    weight_per_meter = Column(Float)
    notes = Column(Text)
    
    # Relationships
    component_materials = relationship("ComponentMaterial", back_populates="material")
    
    def __repr__(self):
        return f"<Material(name={self.name}, unit={self.unit_of_measure})>"
    
    def calculate_price_per_meter(self):
        """Calculate price per meter based on material properties"""
        # This method should calculate price per meter based on the material's properties
        # For now, return a default calculation or use existing fields
        if hasattr(self, 'price_per_kg') and hasattr(self, 'weight_per_meter'):
            # If we have price per kg and weight per meter, calculate price per meter
            if self.price_per_kg and self.weight_per_meter:
                return self.price_per_kg * self.weight_per_meter
        elif hasattr(self, 'cost_per_unit'):
            # Use the cost_per_unit field as fallback
            return self.cost_per_unit or 0.0
        else:
            # Default fallback
            return 0.0

class ComponentMaterial(Base):
    """Many-to-many relationship between components and materials"""
    __tablename__ = 'component_materials'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    component_id = Column(Integer, ForeignKey('components.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    quantity_required = Column(Float, nullable=False, default=1.0)
    unit_of_measure = Column(String(20), default='kg')
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    component = relationship("Component", back_populates="materials")
    material = relationship("Material", back_populates="component_materials")
    
    def __repr__(self):
        return f"<ComponentMaterial(component_id={self.component_id}, material_id={self.material_id}, quantity={self.quantity_required})>"

class ComponentStock(Base):
    """Track stock levels for components"""
    __tablename__ = 'component_stock'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    component_id = Column(Integer, ForeignKey('components.id'), nullable=False)
    current_stock = Column(Float, default=0.0)  # Current stock level
    minimum_stock = Column(Float, default=0.0)  # Minimum stock level (reorder point)
    unit_of_measure = Column(String(20), default='pcs')  # pcs, kg, m, etc.
    last_updated = Column(DateTime, default=datetime.now)
    notes = Column(Text)  # Additional notes about stock
    
    component = relationship("Component", back_populates="stock")
    
    def __repr__(self):
        return f"<ComponentStock(component_id={self.component_id}, current_stock={self.current_stock})>"

class LabelLog(Base):
    """Track printed labels for audit and reporting"""
    __tablename__ = 'label_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_item_id = Column(Integer, ForeignKey('order_items.id'), nullable=True)
    customer_name = Column(String(200), nullable=False)
    customer_name_index = Column(String(50), nullable=False)
    order_number = Column(String(100), nullable=False)
    item_code = Column(String(100), nullable=False)
    item_name = Column(String(300), nullable=False)
    quantity = Column(Integer, nullable=False)
    printed_quantity = Column(Integer, nullable=False)  # How many labels were printed
    delivery_date = Column(Date, nullable=True)  # Delivery date used for the label
    barcodes_included = Column(Boolean, default=False)
    item_barcode = Column(String(200))  # The actual barcode data
    order_barcode = Column(String(200))
    quantity_barcode = Column(String(200))
    printed_by = Column(String(100))  # User who printed the labels
    printed_at = Column(DateTime, default=datetime.now)
    pdf_filename = Column(String(500))  # Path to the generated PDF
    notes = Column(Text)  # Additional notes about the print job
    
    # Relationships
    order_item = relationship("OrderItem", back_populates="label_logs")
    
    def __repr__(self):
        return f"<LabelLog(order_item_id={self.order_item_id}, customer={self.customer_name_index}, quantity={self.quantity}, printed_at={self.printed_at})>"

def get_database_path():
    """Get database path from config or use default"""
    # Check for environment variable first (for cloud deployments)
    env_db_path = os.environ.get('DATABASE_PATH')
    if env_db_path:
        return env_db_path
    
    config_file = os.path.expanduser('~/Library/Application Support/Orders/config.json')
    
    # Try to read config file
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if 'database_path' in config:
                    return config['database_path']
        except Exception as e:
            logger.warning(f"Could not read config file: {e}")
    
    # Default to local database
    db_dir = os.path.expanduser('~/Library/Application Support/Orders')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'orders.db')

def set_database_path(path):
    """Set the database path in config"""
    config_dir = os.path.expanduser('~/Library/Application Support/Orders')
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, 'config.json')
    
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except Exception:
            pass
    
    config['database_path'] = path
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Database path set to: {path}")
    except Exception as e:
        logger.error(f"Could not save config: {e}")

def init_db():
    """Initialize the database"""
    try:
        # Check if Supabase URL is set
        supabase_url = os.environ.get('SUPABASE_URL')
        
        if supabase_url:
            # Use Supabase PostgreSQL with optimized settings
            
            # Add connection pooling and optimization parameters
            engine = create_engine(
                supabase_url,
                pool_size=5,  # Connection pool size
                max_overflow=10,  # Additional connections when pool is full
                pool_pre_ping=True,  # Test connections before use
                pool_recycle=1800,  # Recycle connections every 30 minutes (reduced from 1 hour)
                pool_timeout=30,  # Timeout for getting connection from pool
                connect_args={
                    "connect_timeout": 10,  # 10 second connection timeout
                    "application_name": "orders_desktop_app",  # Identify the app
                    "keepalives_idle": 60,  # Send keepalive after 60 seconds of inactivity
                    "keepalives_interval": 10,  # Send keepalive every 10 seconds
                    "keepalives_count": 5,  # Allow 5 missed keepalives before closing
                    "options": "-c statement_timeout=300000"  # 5 minute statement timeout
                }
            )
            
            Base.metadata.create_all(engine)
            
            return engine
        else:
            # Use local SQLite as fallback
            db_path = get_database_path()
            
            # Ensure directory exists (only if it's not a simple filename)
            db_dir = os.path.dirname(db_path)
            if db_dir and not db_path.startswith('/tmp/'):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except Exception as e:
                    logger.warning(f"Could not create directory {db_dir}: {e}")
                    # Fallback to /tmp if we can't create the directory
                    db_path = '/tmp/orders.db'
            
            engine = create_engine(f'sqlite:///{db_path}')
            
            Base.metadata.create_all(engine)
            
            return engine
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise 