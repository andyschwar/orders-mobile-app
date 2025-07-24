import hashlib
import secrets
import string
from datetime import datetime
from sqlalchemy.orm import Session
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models.database import User, UserRole

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256()
    hash_obj.update((password + salt).encode('utf-8'))
    return f"{salt}${hash_obj.hexdigest()}"

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, hash_value = password_hash.split('$')
        hash_obj = hashlib.sha256()
        hash_obj.update((password + salt).encode('utf-8'))
        return hash_obj.hexdigest() == hash_value
    except:
        return False

def generate_password(length: int = 12) -> str:
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))

def authenticate_user(session: Session, username: str, password: str) -> User:
    """Authenticate a user with username and password"""
    user = session.query(User).filter(User.username == username).first()
    
    if user and user.is_active and verify_password(password, user.password_hash):
        # Update last login
        user.last_login = datetime.utcnow()
        session.commit()
        return user
    
    return None

def create_default_users(session: Session):
    """Create default users if they don't exist"""
    default_users = [
        {
            'username': 'admin',
            'password': 'admin123',
            'email': 'admin@orders.com',
            'role': UserRole.ADMIN
        },
        {
            'username': 'manager',
            'password': 'manager123',
            'email': 'manager@orders.com',
            'role': UserRole.MANAGER
        },
        {
            'username': 'user',
            'password': 'user123',
            'email': 'user@orders.com',
            'role': UserRole.USER
        },
        {
            'username': 'viewer',
            'password': 'viewer123',
            'email': 'viewer@orders.com',
            'role': UserRole.VIEWER
        }
    ]
    
    for user_data in default_users:
        existing_user = session.query(User).filter(User.username == user_data['username']).first()
        if not existing_user:
            user = User(
                username=user_data['username'],
                password_hash=hash_password(user_data['password']),
                email=user_data['email'],
                role=user_data['role'],
                is_active=True
            )
            session.add(user)
        else:
            # Update email if it's missing
            if not existing_user.email:
                existing_user.email = user_data['email']
    
    session.commit()

def create_user_with_email(session: Session, username: str, email: str, role: UserRole, temp_password: str = None) -> User:
    """Create a new user with email and send welcome email"""
    if not temp_password:
        temp_password = generate_password()
    
    user = User(
        username=username,
        password_hash=hash_password(temp_password),
        email=email,
        role=role,
        is_active=True
    )
    session.add(user)
    session.commit()
    
    # Send welcome email
    try:
        from .email_utils import get_email_sender
        email_sender = get_email_sender()
        email_sender.send_welcome_email(user, temp_password)
    except Exception as e:
        print(f"Warning: Could not send welcome email: {e}")
    
    return user

def request_password_reminder(session: Session, username: str) -> bool:
    """Request password reminder for user"""
    try:
        from .email_utils import get_password_reminder_manager
        reminder_manager = get_password_reminder_manager(session)
        return reminder_manager.request_password_reminder(username)
    except Exception as e:
        print(f"Error requesting password reminder: {e}")
        return False

def get_role_display_name(role: UserRole) -> str:
    """Get display name for role"""
    role_names = {
        UserRole.ADMIN: "Administrator",
        UserRole.MANAGER: "Manager", 
        UserRole.USER: "User",
        UserRole.VIEWER: "Viewer"
    }
    return role_names.get(role, str(role.value).title()) 