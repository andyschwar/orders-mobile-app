from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QDateEdit, QComboBox, QLabel, QHeaderView, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, date, timedelta
import pandas as pd
import os
from pathlib import Path

class LabelLogsTab(QWidget):
    def __init__(self, session: Session, user=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.setup_ui()
        self.refresh_data()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Create toolbar
        toolbar = QHBoxLayout()
        
        # Export to Excel button
        export_button = QPushButton("Export to Excel")
        export_button.clicked.connect(self.export_to_excel)
        toolbar.addWidget(export_button)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_button)
        
        # Add search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search label logs...")
        self.search_input.textChanged.connect(self.search_logs)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Filter section
        filter_layout = QHBoxLayout()
        
        # Date range filter
        date_layout = QVBoxLayout()
        date_label = QLabel("Date Range:")
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))  # Last 30 days
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(self.end_date)
        filter_layout.addLayout(date_layout)
        
        # Customer filter
        customer_layout = QVBoxLayout()
        customer_label = QLabel("Customer:")
        self.customer_filter = QComboBox()
        self.customer_filter.addItem("All Customers", None)
        self.customer_filter.currentIndexChanged.connect(self.apply_filters)
        customer_layout.addWidget(customer_label)
        customer_layout.addWidget(self.customer_filter)
        filter_layout.addLayout(customer_layout)
        
        # Printed by filter
        printed_by_layout = QVBoxLayout()
        printed_by_label = QLabel("Printed By:")
        self.printed_by_filter = QComboBox()
        self.printed_by_filter.addItem("All Users", None)
        self.printed_by_filter.currentIndexChanged.connect(self.apply_filters)
        printed_by_layout.addWidget(printed_by_label)
        printed_by_layout.addWidget(self.printed_by_filter)
        filter_layout.addLayout(printed_by_layout)
        
        # Apply filters button
        apply_filters_button = QPushButton("Apply Filters")
        apply_filters_button.clicked.connect(self.apply_filters)
        filter_layout.addWidget(apply_filters_button)
        
        layout.addLayout(filter_layout)
        
        # Table setup
        self.table = QTableWidget()
        self.setup_table()
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def setup_table(self):
        """Setup the table columns and properties"""
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Customer",
            "Order Number",
            "Item Code",
            "Item Name",
            "Quantity",
            "Printed Quantity",
            "Barcodes Included",
            "Printed By",
            "Printed At",
            "PDF File",
            "Notes"
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 50)   # ID
        self.table.setColumnWidth(1, 150)  # Customer
        self.table.setColumnWidth(2, 120)  # Order Number
        self.table.setColumnWidth(3, 100)  # Item Code
        self.table.setColumnWidth(4, 200)  # Item Name
        self.table.setColumnWidth(5, 80)   # Quantity
        self.table.setColumnWidth(6, 100) # Printed Quantity
        self.table.setColumnWidth(7, 120) # Barcodes Included
        self.table.setColumnWidth(8, 100) # Printed By
        self.table.setColumnWidth(9, 120) # Printed At
        self.table.setColumnWidth(10, 200) # PDF File
        self.table.setColumnWidth(11, 150) # Notes
        
        # Make table read-only
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Connect double-click to open PDF
        self.table.cellDoubleClicked.connect(self.open_pdf)
    
    def refresh_data(self):
        """Refresh the data from database"""
        try:
            from models.database import LabelLog
            
            # Load filter options
            self.load_filter_options()
            
            # Get all label logs
            logs = self.session.query(LabelLog).order_by(desc(LabelLog.printed_at)).all()
            self.populate_table(logs)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load label logs: {str(e)}")
    
    def load_filter_options(self):
        """Load options for filter dropdowns"""
        try:
            from models.database import LabelLog
            
            # Load customers
            customers = self.session.query(LabelLog.customer_name_index).distinct().all()
            self.customer_filter.clear()
            self.customer_filter.addItem("All Customers", None)
            for customer in customers:
                self.customer_filter.addItem(customer[0], customer[0])
            
            # Load users
            users = self.session.query(LabelLog.printed_by).distinct().all()
            self.printed_by_filter.clear()
            self.printed_by_filter.addItem("All Users", None)
            for user in users:
                if user[0]:  # Skip None values
                    self.printed_by_filter.addItem(user[0], user[0])
                    
        except Exception as e:
            print(f"Error loading filter options: {e}")
    
    def populate_table(self, logs):
        """Populate the table with label logs"""
        self.table.setRowCount(len(logs))
        
        for i, log in enumerate(logs):
            self.table.setItem(i, 0, QTableWidgetItem(str(log.id)))
            self.table.setItem(i, 1, QTableWidgetItem(f"{log.customer_name_index} - {log.customer_name}"))
            self.table.setItem(i, 2, QTableWidgetItem(log.order_number))
            self.table.setItem(i, 3, QTableWidgetItem(log.item_code))
            self.table.setItem(i, 4, QTableWidgetItem(log.item_name))
            self.table.setItem(i, 5, QTableWidgetItem(str(log.quantity)))
            self.table.setItem(i, 6, QTableWidgetItem(str(log.printed_quantity)))
            self.table.setItem(i, 7, QTableWidgetItem("Yes" if log.barcodes_included else "No"))
            self.table.setItem(i, 8, QTableWidgetItem(log.printed_by or "Unknown"))
            self.table.setItem(i, 9, QTableWidgetItem(log.printed_at.strftime("%Y-%m-%d %H:%M") if log.printed_at else ""))
            self.table.setItem(i, 10, QTableWidgetItem(log.pdf_filename or ""))
            self.table.setItem(i, 11, QTableWidgetItem(log.notes or ""))
    
    def search_logs(self):
        """Search logs based on search input"""
        search_text = self.search_input.text().lower()
        if not search_text:
            self.refresh_data()
            return
        
        try:
            from models.database import LabelLog
            
            # Search in multiple fields
            logs = self.session.query(LabelLog).filter(
                or_(
                    LabelLog.customer_name.ilike(f"%{search_text}%"),
                    LabelLog.order_number.ilike(f"%{search_text}%"),
                    LabelLog.item_code.ilike(f"%{search_text}%"),
                    LabelLog.item_name.ilike(f"%{search_text}%"),
                    LabelLog.printed_by.ilike(f"%{search_text}%")
                )
            ).order_by(desc(LabelLog.printed_at)).all()
            
            self.populate_table(logs)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Search failed: {str(e)}")
    
    def apply_filters(self):
        """Apply date range and other filters"""
        try:
            from models.database import LabelLog
            
            # Build filter conditions
            filters = []
            
            # Date range filter
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()
            filters.append(LabelLog.printed_at >= datetime.combine(start_date, datetime.min.time()))
            filters.append(LabelLog.printed_at <= datetime.combine(end_date, datetime.max.time()))
            
            # Customer filter
            customer_filter = self.customer_filter.currentData()
            if customer_filter:
                filters.append(LabelLog.customer_name_index == customer_filter)
            
            # Printed by filter
            printed_by_filter = self.printed_by_filter.currentData()
            if printed_by_filter:
                filters.append(LabelLog.printed_by == printed_by_filter)
            
            # Query with filters
            logs = self.session.query(LabelLog).filter(and_(*filters)).order_by(desc(LabelLog.printed_at)).all()
            self.populate_table(logs)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Filter failed: {str(e)}")
    
    def open_pdf(self, row, column):
        """Open PDF file when double-clicked"""
        try:
            pdf_filename = self.table.item(row, 10).text()  # PDF File column
            if pdf_filename and os.path.exists(pdf_filename):
                QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_filename))
            else:
                QMessageBox.warning(self, "File Not Found", f"PDF file not found: {pdf_filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open PDF: {str(e)}")
    
    def export_to_excel(self):
        """Export label logs to Excel"""
        try:
            # Get current filtered data
            from models.database import LabelLog
            
            # Build filter conditions (same as apply_filters)
            filters = []
            
            # Date range filter
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()
            filters.append(LabelLog.printed_at >= datetime.combine(start_date, datetime.min.time()))
            filters.append(LabelLog.printed_at <= datetime.combine(end_date, datetime.max.time()))
            
            # Customer filter
            customer_filter = self.customer_filter.currentData()
            if customer_filter:
                filters.append(LabelLog.customer_name_index == customer_filter)
            
            # Printed by filter
            printed_by_filter = self.printed_by_filter.currentData()
            if printed_by_filter:
                filters.append(LabelLog.printed_by == printed_by_filter)
            
            # Query with filters
            logs = self.session.query(LabelLog).filter(and_(*filters)).order_by(desc(LabelLog.printed_at)).all()
            
            if not logs:
                QMessageBox.information(self, "No Data", "No label logs found to export.")
                return
            
            # Create DataFrame
            data = []
            for log in logs:
                data.append({
                    'ID': log.id,
                    'Customer': f"{log.customer_name_index} - {log.customer_name}",
                    'Order Number': log.order_number,
                    'Item Code': log.item_code,
                    'Item Name': log.item_name,
                    'Quantity': log.quantity,
                    'Printed Quantity': log.printed_quantity,
                    'Barcodes Included': "Yes" if log.barcodes_included else "No",
                    'Item Barcode': log.item_barcode or "",
                    'Order Barcode': log.order_barcode or "",
                    'Quantity Barcode': log.quantity_barcode or "",
                    'Printed By': log.printed_by or "Unknown",
                    'Printed At': log.printed_at.strftime("%Y-%m-%d %H:%M:%S") if log.printed_at else "",
                    'PDF File': log.pdf_filename or "",
                    'Notes': log.notes or ""
                })
            
            df = pd.DataFrame(data)
            
            # Get export filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"label_logs_export_{timestamp}.xlsx"
            
            # Save to Excel
            export_dir = os.path.join(str(Path.home()), "Documents", "OrdersApp", "exports")
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)
            
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            QMessageBox.information(self, "Export Successful", f"Label logs exported to:\n{filepath}")
            
            # Open the exported file
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Could not export to Excel: {str(e)}")
