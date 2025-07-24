from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout, QCheckBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
import os
from models.database import get_database_path, set_database_path
from .barcode_settings_dialog import BarcodeSettingsDialog

class SettingsDialog(QDialog):
    def __init__(self, session=None, parent=None, current_user=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(600, 400)
        
        self._setup_ui()
        self._load_current_settings()
        
    def _setup_ui(self):
        """Set up the settings dialog UI"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Database Settings Tab
        db_tab = QWidget()
        db_layout = QVBoxLayout(db_tab)
        
        # Database Settings Group
        db_group = QGroupBox("Database Settings")
        db_form_layout = QFormLayout(db_group)
        
        # Database Path
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setPlaceholderText("Enter database file path or browse to select")
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_database)
        
        db_path_layout = QHBoxLayout()
        db_path_layout.addWidget(self.db_path_edit)
        db_path_layout.addWidget(browse_button)
        
        db_form_layout.addRow("Database Path:", db_path_layout)
        
        # Network Database Options
        self.use_network_db = QCheckBox("Use network database")
        self.use_network_db.toggled.connect(self._on_network_db_toggled)
        db_form_layout.addRow("", self.use_network_db)
        
        # Network path options
        self.network_path_edit = QLineEdit()
        self.network_path_edit.setPlaceholderText("\\\\server\\share\\orders.db or smb://server/share/orders.db")
        db_form_layout.addRow("Network Path:", self.network_path_edit)
        
        # Help text
        help_label = QLabel(
            "To share the database with your colleague:\n"
            "1. Place the database file in a shared folder (Google Drive, Dropbox, network drive)\n"
            "2. Enter the full path to the database file\n"
            "3. Both users should point to the same file\n\n"
            "Examples:\n"
            "• Google Drive: /Users/username/Google Drive/orders.db\n"
            "• Network: //server/share/orders.db\n"
            "• Dropbox: /Users/username/Dropbox/orders.db"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: gray; font-size: 11px;")
        
        db_layout.addWidget(db_group)
        db_layout.addWidget(help_label)
        
        # Database tab buttons
        db_button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self._test_connection)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_settings)
        
        db_button_layout.addWidget(self.test_button)
        db_button_layout.addStretch()
        db_button_layout.addWidget(self.save_button)
        
        db_layout.addLayout(db_button_layout)
        
        # Add database tab
        tab_widget.addTab(db_tab, "Database")
        
        # Email Configuration Tab (Admin only)
        if self.current_user and self.current_user.role.value == 'admin':
            email_tab = QWidget()
            email_layout = QVBoxLayout(email_tab)
            
            # Email Settings Group
            email_group = QGroupBox("Email Configuration")
            email_form_layout = QFormLayout(email_group)
            
            # SMTP Server
            self.smtp_server_edit = QLineEdit()
            self.smtp_server_edit.setPlaceholderText("smtp.gmail.com")
            email_form_layout.addRow("SMTP Server:", self.smtp_server_edit)
            
            # SMTP Port
            self.smtp_port_edit = QLineEdit()
            self.smtp_port_edit.setPlaceholderText("587")
            email_form_layout.addRow("SMTP Port:", self.smtp_port_edit)
            
            # Email Address
            self.email_address_edit = QLineEdit()
            self.email_address_edit.setPlaceholderText("your-email@gmail.com")
            email_form_layout.addRow("Email Address:", self.email_address_edit)
            
            # Password
            self.email_password_edit = QLineEdit()
            self.email_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.email_password_edit.setPlaceholderText("Enter your email password or app password")
            email_form_layout.addRow("Password:", self.email_password_edit)
            
            # Help text for email
            email_help_label = QLabel(
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
            email_help_label.setWordWrap(True)
            email_help_label.setStyleSheet("color: gray; font-size: 11px;")
            
            email_layout.addWidget(email_group)
            email_layout.addWidget(email_help_label)
            
            # Email tab buttons
            email_button_layout = QHBoxLayout()
            
            self.test_email_button = QPushButton("Test Email")
            self.test_email_button.clicked.connect(self._test_email)
            
            self.save_email_button = QPushButton("Save Email Settings")
            self.save_email_button.clicked.connect(self._save_email_settings)
            
            email_button_layout.addWidget(self.test_email_button)
            email_button_layout.addStretch()
            email_button_layout.addWidget(self.save_email_button)
            
            email_layout.addLayout(email_button_layout)
            
            # Add email tab
            tab_widget.addTab(email_tab, "Email")
        
        # Barcode Settings Tab (Admin only)
        if self.current_user and self.current_user.role.value == 'admin':
            barcode_tab = QWidget()
            barcode_layout = QVBoxLayout(barcode_tab)
            
            # Barcode settings description
            barcode_desc = QLabel(
                "Configure barcode generation settings for each customer.\n"
                "Only customers with barcodes enabled will have barcodes generated on their labels."
            )
            barcode_desc.setStyleSheet("color: gray; font-size: 11px;")
            barcode_layout.addWidget(barcode_desc)
            
            # Barcode settings button
            barcode_button = QPushButton("Manage Barcode Settings")
            barcode_button.clicked.connect(self._open_barcode_settings)
            barcode_layout.addWidget(barcode_button)
            
            barcode_layout.addStretch()
            
            # Add barcode tab
            tab_widget.addTab(barcode_tab, "Barcode Settings")
        
        layout.addWidget(tab_widget)
        
        # Main dialog buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Close")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def _load_current_settings(self):
        """Load current settings into the dialog"""
        current_path = get_database_path()
        self.db_path_edit.setText(current_path)
        
        # Check if it's a network path
        is_network = (
            current_path.startswith('//') or 
            current_path.startswith('\\\\') or
            'Google Drive' in current_path or
            'Dropbox' in current_path or
            'OneDrive' in current_path
        )
        
        self.use_network_db.setChecked(is_network)
        if is_network:
            self.network_path_edit.setText(current_path)
        
        # Load email settings if admin
        if self.current_user and self.current_user.role.value == 'admin':
            self._load_email_settings()
            
    def _browse_database(self):
        """Browse for database file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Database File",
            "",
            "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*)"
        )
        
        if file_path:
            self.db_path_edit.setText(file_path)
            
    def _on_network_db_toggled(self, checked):
        """Handle network database checkbox toggle"""
        if checked:
            self.network_path_edit.setEnabled(True)
            self.db_path_edit.setEnabled(False)
        else:
            self.network_path_edit.setEnabled(False)
            self.db_path_edit.setEnabled(True)
            
    def _test_connection(self):
        """Test database connection"""
        try:
            path = self._get_selected_path()
            
            if not path:
                QMessageBox.warning(self, "Warning", "Please enter a database path")
                return
            
            import sqlite3
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()
            
            QMessageBox.information(
                self, 
                "Connection Test", 
                f"Database connection successful!\n\nPath: {path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Connection Test Failed", 
                f"Database connection failed:\n\nPath: {path}\n\nError: {str(e)}"
            )
    
    def _get_selected_path(self):
        """Get the selected database path"""
        if self.use_network_db.isChecked():
            return self.network_path_edit.text().strip()
        else:
            return self.db_path_edit.text().strip()
            
    def _save_settings(self):
        """Save the settings"""
        try:
            path = self._get_selected_path()
            
            if not path:
                QMessageBox.warning(self, "Warning", "Please enter a database path")
                return
            
            # Check if the directory exists and is writable
            db_dir = os.path.dirname(path)
            if db_dir and not os.path.exists(db_dir):
                QMessageBox.warning(
                    self, 
                    "Directory Not Found", 
                    f"The directory does not exist:\n{db_dir}\n\nPlease create the directory first."
                )
                return
            
            # Check if we can write to the directory
            if db_dir and not os.access(db_dir, os.W_OK):
                QMessageBox.warning(
                    self, 
                    "Permission Error", 
                    f"Cannot write to directory:\n{db_dir}\n\nPlease check permissions."
                )
                return
                
            # Test the connection before saving using sqlite3 directly
            import sqlite3
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                conn.close()
                
                # Save the path
                set_database_path(path)
                
                QMessageBox.information(
                    self, 
                    "Settings Saved", 
                    f"Database path has been updated to:\n{path}\n\nPlease restart the application for changes to take effect."
                )
                
                self.accept()
                
            except sqlite3.Error as sqlite_error:
                error_msg = str(sqlite_error)
                
                # Provide more helpful error messages
                if "no such table" in error_msg.lower():
                    # This is actually okay for a new database
                    set_database_path(path)
                    QMessageBox.information(
                        self, 
                        "Settings Saved", 
                        f"Database path has been updated to:\n{path}\n\nThis appears to be a new database location.\nPlease restart the application for changes to take effect."
                    )
                    self.accept()
                elif "permission" in error_msg.lower():
                    QMessageBox.critical(
                        self, 
                        "Permission Error", 
                        f"Cannot access database file:\n{path}\n\nError: {error_msg}\n\nPlease check file permissions."
                    )
                else:
                    QMessageBox.critical(
                        self, 
                        "Connection Error", 
                        f"Database connection failed:\n\nPath: {path}\n\nError: {error_msg}"
                    )
                    
        except Exception as e:
            error_msg = str(e)
            QMessageBox.critical(
                self, 
                "Connection Error", 
                f"Database connection failed:\n\nPath: {path}\n\nError: {error_msg}"
            )
    
    def _open_barcode_settings(self):
        """Open the barcode settings dialog"""
        if not self.session:
            QMessageBox.warning(self, "Warning", "No database session available.")
            return
        
        dialog = BarcodeSettingsDialog(self.session, self)
        dialog.settings_updated.connect(self._on_barcode_settings_updated)
        dialog.exec()
    
    def _on_barcode_settings_updated(self):
        """Handle barcode settings updates"""
        QMessageBox.information(self, "Success", "Barcode settings have been updated!")
    
    def _load_email_settings(self):
        """Load current email settings"""
        try:
            from src.utils.email_utils import EmailConfig
            config = EmailConfig()
            
            self.smtp_server_edit.setText(config.config.get('smtp_server', 'smtp.gmail.com'))
            self.smtp_port_edit.setText(str(config.config.get('smtp_port', 587)))
            self.email_address_edit.setText(config.config.get('sender_email', ''))
            self.email_password_edit.setText(config.config.get('sender_password', ''))
        except Exception as e:
            print(f"Error loading email settings: {e}")
    
    def _save_email_settings(self):
        """Save email settings"""
        try:
            from src.utils.email_utils import EmailConfig
            config = EmailConfig()
            
            config.update_config(
                smtp_server=self.smtp_server_edit.text(),
                smtp_port=int(self.smtp_port_edit.text()),
                sender_email=self.email_address_edit.text(),
                sender_password=self.email_password_edit.text()
            )
            
            QMessageBox.information(self, "Success", "Email settings saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving email settings:\n{str(e)}")
    
    def _test_email(self):
        """Test email configuration"""
        try:
            from src.utils.email_utils import EmailSender
            email_sender = EmailSender()
            
            # Test with a simple email
            success = email_sender._send_email(
                to_email=self.email_address_edit.text(),
                subject="Test Email",
                html_content="<p>This is a test email from Orders Management System.</p>",
                text_content="This is a test email from Orders Management System."
            )
            
            if success:
                QMessageBox.information(self, "Success", "Email test successful! Check your inbox.")
            else:
                QMessageBox.critical(self, "Error", "Email test failed. Please check your settings.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error testing email:\n{str(e)}") 