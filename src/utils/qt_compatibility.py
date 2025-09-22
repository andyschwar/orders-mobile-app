"""
Qt Compatibility Layer
Automatically handles PyQt6/PyQt5 compatibility
"""

import sys

# Try PyQt6 first, fall back to PyQt5
try:
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
    from PyQt6.QtPrintSupport import *
    QT_VERSION = 6
    print("[DEBUG] Using PyQt6")
except ImportError as e:
    print(f"[DEBUG] PyQt6 import failed: {e}")
    try:
        from PyQt6.QtWidgets import *
        from PyQt6.QtCore import *
        from PyQt6.QtGui import *
        from PyQt6.QtPrintSupport import *
        QT_VERSION = 5
        print("[DEBUG] Using PyQt5")
    except ImportError as e2:
        print(f"[DEBUG] PyQt5 import failed: {e2}")
        raise ImportError("Neither PyQt6 nor PyQt5 could be imported. Please install one of them.")

# Handle differences between PyQt5 and PyQt6
if QT_VERSION == 5:
    # PyQt5 compatibility fixes
    try:
        # Some PyQt6 features might not exist in PyQt5
        if not hasattr(Qt, 'CheckState'):
            # Create a simple CheckState enum for PyQt5
            class CheckState:
                Unchecked = 0
                PartiallyChecked = 1
                Checked = 2
            Qt.CheckState = CheckState()
    except:
        pass

def get_qt_version():
    """Return the Qt version being used"""
    return QT_VERSION

def is_pyqt6():
    """Check if PyQt6 is being used"""
    return QT_VERSION == 6

def is_pyqt5():
    """Check if PyQt5 is being used"""
    return QT_VERSION == 5

# Convenience functions for common imports
def get_qapplication():
    """Get QApplication class"""
    if QT_VERSION == 6:
        from PyQt6.QtWidgets import QApplication
    else:
        from PyQt6.QtWidgets import QApplication
    return QApplication

def get_qaction():
    """Get QAction class"""
    if QT_VERSION == 6:
        from PyQt6.QtGui import QAction
    else:
        from PyQt6.QtGui import QAction
    return QAction

def get_qdesktopservices():
    """Get QDesktopServices class"""
    if QT_VERSION == 6:
        from PyQt6.QtCore import QDesktopServices
    else:
        from PyQt6.QtCore import QDesktopServices
    return QDesktopServices
