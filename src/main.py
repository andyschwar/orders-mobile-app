import sys
import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QMessageBox, QDialog
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from sqlalchemy.orm import sessionmaker, scoped_session
from models.database import init_db, User, UserRole
from utils.auth import create_default_users, get_role_display_name
from views.tabs.customers_tab import CustomersTab
from views.tabs.products_tab import ProductsTab
from views.tabs.items_tab import ItemsTab
from views.tabs.orders_tab import OrdersTab
from views.tabs.order_items_tab import OrderItemsTab
from views.tabs.employees_tab import EmployeesTab
from views.tabs.import_tab import ImportTab
from views.tabs.labels_tab import LabelsTab
from views.tabs.production_plans_tab import ProductionPlansTab
from views.tabs.reports_tab import ReportsTab
from views.tabs.components_tab import ComponentsTab
from views.tabs.stock_tab import StockTab
from views.dialogs.settings_dialog import SettingsDialog
from views.dialogs.login_dialog import LoginDialog
from views.dialogs.permissions_dialog import PermissionsDialog
from views.dialogs.database_management_dialog import DatabaseManagementDialog

# Set up logging
log_dir = os.path.expanduser('~/Library/Logs/Orders')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'orders.log')
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orders Management System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize authentication
        self.current_user = None
        
        self.setStyleSheet("""
            QMainWindow {
                background: white;
            }
            QStatusBar {
                background: white;
                border: none;
            }
            QToolBar {
                background: white;
                border: none;
                spacing: 5px;
            }
            QMenuBar {
                background: white;
                border: none;
            }
            QMenuBar::item {
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #e0e0e0;
            }
        """)
        
        # Initialize database with thread-safe session factory
        engine = init_db()
        session_factory = sessionmaker(bind=engine)
        self.Session = scoped_session(session_factory)
        self.session = self.Session()
        
        # Create default users if they don't exist
        try:
            create_default_users(self.session)
        except Exception as e:
            logger.warning(f"Could not create default users: {e}")
        
        # Reload permissions to ensure fresh data
        from utils.permissions import get_permissions_manager
        permissions_manager = get_permissions_manager()
        permissions_manager.reload_permissions()
        
        # Show login dialog
        if not self.show_login():
            sys.exit(0)
        
        try:
            # Create central widget and layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Create tab widget
            self.tab_widget = QTabWidget()
            
            # Create and add tabs
            self.customers_tab = CustomersTab(self.session, self.current_user)
            self.products_tab = ProductsTab(self.session, self.current_user)
            self.items_tab = ItemsTab(self.session, self.current_user)
            self.orders_tab = OrdersTab(self.session, self.current_user)
            self.order_items_tab = OrderItemsTab(self.session, self.current_user)
            self.employees_tab = EmployeesTab(self.session, self.current_user)
            self.labels_tab = LabelsTab(self.session, self.current_user)
            self.production_plans_tab = ProductionPlansTab(self.session, self.current_user)
            self.reports_tab = ReportsTab(self.session, self.current_user)
            self.components_tab = ComponentsTab(self.session, self.current_user)
            self.stock_tab = StockTab(self.session, self.current_user)
            
            # Import tab will be created when needed from Settings menu
            
            # Connect items tab signals to refresh labels when items are updated
            self.items_tab.item_updated.connect(self.labels_tab.refresh_all_items)
            
            # Connect tab switching signals to refresh labels when items are updated
            self.tab_widget.currentChanged.connect(self.on_tab_changed)
            
            # Add tabs based on user permissions
            self.add_tabs_based_on_permissions()
            
            layout.addWidget(self.tab_widget)
            
            # Create menu bar with Settings
            self.create_menu_bar()
            
            # Update window title with user info
            role_name = get_role_display_name(self.current_user.role)
            self.setWindowTitle(f"Orders Management System - {self.current_user.username} ({role_name})")
            
            logger.debug("UI initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing UI: {e}")
            QMessageBox.critical(None, "UI Error", f"Could not initialize user interface: {str(e)}")
            sys.exit(1)
        
        # Schedule the popup check after the window is shown
        QTimer.singleShot(2000, self.check_upcoming_events)  # 2 second delay
    
    def show_login(self):
        """Show login dialog and return True if login successful"""
        login_dialog = LoginDialog(self.session, self)
        if login_dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_user = login_dialog.get_user()
            return True
        return False
    
    def add_tabs_based_on_permissions(self):
        """Add tabs based on user permissions"""
        logger.debug(f"Adding tabs for user: {self.current_user.username} with role: {self.current_user.role.value}")
        
        if self.current_user.can_access_tab('customers'):
            logger.debug("Adding customers tab")
            self.tab_widget.addTab(self.customers_tab, "Customers")
        
        if self.current_user.can_access_tab('products'):
            logger.debug("Adding products tab")
            self.tab_widget.addTab(self.products_tab, "Products")
        
        if self.current_user.can_access_tab('items'):
            logger.debug("Adding items tab")
            self.tab_widget.addTab(self.items_tab, "Items")
        
        if self.current_user.can_access_tab('orders'):
            logger.debug("Adding orders tab")
            self.tab_widget.addTab(self.orders_tab, "Orders")
            self.tab_widget.addTab(self.order_items_tab, "Order Items")
        
        if self.current_user.can_access_tab('employees'):
            logger.debug("Adding employees tab")
            self.tab_widget.addTab(self.employees_tab, "Employees")
        
        # Import tab moved to Settings menu
        
        if self.current_user.can_access_tab('labels'):
            logger.debug("Adding labels tab")
            self.tab_widget.addTab(self.labels_tab, "Labels")
        
        if self.current_user.can_access_tab('production_plans'):
            logger.debug("Adding production plans tab")
            self.tab_widget.addTab(self.production_plans_tab, "Production Plans")
        
        if self.current_user.can_access_tab('reports'):
            logger.debug("Adding reports tab")
            self.tab_widget.addTab(self.reports_tab, "Reports")
        
        if self.current_user.can_access_tab('components'):
            logger.debug("Adding components tab")
            self.tab_widget.addTab(self.components_tab, "Components")
        
        if self.current_user.can_access_tab('stock'):
            logger.debug("Adding stock tab")
            self.tab_widget.addTab(self.stock_tab, "Stock")
        else:
            logger.debug(f"User cannot access stock tab. can_access_tab('stock') returned: {self.current_user.can_access_tab('stock')}")
            logger.debug(f"User role: {self.current_user.role.value}")
            
            # Check permissions manager directly
            from utils.permissions import get_permissions_manager
            pm = get_permissions_manager()
            logger.debug(f"Permissions manager tab_access: {pm.permissions_data.get('tab_access', {})}")
            logger.debug(f"User visible tabs: {pm.get_visible_tabs(self.current_user)}")
            logger.debug(f"Stock tab access for admin: {'admin' in pm.permissions_data.get('tab_access', {}).get('stock', [])}")
    
    def on_tab_changed(self, index):
        """Handle tab switching - refresh labels tab when it becomes active"""
        current_widget = self.tab_widget.widget(index)
        if current_widget == self.labels_tab:
            # Refresh items in labels tab when it becomes active
            self.labels_tab.refresh_all_items()
    
    def check_upcoming_events(self):
        # Switch to employees tab and check for events
        if self.current_user.can_access_tab('employees'):
            self.tab_widget.setCurrentWidget(self.employees_tab)
            self.employees_tab.check_upcoming_events()

    def create_menu_bar(self):
        """Create the menu bar with Help options only"""
        menubar = self.menuBar()
        print("=== Creating menu bar ===")
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        print("Added Help menu")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        print("Added About action to Help menu")
        
        # Also add a toolbar with Settings button
        toolbar = self.addToolBar("Main Toolbar")
        print("Created toolbar")
        
        # Apply blue theme styling throughout the application with black text
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fbff;
            }
            QMenuBar {
                background-color: #e6f3ff;
                border-bottom: 1px solid #b3d9ff;
                color: #000000;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
                color: #000000;
            }
            QMenuBar::item:selected {
                background-color: #d0e3ff;
                border-radius: 3px;
            }
            QMenu {
                background-color: #f0f8ff;
                border: 1px solid #b3d9ff;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #000000;
            }
            QMenu::item:selected {
                background-color: #d0e3ff;
            }
            QTabWidget::pane {
                border: 1px solid #b3d9ff;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #e6f3ff;
                border: 1px solid #b3d9ff;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 14px;
                font-weight: bold;
                color: #000000;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 1px solid #ffffff;
                color: #000000;
            }
            QTabBar::tab:hover {
                background-color: #d0e3ff;
            }
            QToolBar {
                background-color: #e6f3ff;
                border-bottom: 1px solid #b3d9ff;
                padding: 4px;
            }
            QToolBar QToolButton {
                font-size: 14px;
                font-weight: bold;
                padding: 4px 8px;
                background-color: #f0f8ff;
                border: 1px solid #cce0ff;
                border-radius: 3px;
                color: #000000;
            }
            QToolBar QToolButton:hover {
                background-color: #d0e3ff;
                border: 1px solid #b3d9ff;
            }
            QPushButton {
                background-color: #e6f3ff;
                border: 1px solid #b3d9ff;
                border-radius: 4px;
                padding: 6px 12px;
                color: #000000;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0e3ff;
                border: 1px solid #a3c9ff;
            }
            QPushButton:pressed {
                background-color: #b3d9ff;
                border: 1px solid #8ac0ff;
            }
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fbff;
                gridline-color: #e6f3ff;
                border: 1px solid #b3d9ff;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f8ff;
            }
            QTableWidget::item:selected {
                background-color: #d0e3ff;
                color: #000000;
            }
            /* Allow individual item backgrounds to override global styling */
            QTableWidget::item[background] {
                background-color: attr(background);
            }
            /* Allow text colors to be set programmatically */
            QTableWidget::item[color] {
                color: attr(color);
            }
            QHeaderView::section {
                background-color: #e6f3ff;
                border: 1px solid #b3d9ff;
                padding: 6px;
                font-weight: bold;
                color: #000000;
            }
            QHeaderView::section:hover {
                background-color: #d0e3ff;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #b3d9ff;
                border-radius: 3px;
                padding: 4px;
                color: #000000;
            }
            QLineEdit:focus {
                border: 2px solid #8ac0ff;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #b3d9ff;
                border-radius: 3px;
                padding: 4px;
                color: #000000;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #e6f3ff;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #000000;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #b3d9ff;
                border-radius: 3px;
                padding: 4px;
                color: #000000;
            }
            QTextEdit, QPlainTextEdit {
                background-color: #ffffff;
                border: 1px solid #b3d9ff;
                border-radius: 3px;
                padding: 4px;
                color: #000000;
            }
            QGroupBox {
                font-weight: bold;
                color: #000000;
                border: 1px solid #b3d9ff;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                background-color: #f8fbff;
            }
            QLabel {
                color: #000000;
            }
            QCheckBox {
                color: #000000;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #b3d9ff;
                border-radius: 2px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #2c5aa0;
                border: 1px solid #1e3a8a;
            }
            QRadioButton {
                color: #000000;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #b3d9ff;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QRadioButton::indicator:checked {
                background-color: #2c5aa0;
                border: 1px solid #1e3a8a;
            }
            QScrollBar:vertical {
                background-color: #f0f8ff;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #b3d9ff;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #8ac0ff;
            }
            QScrollBar:horizontal {
                background-color: #f0f8ff;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #b3d9ff;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #8ac0ff;
            }
        """)
        
        settings_toolbar_action = QAction("Settings", self)
        settings_toolbar_action.triggered.connect(self._show_settings)
        toolbar.addAction(settings_toolbar_action)
        print("Added Settings button to toolbar")
        
        # Add Import Data button to toolbar
        if self.current_user.can_access_tab('import'):
            import_toolbar_action = QAction("Import Data", self)
            import_toolbar_action.triggered.connect(self._show_import_dialog)
            toolbar.addAction(import_toolbar_action)
            print("Added Import Data button to toolbar")
        
        # Add Permissions button to toolbar for admin users
        if self.current_user.role == UserRole.ADMIN:
            permissions_toolbar_action = QAction("Permissions", self)
            permissions_toolbar_action.triggered.connect(self._show_permissions)
            toolbar.addAction(permissions_toolbar_action)
            print("Added Permissions button to toolbar")
            
            # Add Database Management button to toolbar for admin users
            db_management_toolbar_action = QAction("Database", self)
            db_management_toolbar_action.triggered.connect(self._show_database_management)
            toolbar.addAction(db_management_toolbar_action)
            print("Added Database Management button to toolbar")
            
                    # Add User Management button to toolbar for users with manage_users permission
        if self.current_user.has_permission('manage_users'):
            user_management_toolbar_action = QAction("User Management", self)
            user_management_toolbar_action.triggered.connect(self._show_user_management)
            toolbar.addAction(user_management_toolbar_action)
            print("Added User Management button to toolbar")
        
        print("=== Menu bar creation completed ===")
    
    def _show_settings(self):
        """Show settings dialog (admin only)"""
        if self.current_user and self.current_user.has_permission('view_settings'):
            dialog = SettingsDialog(self.session, self, self.current_user)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                QMessageBox.information(
                    self,
                    "Restart Required",
                    "Database settings have been changed. Please restart the application for changes to take effect."
                )
        else:
            QMessageBox.warning(self, "Access Denied", "You don't have permission to access settings.")
    
    def _show_permissions(self):
        """Show permissions management dialog (admin only)"""
        try:
            dialog = PermissionsDialog(self)
            dialog.permissions_updated.connect(self._on_permissions_updated)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing permissions dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not open permissions: {str(e)}")
    
    def _on_permissions_updated(self):
        """Handle permissions update"""
        try:
            from utils.permissions import reload_permissions
            reload_permissions()
            QMessageBox.information(self, "Permissions Updated", 
                                  "Permissions have been updated. Please restart the application for changes to take effect.")
        except Exception as e:
            logger.error(f"Error updating permissions: {e}")
    
    def _show_database_management(self):
        """Show database management dialog (admin only)"""
        try:
            dialog = DatabaseManagementDialog(self.session, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing database management dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not open database management: {str(e)}")
    
    def _show_import_dialog(self):
        """Show import data dialog"""
        try:
            from views.dialogs.import_dialog import ImportDialog
            dialog = ImportDialog(self.session, self.current_user, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing import dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not open import dialog: {str(e)}")
    
    def _show_user_management(self):
        """Show user management dialog (users with manage_users permission)"""
        try:
            from views.dialogs.user_management_dialog import UserManagementDialog
            dialog = UserManagementDialog(self.session, self)
            dialog.current_user = self.current_user  # Pass current user for permission checks
            dialog.user_updated.connect(self._on_user_updated)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing user management dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not open user management: {str(e)}")
    
    def _on_user_updated(self):
        """Handle user update"""
        try:
            QMessageBox.information(self, "User Updated", 
                                  "User information has been updated successfully.")
        except Exception as e:
            logger.error(f"Error handling user update: {e}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", "Orders Management System v1.0")
    
    def closeEvent(self, event):
        # Properly close the session when the application exits
        if self.session:
            self.session.close()
            self.Session.remove()
        super().closeEvent(event)

def main():
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        QMessageBox.critical(None, "Error", f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1) 