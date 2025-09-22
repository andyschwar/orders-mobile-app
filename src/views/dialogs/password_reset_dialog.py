from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame,
                             QTextEdit, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
from sqlalchemy.orm import Session
from src.utils.auth import request_password_reminder, get_role_display_name
from src.models.database import User

class PasswordReminderDialog(QDialog):
    """Password reminder dialog for users"""
    
    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Password Reminder")
        self.setFixedSize(450, 300)
        self.setModal(True)
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon("assets/icon.png"))
        except:
            pass
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Password Reminder")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Enter your username to receive your current password via email")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        layout.addWidget(subtitle_label)
        
        layout.addSpacing(20)
        
        # Username selection dropdown
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        username_label.setFixedWidth(80)
        self.username_combo = QComboBox()
        self.username_combo.setMinimumWidth(200)
        self.load_users()
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_combo)
        layout.addLayout(username_layout)
        
        # Email display
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setFixedWidth(80)
        self.email_display = QLabel("Select a user to see their email")
        self.email_display.setStyleSheet("color: gray;")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_display)
        layout.addLayout(email_layout)
        
        layout.addSpacing(20)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setMaximumHeight(80)
        instructions.setPlainText(
            "Instructions:\n"
            "1. Select your username from the dropdown\n"
            "2. Verify your email address is correct\n"
            "3. Click 'Send Reminder Email' to receive your current password\n"
            "4. Check your email and use the password to log in"
        )
        instructions.setReadOnly(True)
        layout.addWidget(instructions)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.send_button = QPushButton("Send Reminder Email")
        self.send_button.setDefault(True)
        self.send_button.clicked.connect(self.send_reminder_email)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect signals
        self.username_combo.currentIndexChanged.connect(self.on_user_changed)
        
        # Focus on username combo
        self.username_combo.setFocus()
        
    def load_users(self):
        """Load all users with emails into the combo box"""
        users = self.session.query(User).filter(User.email.isnot(None)).order_by(User.username).all()
        self.users = users
        
        for user in users:
            role_name = get_role_display_name(user.role)
            self.username_combo.addItem(f"{user.username} ({role_name})", user.id)
    
    def on_user_changed(self):
        """Handle user selection change"""
        if self.username_combo.currentIndex() >= 0:
            user_id = self.username_combo.currentData()
            selected_user = self.session.query(User).filter(User.id == user_id).first()
            
            if selected_user and selected_user.email:
                self.email_display.setText(selected_user.email)
                self.email_display.setStyleSheet("color: black;")
            else:
                self.email_display.setText("No email available")
                self.email_display.setStyleSheet("color: red;")
        else:
            self.email_display.setText("Select a user to see their email")
            self.email_display.setStyleSheet("color: gray;")
    
    def send_reminder_email(self):
        """Send password reminder email"""
        if self.username_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Error", "Please select a user.")
            return
        
        # Get selected user
        user_id = self.username_combo.currentData()
        selected_user = self.session.query(User).filter(User.id == user_id).first()
        
        if not selected_user:
            QMessageBox.critical(self, "Error", "Selected user not found.")
            return
        
        if not selected_user.email:
            QMessageBox.critical(self, "Error", "Selected user has no email address configured.")
            return
        
        # Send reminder email
        try:
            success = request_password_reminder(self.session, selected_user.username)
            
            if success:
                QMessageBox.information(
                    self, 
                    "Email Sent", 
                    f"Password reminder email has been sent to:\n{selected_user.email}\n\n"
                    "Please check your email for your current password."
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    "Failed to send password reminder email.\n\n"
                    "This user may not have a known password, or email configuration is incorrect.\n"
                    "Please contact your administrator."
                )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Error sending password reminder email:\n{str(e)}"
            )

class EmailConfigDialog(QDialog):
    """Dialog for configuring email settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Email Configuration")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Email Configuration")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        layout.addSpacing(20)
        
        # SMTP Server
        smtp_layout = QHBoxLayout()
        smtp_label = QLabel("SMTP Server:")
        smtp_label.setFixedWidth(120)
        self.smtp_input = QLineEdit()
        self.smtp_input.setPlaceholderText("smtp.gmail.com")
        smtp_layout.addWidget(smtp_label)
        smtp_layout.addWidget(self.smtp_input)
        layout.addLayout(smtp_layout)
        
        # SMTP Port
        port_layout = QHBoxLayout()
        port_label = QLabel("SMTP Port:")
        port_label.setFixedWidth(120)
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("587")
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)
        
        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email Address:")
        email_label.setFixedWidth(120)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your-email@gmail.com")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password/App Password:")
        password_label.setFixedWidth(120)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your email password or app password")
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        layout.addSpacing(20)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setMaximumHeight(120)
        instructions.setPlainText(
            "Email Configuration Instructions:\n\n"
            "For Gmail:\n"
            "- SMTP Server: smtp.gmail.com\n"
            "- SMTP Port: 587\n"
            "- Use an App Password (not your regular password)\n\n"
            "For Outlook:\n"
            "- SMTP Server: smtp-mail.outlook.com\n"
            "- SMTP Port: 587\n\n"
            "For other providers, check their SMTP settings."
        )
        instructions.setReadOnly(True)
        layout.addWidget(instructions)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        
        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save_config)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Load current config
        self.load_config()
    
    def load_config(self):
        """Load current email configuration"""
        try:
            from src.utils.email_utils import EmailConfig
            config = EmailConfig()
            
            self.smtp_input.setText(config.config.get('smtp_server', 'smtp.gmail.com'))
            self.port_input.setText(str(config.config.get('smtp_port', 587)))
            self.email_input.setText(config.config.get('sender_email', ''))
            self.password_input.setText(config.config.get('sender_password', ''))
        except Exception as e:
            pass
    
    def save_config(self):
        """Save email configuration"""
        try:
            from src.utils.email_utils import EmailConfig
            config = EmailConfig()
            
            config.update_config(
                smtp_server=self.smtp_input.text(),
                smtp_port=int(self.port_input.text()),
                sender_email=self.email_input.text(),
                sender_password=self.password_input.text()
            )
            
            QMessageBox.information(self, "Success", "Email configuration saved successfully!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving configuration:\n{str(e)}")
    
    def test_connection(self):
        """Test email connection"""
        try:
            from src.utils.email_utils import EmailSender
            email_sender = EmailSender()
            
            # Test with a simple email
            success = email_sender._send_email(
                to_email=self.email_input.text(),
                subject="Test Email",
                html_content="<p>This is a test email.</p>",
                text_content="This is a test email."
            )
            
            if success:
                QMessageBox.information(self, "Success", "Email connection test successful!")
            else:
                QMessageBox.critical(self, "Error", "Email connection test failed. Please check your settings.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error testing connection:\n{str(e)}") 