from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Text, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class DeliveryTerm(Base):
    """Represents a planned delivery term for an order item"""
    __tablename__ = 'delivery_terms'
    
    id = Column(Integer, primary_key=True)
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
    """Modified delivery table to include delivery term reference"""
    __tablename__ = 'deliveries'
    
    id = Column(Integer, primary_key=True)
    order_item_id = Column(Integer, ForeignKey('order_items.id'))
    delivery_term_id = Column(Integer, ForeignKey('delivery_terms.id'), nullable=True)  # Which term this delivery fulfills
    quantity = Column(Integer, nullable=False)
    delivery_date = Column(Date, nullable=False)  # Actual delivery date
    notes = Column(Text)  # Optional notes about the delivery
    created_at = Column(DateTime, default=datetime.now)
    
    order_item = relationship("OrderItem", back_populates="deliveries")
    delivery_term = relationship("DeliveryTerm", back_populates="deliveries")

class OrderItem(Base):
    """Modified order item to include delivery terms relationship"""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    item_id = Column(Integer, ForeignKey('items.id'))
    quantity = Column(Integer, nullable=False)
    price = Column(Float)
    delivery_date = Column(Date, nullable=False)  # Keep for backward compatibility
    delivered_quantity = Column(Integer, default=0)
    last_delivery_date = Column(Date)
    surface_treatment = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    order = relationship("Order", back_populates="items")
    item = relationship("Item", back_populates="order_items")
    deliveries = relationship("Delivery", back_populates="order_item", cascade="all, delete-orphan")
    delivery_terms = relationship("DeliveryTerm", back_populates="order_item", cascade="all, delete-orphan")

def upgrade():
    """Add delivery terms functionality"""
    from models.database import get_database_path, init_db
    
    # Get database path
    db_path = get_database_path()
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Create new tables
    Base.metadata.create_all(engine)
    
    logger.info("Delivery terms functionality added successfully")

def downgrade():
    """Remove delivery terms functionality"""
    from models.database import get_database_path
    
    db_path = get_database_path()
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Drop new tables
    DeliveryTerm.__table__.drop(engine, checkfirst=True)
    
    logger.info("Delivery terms functionality removed")

if __name__ == "__main__":
    upgrade() 