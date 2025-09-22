from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QMessageBox, QHeaderView, QDialog, QFormLayout,
    QDoubleSpinBox, QComboBox, QTextEdit, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session
from models.database import Material

class MaterialDialog(QDialog):
    def __init__(self, session: Session, material=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.material = material
        self.setWindowTitle("Edit Material" if material else "Add Material")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
        if material:
            self.populate_fields()
    
    def init_ui(self):
        layout = QFormLayout()
        
        # Basic information
        self.name = QLineEdit()
        self.material_type = QComboBox()
        self.material_type.setEditable(True)
        self.material_type.addItems(["Steel", "Aluminum", "Brass", "Copper", "Stainless Steel", "Plastic"])
        
        self.shape = QComboBox()
        self.shape.setEditable(True)
        self.shape.addItems(["Hexagon", "Round", "Square", "Flat", "Rectangle", "Tube"])
        
        self.size = QLineEdit()
        self.length = QDoubleSpinBox()
        self.length.setDecimals(0)
        self.length.setMaximum(10000.0)
        self.length.setSuffix(" mm")
        
        # Pricing information
        self.price_per_kg = QDoubleSpinBox()
        self.price_per_kg.setDecimals(2)
        self.price_per_kg.setMaximum(10000.0)
        self.price_per_kg.setSuffix(" CZK/kg")
        
        self.weight_per_meter = QDoubleSpinBox()
        self.weight_per_meter.setDecimals(3)
        self.weight_per_meter.setMaximum(100.0)
        self.weight_per_meter.setSuffix(" kg/m")
        
        self.supplier = QLineEdit()
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        
        # Price per meter display
        self.price_per_meter_label = QLabel("0.00 CZK/m")
        self.price_per_meter_label.setStyleSheet("font-weight: bold; color: blue;")
        
        # Add fields to layout
        layout.addRow("Name:", self.name)
        layout.addRow("Material Type:", self.material_type)
        layout.addRow("Shape:", self.shape)
        layout.addRow("Size:", self.size)
        layout.addRow("Standard Length:", self.length)
        layout.addRow("Price per kg:", self.price_per_kg)
        layout.addRow("Weight per meter:", self.weight_per_meter)
        layout.addRow("Price per meter:", self.price_per_meter_label)
        layout.addRow("Supplier:", self.supplier)
        layout.addRow("Notes:", self.notes)
        
        # Connect price calculation
        self.price_per_kg.valueChanged.connect(self.update_price_per_meter)
        self.weight_per_meter.valueChanged.connect(self.update_price_per_meter)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_material)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
        
        self.update_price_per_meter()
    
    def populate_fields(self):
        if self.material:
            self.name.setText(self.material.name or "")
            self.material_type.setCurrentText(self.material.material_type or "")
            self.shape.setCurrentText(self.material.shape or "")
            self.size.setText(self.material.size or "")
            self.length.setValue(self.material.length or 0.0)
            self.price_per_kg.setValue(self.material.price_per_kg or 0.0)
            self.weight_per_meter.setValue(self.material.weight_per_meter or 0.0)
            self.supplier.setText(self.material.supplier or "")
            self.notes.setPlainText(self.material.notes or "")
    
    def update_price_per_meter(self):
        """Update the price per meter display"""
        price_per_kg = self.price_per_kg.value()
        weight_per_meter = self.weight_per_meter.value()
        price_per_meter = price_per_kg * weight_per_meter
        self.price_per_meter_label.setText(f"{price_per_meter:.2f} CZK/m")
    
    def save_material(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return
        
        try:
            if self.material:
                # Update existing material
                self.material.name = self.name.text().strip()
                self.material.material_type = self.material_type.currentText().strip() or None
                self.material.shape = self.shape.currentText().strip() or None
                self.material.size = self.size.text().strip() or None
                self.material.length = self.length.value()
                self.material.price_per_kg = self.price_per_kg.value()
                self.material.weight_per_meter = self.weight_per_meter.value()
                self.material.supplier = self.supplier.text().strip() or None
                self.material.notes = self.notes.toPlainText().strip() or None
            else:
                # Create new material
                material = Material(
                    name=self.name.text().strip(),
                    material_type=self.material_type.currentText().strip() or None,
                    shape=self.shape.currentText().strip() or None,
                    size=self.size.text().strip() or None,
                    length=self.length.value(),
                    price_per_kg=self.price_per_kg.value(),
                    weight_per_meter=self.weight_per_meter.value(),
                    supplier=self.supplier.text().strip() or None,
                    notes=self.notes.toPlainText().strip() or None
                )
                self.session.add(material)
            
            self.session.commit()
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error saving material: {str(e)}")

class MaterialsTab(QWidget):
    material_updated = pyqtSignal()
    material_created = pyqtSignal()
    material_deleted = pyqtSignal()
    
    def __init__(self, session: Session, user, permissions_manager, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        self.permissions_manager = permissions_manager
        self.init_ui()
        self.refresh_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search and buttons
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search materials...")
        self.search_input.textChanged.connect(self.filter_materials)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        search_layout.addStretch()
        
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Material")
        add_button.clicked.connect(self.add_material)
        edit_button = QPushButton("Edit Material")
        edit_button.clicked.connect(self.edit_material)
        delete_button = QPushButton("Delete Material")
        delete_button.clicked.connect(self.delete_material)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        
        button_layout.addStretch()
        layout.addLayout(search_layout)
        layout.addLayout(button_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Name", "Material Type", "Shape", "Size", "Length (mm)", 
            "Price/kg (CZK)", "Weight/m (kg)", "Price/m (CZK)"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Material Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Shape
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Length
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Price/kg
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Weight/m
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Price/m
        
        # Set table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def refresh_data(self):
        """Refresh the materials table"""
        try:
            materials = self.session.query(Material).order_by(Material.name).all()
            self.populate_table(materials)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load materials: {str(e)}")
    
    def populate_table(self, materials):
        self.table.setRowCount(len(materials))
        for i, material in enumerate(materials):
            price_per_meter = material.calculate_price_per_meter()
            
            self.table.setItem(i, 0, QTableWidgetItem(material.name or ""))
            self.table.setItem(i, 1, QTableWidgetItem(material.material_type or ""))
            self.table.setItem(i, 2, QTableWidgetItem(material.shape or ""))
            self.table.setItem(i, 3, QTableWidgetItem(material.size or ""))
            self.table.setItem(i, 4, QTableWidgetItem(f"{material.length:.0f}" if material.length else "0"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{material.price_per_kg:.2f}" if material.price_per_kg else "0.00"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{material.weight_per_meter:.3f}" if material.weight_per_meter else "0.000"))
            self.table.setItem(i, 7, QTableWidgetItem(f"{price_per_meter:.2f}"))
    
    def filter_materials(self):
        """Filter materials based on search text"""
        search_text = self.search_input.text().lower()
        if not search_text:
            self.refresh_data()
            return
        
        try:
            materials = self.session.query(Material).filter(
                Material.name.ilike(f"%{search_text}%") |
                Material.material_type.ilike(f"%{search_text}%") |
                Material.shape.ilike(f"%{search_text}%") |
                Material.size.ilike(f"%{search_text}%")
            ).order_by(Material.name).all()
            self.populate_table(materials)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not filter materials: {str(e)}")
    
    def get_selected_material(self):
        """Get the currently selected material"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        material_name = self.table.item(row, 0).text()
        
        return self.session.query(Material).filter(Material.name == material_name).first()
    
    def add_material(self):
        """Add a new material"""
        dialog = MaterialDialog(self.session, None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
            self.material_created.emit()
    
    def edit_material(self):
        """Edit the selected material"""
        material = self.get_selected_material()
        if not material:
            QMessageBox.warning(self, "Warning", "Please select a material to edit")
            return
        
        dialog = MaterialDialog(self.session, material, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
            self.material_updated.emit()
    
    def delete_material(self):
        """Delete the selected material"""
        material = self.get_selected_material()
        if not material:
            QMessageBox.warning(self, "Warning", "Please select a material to delete")
            return
        
        # Check if material is used in any components
        if material.component_materials:
            QMessageBox.warning(
                self, "Cannot Delete", 
                f"Material '{material.name}' is used in {len(material.component_materials)} component(s). "
                "Please remove it from all components first."
            )
            return
        
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete material '{material.name}'?",
            QMessageBox.StandardButton.Yes | QMessageButton.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.session.delete(material)
                self.session.commit()
                self.refresh_data()
                self.material_deleted.emit()
                QMessageBox.information(self, "Success", "Material deleted successfully")
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting material: {str(e)}")





