from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
from sqlalchemy.orm import Session
from src.utils.auth import authenticate_user, get_role_display_name
from src.models.database import User

class LoginDialog(QDialog):
    """Login dialog for user authentication"""
    
    login_successful = pyqtSignal(object)  # Signal emitted with user object on successful login
    
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Orders Management - Login")
        self.setFixedSize(450, 300)
        self.setModal(True)
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon("assets/icon.png"))
        except:
            pass
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Orders Management System")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Please log in to continue")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        layout.addWidget(subtitle_label)
        
        layout.addSpacing(20)
        
        # User selection dropdown
        user_layout = QHBoxLayout()
        user_label = QLabel("User:")
        user_label.setFixedWidth(80)
        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(200)
        self.load_users()
        user_layout.addWidget(user_label)
        user_layout.addWidget(self.user_combo)
        layout.addLayout(user_layout)
        
        # Password field
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        password_label.setFixedWidth(80)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton("Login")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.login)
        
        self.forgot_password_button = QPushButton("Forgot Password?")
        self.forgot_password_button.clicked.connect(self.show_password_reset)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.forgot_password_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect enter key to login
        self.user_combo.currentIndexChanged.connect(self.on_user_changed)
        self.password_input.returnPressed.connect(self.login)
        
        # Focus on password field
        self.password_input.setFocus()
        
    def load_users(self):
        """Load all users into the combo box"""
        users = self.session.query(User).order_by(User.username).all()
        self.users = users
        
        for user in users:
            role_name = get_role_display_name(user.role)
            self.user_combo.addItem(f"{user.username} ({role_name})", user.id)
    
    def on_user_changed(self):
        """Handle user selection change"""
        # Clear password field when user changes
        self.password_input.clear()
        self.password_input.setFocus()
        
    def login(self):
        """Handle login attempt"""
        if self.user_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Login Error", "Please select a user.")
            return
            
        password = self.password_input.text()
        
        if not password:
            QMessageBox.warning(self, "Login Error", "Please enter password.")
            return
        
        # Get selected user
        user_id = self.user_combo.currentData()
        selected_user = self.session.query(User).filter(User.id == user_id).first()
        
        if not selected_user:
            QMessageBox.critical(self, "Login Error", "Selected user not found.")
            return
        
        # Authenticate user with password
        user = authenticate_user(self.session, selected_user.username, password)
        
        if user:
            self.user = user
            role_name = get_role_display_name(user.role)
            # Use name if available, otherwise fall back to username
            display_name = user.name if user.name else user.username
            QMessageBox.information(
                self, 
                "Login Successful", 
                f"Welcome, {display_name}!\nRole: {role_name}"
            )
            self.login_successful.emit(user)
            self.accept()
        else:
            QMessageBox.critical(
                self, 
                "Login Failed", 
                "Invalid password.\nPlease try again."
            )
            self.password_input.clear()
            self.password_input.setFocus()
    
    def get_user(self):
        """Return the authenticated user"""
        return self.user
    
    def show_password_reset(self):
        """Show password reminder dialog"""
        from .password_reset_dialog import PasswordReminderDialog
        reminder_dialog = PasswordReminderDialog(self.session, self)
        reminder_dialog.exec() 