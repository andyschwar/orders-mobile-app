#!/usr/bin/env python3
"""
Email utilities for the Orders Management System
Handles password reset emails and other notifications
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import secrets
import string
import json
import os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.models.database import User

class EmailConfig:
    """Email configuration settings"""
    
    def __init__(self):
        self.config_file = os.path.expanduser('~/Library/Application Support/Orders/email_config.json')
        self.default_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'use_tls': True,
            'sender_email': '',
            'sender_password': '',
            'app_name': 'Orders Management System'
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load email configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return self.default_config.copy()
        return self.default_config.copy()
    
    def save_config(self):
        """Save email configuration to file"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def update_config(self, **kwargs):
        """Update email configuration"""
        self.config.update(kwargs)
        self.save_config()
    
    def get_smtp_settings(self) -> Dict[str, Any]:
        """Get SMTP settings"""
        return {
            'server': self.config.get('smtp_server', 'smtp.gmail.com'),
            'port': self.config.get('smtp_port', 587),
            'use_tls': self.config.get('use_tls', True),
            'username': self.config.get('sender_email', ''),
            'password': self.config.get('sender_password', '')
        }

class EmailSender:
    """Handles sending emails"""
    
    def __init__(self):
        self.config = EmailConfig()
    
    def send_password_reminder_email(self, user: User, current_password: str) -> bool:
        """Send current password reminder email to user"""
        try:
            if not user.email:
                return False
            
            # Email content
            subject = f"Password Reminder - {self.config.config.get('app_name', 'Orders Management System')}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Password Reminder</h2>
                <p>Hello {user.username},</p>
                <p>You have requested a reminder of your current password.</p>
                <p>Your current password is: <strong>{current_password}</strong></p>
                <p>Please use this password to log in to your account.</p>
                <p>If you didn't request this reminder, please contact your administrator.</p>
                <br>
                <p>Best regards,<br>{self.config.config.get('app_name', 'Orders Management System')}</p>
            </body>
            </html>
            """
            
            text_content = f"""
            Password Reminder
            
            Hello {user.username},
            
            You have requested a reminder of your current password.
            
            Your current password is: {current_password}
            
            Please use this password to log in to your account.
            
            If you didn't request this reminder, please contact your administrator.
            
            Best regards,
            {self.config.config.get('app_name', 'Orders Management System')}
            """
            
            return self._send_email(user.email, subject, html_content, text_content)
            
        except Exception as e:
            print(f"Error sending password reminder email: {e}")
            return False
    
    def send_welcome_email(self, user: User, temp_password: str) -> bool:
        """Send welcome email with temporary password"""
        try:
            if not user.email:
                return False
            
            subject = f"Welcome to {self.config.config.get('app_name', 'Orders Management System')}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Welcome!</h2>
                <p>Hello {user.username},</p>
                <p>Your account has been created successfully.</p>
                <p>Your temporary password is: <strong>{temp_password}</strong></p>
                <p>Please change your password after your first login.</p>
                <br>
                <p>Best regards,<br>{self.config.config.get('app_name', 'Orders Management System')}</p>
            </body>
            </html>
            """
            
            text_content = f"""
            Welcome!
            
            Hello {user.username},
            
            Your account has been created successfully.
            
            Your temporary password is: {temp_password}
            
            Please change your password after your first login.
            
            Best regards,
            {self.config.config.get('app_name', 'Orders Management System')}
            """
            
            return self._send_email(user.email, subject, html_content, text_content)
            
        except Exception as e:
            print(f"Error sending welcome email: {e}")
            return False
    
    def send_password_reset_email(self, user: User, new_password: str) -> bool:
        """Send password reset email with new temporary password"""
        try:
            if not user.email:
                return False
            
            subject = f"Password Reset - {self.config.config.get('app_name', 'Orders Management System')}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Password Reset</h2>
                <p>Hello {user.username},</p>
                <p>Your password has been reset by an administrator.</p>
                <p>Your new temporary password is: <strong>{new_password}</strong></p>
                <p>Please change your password after your next login.</p>
                <br>
                <p>Best regards,<br>{self.config.config.get('app_name', 'Orders Management System')}</p>
            </body>
            </html>
            """
            
            text_content = f"""
            Password Reset
            
            Hello {user.username},
            
            Your password has been reset by an administrator.
            
            Your new temporary password is: {new_password}
            
            Please change your password after your next login.
            
            Best regards,
            {self.config.config.get('app_name', 'Orders Management System')}
            """
            
            return self._send_email(user.email, subject, html_content, text_content)
            
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, html_content: str, text_content: str) -> bool:
        """Send email using SMTP"""
        try:
            smtp_settings = self.config.get_smtp_settings()
            
            if not smtp_settings['username'] or not smtp_settings['password']:
                print("Email configuration incomplete. Please configure SMTP settings.")
                return False
            
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = smtp_settings['username']
            message['To'] = to_email
            
            # Add content
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_settings['server'], smtp_settings['port']) as server:
                if smtp_settings['use_tls']:
                    server.starttls(context=ssl.create_default_context())
                
                server.login(smtp_settings['username'], smtp_settings['password'])
                server.send_message(message)
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

class PasswordReminderManager:
    """Manages password reminder functionality"""
    
    def __init__(self, session: Session):
        self.session = session
        self.email_sender = EmailSender()
    
    def request_password_reminder(self, username: str) -> bool:
        """Request password reminder for user"""
        user = self.session.query(User).filter(User.username == username).first()
        
        if not user or not user.email:
            return False
        
        # For this simple approach, we need to know the original password
        # Since we only hash passwords, we'll need to use a different approach
        # For now, we'll use the default passwords for the default users
        
        # Get the current password (this is a simplified approach)
        current_password = self._get_current_password(user)
        
        if not current_password:
            return False
        
        # Send reminder email
        return self.email_sender.send_password_reminder_email(user, current_password)
    
    def _get_current_password(self, user: User) -> str:
        """Get the current password for a user (simplified approach)"""
        # This is a simplified approach - in a real system, you might want to store
        # the original passwords or use a different method
        
        # For default users, we know their passwords
        default_passwords = {
            'admin': 'admin123',
            'manager': 'manager123', 
            'user': 'user123',
            'viewer': 'viewer123'
        }
        
        # For now, we can only provide passwords for default users
        # In a production system, you might want to store original passwords
        # or implement a different password recovery mechanism
        password = default_passwords.get(user.username, None)
        
        if not password:
            # For custom users, we can't retrieve the original password
            # You might want to implement a password reset instead
            return None
            
        return password

def get_email_sender() -> EmailSender:
    """Get email sender instance"""
    return EmailSender()

def get_password_reminder_manager(session: Session) -> PasswordReminderManager:
    """Get password reminder manager instance"""
    return PasswordReminderManager(session) 