from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QSpinBox,
    QMessageBox
)
from PyQt6.QtCore import Qt

class BoxSplitDialog(QDialog):
    def __init__(self, item_name, total_quantity, parent=None):
        super().__init__(parent)
        self.item_name = item_name
        self.total_quantity = total_quantity
        self.boxes = []  # List to store box quantities
        
        self.setWindowTitle("Split Into Boxes")
        self.setModal(True)
        self.resize(400, 300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Add header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(f"Item: {self.item_name}"))
        header_layout.addWidget(QLabel(f"Total Quantity: {self.total_quantity}"))
        layout.addLayout(header_layout)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Box #", "Quantity"])
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 100)
        layout.addWidget(self.table)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        add_box_button = QPushButton("Add Box")
        add_box_button.clicked.connect(self.add_box)
        button_layout.addWidget(add_box_button)
        
        remove_box_button = QPushButton("Remove Box")
        remove_box_button.clicked.connect(self.remove_box)
        button_layout.addWidget(remove_box_button)
        
        button_layout.addStretch()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # Add remaining quantity label
        self.remaining_label = QLabel(f"Remaining: {self.total_quantity}")
        layout.addWidget(self.remaining_label)
        
        self.setLayout(layout)
        
        # Add first box by default
        self.add_box()
        
    def add_box(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Box number
        box_num = QTableWidgetItem(str(row + 1))
        box_num.setFlags(box_num.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, box_num)
        
        # Quantity spinner
        quantity_spinner = QSpinBox()
        quantity_spinner.setMinimum(1)
        quantity_spinner.setMaximum(self.total_quantity)
        quantity_spinner.setValue(1)  # Start with 1 instead of remaining quantity
        quantity_spinner.valueChanged.connect(self.update_remaining)
        self.table.setCellWidget(row, 1, quantity_spinner)
        
        self.update_remaining()
        
    def remove_box(self):
        if self.table.rowCount() > 1:  # Keep at least one box
            self.table.removeRow(self.table.rowCount() - 1)
            self.update_remaining()
            
    def calculate_remaining(self):
        total_allocated = 0
        for row in range(self.table.rowCount()):
            spinner = self.table.cellWidget(row, 1)
            if spinner:
                total_allocated += spinner.value()
        return self.total_quantity - total_allocated
        
    def update_remaining(self):
        remaining = self.calculate_remaining()
        self.remaining_label.setText(f"Remaining: {remaining}")
        
        # Update maximum values for all spinners
        for row in range(self.table.rowCount()):
            spinner = self.table.cellWidget(row, 1)
            if spinner:
                current_value = spinner.value()
                max_value = current_value + remaining
                spinner.setMaximum(max_value)
        
        # Update color based on remaining quantity
        if remaining < 0:
            self.remaining_label.setStyleSheet("color: red;")
        elif remaining == 0:
            self.remaining_label.setStyleSheet("color: green;")
        else:
            self.remaining_label.setStyleSheet("color: black;")
        
    def validate_and_accept(self):
        remaining = self.calculate_remaining()
        if remaining != 0:
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Please allocate all quantities. Remaining: {remaining}\n\n"
                f"Total quantity: {self.total_quantity}\n"
                f"Allocated: {self.total_quantity - remaining}"
            )
            return
            
        # Store box quantities
        self.boxes = []
        for row in range(self.table.rowCount()):
            spinner = self.table.cellWidget(row, 1)
            if spinner:
                self.boxes.append(spinner.value())
        
        self.accept()
        
    def get_box_quantities(self):
        return self.boxes 