import logging
import time
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from sqlalchemy.exc import OperationalError, DisconnectionError, TimeoutError
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseConnectionManager(QObject):
    """Manages database connections and handles timeouts gracefully"""
    
    connection_lost = pyqtSignal(str)  # Signal emitted when connection is lost
    connection_restored = pyqtSignal()  # Signal emitted when connection is restored
    
    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.last_activity = datetime.now()
        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.check_connection_health)
        self.connection_check_timer.start(30000)  # Check every 30 seconds
        self.is_connection_healthy = True
        
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = datetime.now()
        
    def check_connection_health(self):
        """Check if the database connection is still healthy"""
        try:
            # Create a test session
            session = self.session_factory()
            
            # Try a simple query
            session.execute(text("SELECT 1"))
            session.close()
            
            # If we get here, connection is healthy
            if not self.is_connection_healthy:
                self.is_connection_healthy = True
                self.connection_restored.emit()
                logger.info("Database connection restored")
                
        except Exception as e:
            if self.is_connection_healthy:
                self.is_connection_healthy = False
                self.connection_lost.emit(str(e))
                logger.warning(f"Database connection lost: {e}")
    
    def is_connection_stale(self):
        """Check if connection has been idle for too long"""
        idle_time = datetime.now() - self.last_activity
        return idle_time > timedelta(minutes=30)  # Consider stale after 30 minutes
    
    @contextmanager
    def get_session(self):
        """Get a database session with error handling"""
        session = None
        try:
            # Check if connection is stale
            if self.is_connection_stale():
                raise OperationalError("Connection has been idle for too long", None, None)
            
            session = self.session_factory()
            self.update_activity()
            yield session
            
        except (OperationalError, DisconnectionError, TimeoutError) as e:
            error_msg = str(e)
            
            # Handle specific connection errors
            if "server closed the connection" in error_msg.lower():
                self._show_connection_error("Database connection was closed by the server.\n\nThis usually happens when the application has been idle for too long.")
            elif "connection" in error_msg.lower() and "timeout" in error_msg.lower():
                self._show_connection_error("Database connection timed out.\n\nThis usually happens when the application has been idle for too long.")
            elif "idle for too long" in error_msg:
                self._show_connection_error("Database connection has been idle for too long.\n\nPlease restart the application to reconnect.")
            else:
                self._show_connection_error(f"Database connection error:\n\n{error_msg}\n\nPlease restart the application.")
            
            raise
            
        except Exception as e:
            # For other errors, show a generic message
            self._show_generic_error(f"An unexpected error occurred:\n\n{str(e)}\n\nPlease restart the application.")
            raise
            
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass
    
    def _show_connection_error(self, message):
        """Show a user-friendly connection error dialog"""
        try:
            # Get the main application window
            app = QApplication.instance()
            if app and app.activeWindow():
                parent = app.activeWindow()
            else:
                parent = None
            
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Database Connection Error")
            msg_box.setText("Connection Lost")
            msg_box.setInformativeText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            # Add restart instructions
            msg_box.setDetailedText(
                "To resolve this issue:\n\n"
                "1. Close this application completely\n"
                "2. Wait a few seconds\n"
                "3. Restart the application\n\n"
                "If the problem persists, please contact your system administrator."
            )
            
            msg_box.exec()
            
        except Exception as e:
            logger.error(f"Error showing connection error dialog: {e}")
    
    def _show_generic_error(self, message):
        """Show a generic error dialog"""
        try:
            app = QApplication.instance()
            if app and app.activeWindow():
                parent = app.activeWindow()
            else:
                parent = None
            
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Application Error")
            msg_box.setText("An error occurred")
            msg_box.setInformativeText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            msg_box.exec()
            
        except Exception as e:
            logger.error(f"Error showing generic error dialog: {e}")
    
    def cleanup(self):
        """Clean up the connection manager"""
        if self.connection_check_timer:
            self.connection_check_timer.stop()


def create_database_manager(session_factory):
    """Create a database connection manager"""
    return DatabaseConnectionManager(session_factory)


def safe_database_operation(func):
    """Decorator to safely execute database operations"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OperationalError, DisconnectionError, TimeoutError) as e:
            # Let the database manager handle the error
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise
    return wrapper

