from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QComboBox, QFrame,
                             QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from sqlalchemy.orm import Session
from src.models.database import User, UserRole
from src.utils.auth import get_role_display_name, hash_password, generate_password
from functools import partial

class UserManagementDialog(QDialog):
    """Dialog for managing users and their email addresses"""
    
    user_updated = pyqtSignal()  # Signal emitted when user is updated
    
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("User Management")
        self.setFixedSize(800, 700)
        self.setModal(True)
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon("assets/icon.png"))
        except:
            pass
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("User Management")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        layout.addSpacing(20)
        
        # User table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels([
            "Username", "Role", "Email", "Status", "Actions"
        ])
        
        # Set column widths
        header = self.user_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Username
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Role
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Email
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        # Set row height to make buttons more readable
        self.user_table.verticalHeader().setDefaultSectionSize(40)
        
        layout.addWidget(self.user_table)
        
        layout.addSpacing(20)
        
        # Add new user section
        add_user_frame = QFrame()
        add_user_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        add_user_layout = QVBoxLayout(add_user_frame)
        
        add_user_title = QLabel("Add New User")
        add_user_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        add_user_layout.addWidget(add_user_title)
        
        # New user form
        form_layout = QVBoxLayout()
        
        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        username_label.setFixedWidth(80)
        self.new_username_edit = QLineEdit()
        self.new_username_edit.setPlaceholderText("Enter username")
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.new_username_edit)
        form_layout.addLayout(username_layout)
        
        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setFixedWidth(80)
        self.new_email_edit = QLineEdit()
        self.new_email_edit.setPlaceholderText("Enter email address")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.new_email_edit)
        form_layout.addLayout(email_layout)
        
        # Role
        role_layout = QHBoxLayout()
        role_label = QLabel("Role:")
        role_label.setFixedWidth(80)
        self.new_role_combo = QComboBox()
        
        # Filter roles based on current user permissions
        available_roles = []
        if hasattr(self, 'current_user') and self.current_user:
            if self.current_user.role.value == 'admin':
                # Admin can create any role
                available_roles = list(UserRole)
            elif self.current_user.role.value == 'manager':
                # Manager can only create user and viewer roles
                available_roles = [UserRole.USER, UserRole.VIEWER]
            else:
                # Other roles cannot create users
                available_roles = []
        else:
            # Default to all roles if no current user
            available_roles = list(UserRole)
        
        for role in available_roles:
            self.new_role_combo.addItem(get_role_display_name(role), role)
        
        role_layout.addWidget(role_label)
        role_layout.addWidget(self.new_role_combo)
        form_layout.addLayout(role_layout)
        
        # Add user button
        add_user_button = QPushButton("Add User")
        add_user_button.clicked.connect(self.add_user)
        form_layout.addWidget(add_user_button)
        
        add_user_layout.addLayout(form_layout)
        layout.addWidget(add_user_frame)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_users)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Load users
        self.load_users()
        
    def load_users(self):
        """Load all users into the table"""
        users = self.session.query(User).order_by(User.username).all()
        self.user_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            # Username
            username_item = QTableWidgetItem(user.username)
            username_item.setFlags(username_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.user_table.setItem(row, 0, username_item)
            
            # Role
            role_item = QTableWidgetItem(get_role_display_name(user.role))
            role_item.setFlags(role_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.user_table.setItem(row, 1, role_item)
            
            # Email
            email_item = QTableWidgetItem(user.email or "")
            self.user_table.setItem(row, 2, email_item)
            
            # Status
            status_item = QTableWidgetItem("Active" if user.is_active else "Inactive")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.user_table.setItem(row, 3, status_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 5, 5, 5)
            actions_layout.setSpacing(5)
            
            update_button = QPushButton("Update")
            update_button.setMinimumHeight(25)
            update_button.clicked.connect(partial(self.update_user, row))
            actions_layout.addWidget(update_button)
            
            # Add show password button
            show_password_button = QPushButton("Show Password")
            show_password_button.setMinimumHeight(25)
            show_password_button.clicked.connect(partial(self.show_password, row))
            actions_layout.addWidget(show_password_button)
            
            # Add reset password button
            reset_password_button = QPushButton("Reset Password")
            reset_password_button.setMinimumHeight(25)
            reset_password_button.clicked.connect(partial(self.reset_password, row))
            actions_layout.addWidget(reset_password_button)
            
            # Add delete button only for admins
            if hasattr(self, 'current_user') and self.current_user and self.current_user.role.value == 'admin':
                delete_button = QPushButton("Delete")
                delete_button.setMinimumHeight(25)
                delete_button.clicked.connect(partial(self.delete_user, row))
                actions_layout.addWidget(delete_button)
            
            self.user_table.setCellWidget(row, 4, actions_widget)
    
    def update_user(self, row):
        """Update user email address"""
        try:
            # Check if dialog is still valid
            if not self.isVisible():
                return
                
            username = self.user_table.item(row, 0).text()
            email = self.user_table.item(row, 2).text().strip()
            
            user = self.session.query(User).filter(User.username == username).first()
            if not user:
                QMessageBox.critical(self, "Error", "User not found.")
                return
            
            # Validate email format if provided
            if email and '@' not in email:
                QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
                return
            
            # Check if email is already used by another user
            if email:
                existing_user = self.session.query(User).filter(
                    User.email == email,
                    User.id != user.id
                ).first()
                if existing_user:
                    QMessageBox.warning(
                        self, 
                        "Duplicate Email", 
                        f"Email '{email}' is already assigned to user '{existing_user.username}'. "
                        "Please use a different email address."
                    )
                    return
            
            # Update email
            user.email = email if email else None
            
            self.session.commit()
            
            QMessageBox.information(self, "Success", f"Email updated for user '{username}'")
            self.user_updated.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error updating user: {str(e)}")
            try:
                self.session.rollback()
            except:
                pass
    
    def reset_password(self, row):
        """Reset user password"""
        try:
            # Check if dialog is still valid
            if not self.isVisible():
                return
                
            username = self.user_table.item(row, 0).text()
            
            # Check if trying to reset own password
            if hasattr(self, 'current_user') and self.current_user and username == self.current_user.username:
                QMessageBox.warning(self, "Error", "You cannot reset your own password from this dialog.")
                return
            
            user = self.session.query(User).filter(User.username == username).first()
            if not user:
                QMessageBox.critical(self, "Error", "User not found.")
                return
            
            # Confirm password reset
            reply = QMessageBox.question(
                self, 
                "Confirm Password Reset", 
                f"Are you sure you want to reset the password for user '{username}'?\n\n"
                f"A new temporary password will be generated and shown to you.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Generate new temporary password
                new_password = generate_password()
                user.password_hash = hash_password(new_password)
                
                self.session.commit()
                
                # Show the new password
                QMessageBox.information(
                    self, 
                    "Password Reset", 
                    f"Password has been reset for user '{username}'.\n\n"
                    f"New temporary password: {new_password}\n\n"
                    f"Please inform the user of their new password."
                )
                
                # Send email notification if user has email
                if user.email:
                    try:
                        from src.utils.email_utils import get_email_sender
                        email_sender = get_email_sender()
                        email_sender.send_password_reset_email(user, new_password)
                        QMessageBox.information(
                            self,
                            "Email Sent",
                            f"Password reset notification has been sent to {user.email}"
                        )
                    except Exception as e:
                        QMessageBox.warning(
                            self,
                            "Email Error",
                            f"Could not send password reset email: {str(e)}\n\n"
                            f"Please manually inform the user of their new password."
                        )
                
                self.user_updated.emit()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error resetting password: {str(e)}")
            try:
                self.session.rollback()
            except:
                pass
    
    def show_password(self, row):
        """Show current password for user"""
        try:
            # Check if dialog is still valid
            if not self.isVisible():
                return
                
            username = self.user_table.item(row, 0).text()
            
            user = self.session.query(User).filter(User.username == username).first()
            if not user:
                QMessageBox.critical(self, "Error", "User not found.")
                return
            
            # Get password reminder manager
            from src.utils.email_utils import get_password_reminder_manager
            pm = get_password_reminder_manager(self.session)
            
            # Try to get current password
            current_password = pm._get_current_password(user)
            
            if current_password:
                QMessageBox.information(
                    self, 
                    "Current Password", 
                    f"Current password for user '{username}':\n\n{current_password}"
                )
            else:
                QMessageBox.warning(
                    self, 
                    "Password Not Available", 
                    f"Cannot retrieve the current password for user '{username}'.\n\n"
                    f"This is only available for default system users (admin, manager, user, viewer).\n\n"
                    f"For custom users, you can use the 'Reset Password' feature instead."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error retrieving password: {str(e)}")
    
    def delete_user(self, row):
        """Delete a user (admin only)"""
        username = self.user_table.item(row, 0).text()
        
        # Check if trying to delete self
        if hasattr(self, 'current_user') and self.current_user and username == self.current_user.username:
            QMessageBox.warning(self, "Error", "You cannot delete your own account.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Are you sure you want to delete user '{username}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            user = self.session.query(User).filter(User.username == username).first()
            if not user:
                QMessageBox.critical(self, "Error", "User not found.")
                return
            
            try:
                self.session.delete(user)
                self.session.commit()
                QMessageBox.information(self, "Success", f"User '{username}' has been deleted.")
                self.load_users()
                self.user_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error deleting user: {str(e)}")
                self.session.rollback()
    
    def add_user(self):
        """Add a new user"""
        username = self.new_username_edit.text().strip()
        email = self.new_email_edit.text().strip()
        role = self.new_role_combo.currentData()
        
        if not username:
            QMessageBox.warning(self, "Error", "Username is required.")
            return
        
        # Check if user already exists
        existing_user = self.session.query(User).filter(User.username == username).first()
        if existing_user:
            QMessageBox.warning(self, "Error", f"User '{username}' already exists.")
            return
        
        # Check if email is already used by another user
        if email:
            existing_email_user = self.session.query(User).filter(User.email == email).first()
            if existing_email_user:
                QMessageBox.warning(
                    self, 
                    "Duplicate Email", 
                    f"Email '{email}' is already assigned to user '{existing_email_user.username}'. "
                    "Please use a different email address."
                )
                return
        
        # Check permissions for role assignment
        from src.utils.permissions import get_permissions_manager
        pm = get_permissions_manager()
        
        # Only allow creating users with roles that the current user can manage
        # For now, managers can only create users with 'user' and 'viewer' roles
        # Admins can create any role
        if hasattr(self, 'current_user') and self.current_user:
            if self.current_user.role.value == 'manager' and role.value in ['admin', 'manager']:
                QMessageBox.warning(self, "Error", "Managers can only create users with 'user' or 'viewer' roles.")
                return
        
        # Generate temporary password
        temp_password = generate_password()
        
        try:
            # Create new user
            new_user = User(
                username=username,
                password_hash=hash_password(temp_password),
                email=email if email else None,
                role=role,
                is_active=True
            )
            self.session.add(new_user)
            self.session.commit()
            
            # Send welcome email if email is provided
            if email:
                try:
                    from src.utils.email_utils import get_email_sender
                    email_sender = get_email_sender()
                    email_sender.send_welcome_email(new_user, temp_password)
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"User '{username}' created successfully!\n"
                        f"Temporary password: {temp_password}\n"
                        f"Welcome email sent to: {email}"
                    )
                except Exception as e:
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"User '{username}' created successfully!\n"
                        f"Temporary password: {temp_password}\n"
                        f"Could not send welcome email: {str(e)}"
                    )
            else:
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"User '{username}' created successfully!\n"
                    f"Temporary password: {temp_password}"
                )
            
            # Clear form
            self.new_username_edit.clear()
            self.new_email_edit.clear()
            
            # Reload users
            self.load_users()
            self.user_updated.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating user: {str(e)}")
            self.session.rollback()
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        try:
            # Disconnect signals to prevent crashes
            self.user_updated.disconnect()
        except:
            pass
        super().closeEvent(event)