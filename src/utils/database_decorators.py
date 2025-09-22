import logging
import functools
from PyQt6.QtWidgets import QMessageBox
from sqlalchemy.exc import OperationalError, DisconnectionError, TimeoutError

logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection before operations"""
    try:
        from models.database import get_session_with_retry
        from sqlalchemy import text
        with get_session_with_retry(max_retries=1, retry_delay=1) as test_session:
            # Simple connection test
            test_session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def with_connection_test(func):
    """
    Decorator that tests database connection before executing the function.
    Shows user-friendly error message if connection fails.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Test connection before proceeding
        if not test_database_connection():
            # Get the parent widget for showing the message box
            parent = None
            if args and hasattr(args[0], 'parent'):
                parent = args[0].parent()
            elif args and hasattr(args[0], 'window'):
                parent = args[0].window()
            
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Database Connection Error")
            msg_box.setText("Connection Lost")
            msg_box.setInformativeText(
                "The database connection has been lost.\n\n"
                "This usually happens when the application has been idle for too long.\n\n"
                "Please restart the application to reconnect."
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return None
        
        # Connection is good, proceed with the function
        return func(*args, **kwargs)
    
    return wrapper

def handle_database_errors(func):
    """
    Decorator to handle database errors gracefully in UI components.
    This decorator catches database connection errors and shows user-friendly messages
    instead of crashing the application.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OperationalError, DisconnectionError, TimeoutError) as e:
            error_msg = str(e)
            
            # Get the parent widget for showing the message box
            parent = None
            if args and hasattr(args[0], 'parent'):
                parent = args[0].parent()
            elif args and hasattr(args[0], 'window'):
                parent = args[0].window()
            
            # Show user-friendly error message
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Database Connection Error")
            msg_box.setText("Connection Lost")
            msg_box.setInformativeText(
                "The database connection has been lost.\n\n"
                "This usually happens when the application has been idle for too long.\n\n"
                "Please restart the application to reconnect."
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            # Add detailed information
            msg_box.setDetailedText(
                f"Technical details:\n{error_msg}\n\n"
                "To resolve this issue:\n"
                "1. Close this application completely\n"
                "2. Wait a few seconds\n"
                "3. Restart the application\n\n"
                "If the problem persists, please contact your system administrator."
            )
            
            msg_box.exec()
            
            # Log the error for debugging
            logger.error(f"Database error in {func.__name__}: {error_msg}")
            
        except Exception as e:
            # Handle other unexpected errors
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            
            # Get the parent widget for showing the message box
            parent = None
            if args and hasattr(args[0], 'parent'):
                parent = args[0].parent()
            elif args and hasattr(args[0], 'window'):
                parent = args[0].window()
            
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Application Error")
            msg_box.setText("An unexpected error occurred")
            msg_box.setInformativeText(
                f"An unexpected error occurred while performing this operation.\n\n"
                f"Error: {str(e)}\n\n"
                f"Please restart the application if the problem persists."
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()
    
    return wrapper


def safe_database_operation(error_message="An error occurred while accessing the database."):
    """
    Decorator factory for safe database operations with custom error messages.
    
    Usage:
        @safe_database_operation("Failed to load customers")
        def load_customers(self):
            # database operation here
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (OperationalError, DisconnectionError, TimeoutError) as e:
                # Get the parent widget for showing the message box
                parent = None
                if args and hasattr(args[0], 'parent'):
                    parent = args[0].parent()
                elif args and hasattr(args[0], 'window'):
                    parent = args[0].window()
                
                msg_box = QMessageBox(parent)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Database Error")
                msg_box.setText("Operation Failed")
                msg_box.setInformativeText(error_message)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
                msg_box.exec()
                
                logger.error(f"Database error in {func.__name__}: {e}")
                
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                
                # Get the parent widget for showing the message box
                parent = None
                if args and hasattr(args[0], 'parent'):
                    parent = args[0].parent()
                elif args and hasattr(args[0], 'window'):
                    parent = args[0].window()
                
                msg_box = QMessageBox(parent)
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText("An unexpected error occurred")
                msg_box.setInformativeText(str(e))
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
                msg_box.exec()
        
        return wrapper
    return decorator

