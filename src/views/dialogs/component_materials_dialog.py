from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QLabel, QDoubleSpinBox,
    QComboBox, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt
from sqlalchemy.orm import Session
from models.database import Component, Material, ComponentMaterial

class ComponentMaterialsDialog(QDialog):
    def __init__(self, session: Session, component: Component, parent=None):
        super().__init__(parent)
        self.session = session
        self.component = component
        self.setWindowTitle(f"Material Calculation - {component.name}")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.load_materials()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Component info
        info_group = QGroupBox("Component Information")
        info_layout = QFormLayout()
        
        self.component_name_label = QLabel(self.component.name)
        self.component_name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.component_type_label = QLabel(self.component.component_type or "Unknown")
        
        info_layout.addRow("Name:", self.component_name_label)
        info_layout.addRow("Type:", self.component_type_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Add material section
        add_group = QGroupBox("Add Material")
        add_layout = QFormLayout()
        
        self.material_combo = QComboBox()
        self.material_combo.setMinimumWidth(300)
        
        self.required_length = QDoubleSpinBox()
        self.required_length.setDecimals(1)
        self.required_length.setMaximum(10000.0)
        self.required_length.setSuffix(" mm")
        
        self.cutting_allowance = QDoubleSpinBox()
        self.cutting_allowance.setDecimals(1)
        self.cutting_allowance.setMaximum(1000.0)
        self.cutting_allowance.setValue(5.0)  # Default 5mm
        self.cutting_allowance.setSuffix(" mm")
        
        self.waste_percentage = QDoubleSpinBox()
        self.waste_percentage.setDecimals(1)
        self.waste_percentage.setMaximum(100.0)
        self.waste_percentage.setSuffix(" %")
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        
        add_layout.addRow("Material:", self.material_combo)
        add_layout.addRow("Required Length:", self.required_length)
        add_layout.addRow("Cutting Allowance:", self.cutting_allowance)
        add_layout.addRow("Waste Percentage:", self.waste_percentage)
        add_layout.addRow("Notes:", self.notes)
        
        add_button = QPushButton("Add Material")
        add_button.clicked.connect(self.add_material)
        add_layout.addRow(add_button)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        # Materials table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Material", "Size", "Required Length", "Cutting Allowance", 
            "Waste %", "Total Length", "Cost (CZK)"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Material
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Required Length
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Cutting Allowance
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Waste %
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Total Length
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Cost
        
        # Set table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        layout.addWidget(self.table)
        
        # Summary
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; color: blue; font-size: 14px;")
        layout.addWidget(self.summary_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Remove material button
        remove_button = QPushButton("Remove Selected Material")
        remove_button.clicked.connect(self.remove_material)
        remove_button.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        button_layout.addWidget(remove_button)
        
        button_layout.addStretch()
        
        # Calculate material cost button
        calculate_button = QPushButton("Update Material Cost")
        calculate_button.clicked.connect(self.update_manufacturing_cost)
        calculate_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        button_layout.addWidget(calculate_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Load data
        self.load_component_materials()
    
    def load_materials(self):
        """Load available materials into the combo box"""
        try:
            materials = self.session.query(Material).order_by(Material.name).all()
            self.material_combo.clear()
            for material in materials:
                self.material_combo.addItem(f"{material.name} ({material.size})", material.id)
        except Exception as e:
            QMessageBox.warning(self, "Database Error", f"Could not load materials: {str(e)}")
    
    def load_component_materials(self):
        """Load component materials into the table"""
        try:
            component_materials = self.session.query(ComponentMaterial).filter(
                ComponentMaterial.component_id == self.component.id
            ).all()
            
            self.table.setRowCount(len(component_materials))
            total_cost = 0.0
            
            for i, comp_material in enumerate(component_materials):
                material = comp_material.material
                cost = comp_material.calculate_material_cost()
                total_cost += cost
                
                # Calculate total length
                total_length = comp_material.required_length + comp_material.cutting_allowance
                if comp_material.waste_percentage > 0:
                    total_length = total_length * (1 + comp_material.waste_percentage / 100)
                
                self.table.setItem(i, 0, QTableWidgetItem(material.name))
                self.table.setItem(i, 1, QTableWidgetItem(material.size or ""))
                self.table.setItem(i, 2, QTableWidgetItem(f"{comp_material.required_length:.1f}"))
                self.table.setItem(i, 3, QTableWidgetItem(f"{comp_material.cutting_allowance:.1f}"))
                self.table.setItem(i, 4, QTableWidgetItem(f"{comp_material.waste_percentage:.1f}"))
                self.table.setItem(i, 5, QTableWidgetItem(f"{total_length:.1f}"))
                self.table.setItem(i, 6, QTableWidgetItem(f"{cost:.2f}"))
            
            # Update summary
            self.summary_label.setText(f"Total Material Cost: {total_cost:.2f} CZK")
            
        except Exception as e:
            QMessageBox.warning(self, "Database Error", f"Could not load component materials: {str(e)}")
    
    def add_material(self):
        """Add a material to the component"""
        material_id = self.material_combo.currentData()
        if not material_id:
            QMessageBox.warning(self, "Warning", "Please select a material")
            return
        
        if self.required_length.value() <= 0:
            QMessageBox.warning(self, "Warning", "Required length must be greater than 0")
            return
        
        try:
            # Check if material is already added
            existing = self.session.query(ComponentMaterial).filter(
                ComponentMaterial.component_id == self.component.id,
                ComponentMaterial.material_id == material_id
            ).first()
            
            if existing:
                QMessageBox.warning(self, "Warning", "This material is already added to the component")
                return
            
            # Create new component material
            component_material = ComponentMaterial(
                component_id=self.component.id,
                material_id=material_id,
                required_length=self.required_length.value(),
                cutting_allowance=self.cutting_allowance.value(),
                waste_percentage=self.waste_percentage.value(),
                notes=self.notes.toPlainText().strip() or None
            )
            
            self.session.add(component_material)
            self.session.commit()
            
            # Clear form
            self.required_length.setValue(0.0)
            self.cutting_allowance.setValue(5.0)
            self.waste_percentage.setValue(0.0)
            self.notes.clear()
            
            # Refresh table
            self.load_component_materials()
            
            QMessageBox.information(self, "Success", "Material added successfully")
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error adding material: {str(e)}")
    
    def remove_material(self):
        """Remove selected material from component"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a material to remove")
            return
        
        row = selected_rows[0].row()
        material_name = self.table.item(row, 0).text()
        
        confirm = QMessageBox.question(
            self,
            "Confirm Remove",
            f"Are you sure you want to remove '{material_name}' from this component?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                # Find the component material
                component_material = self.session.query(ComponentMaterial).filter(
                    ComponentMaterial.component_id == self.component.id,
                    ComponentMaterial.material.has(Material.name == material_name)
                ).first()
                
                if component_material:
                    self.session.delete(component_material)
                    self.session.commit()
                    self.load_component_materials()
                    QMessageBox.information(self, "Success", "Material removed successfully")
                
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error removing material: {str(e)}")
    
    def update_manufacturing_cost(self):
        """Update the component's material cost based on materials"""
        try:
            # Calculate total material cost from materials
            total_cost = 0.0
            component_materials = self.session.query(ComponentMaterial).filter(
                ComponentMaterial.component_id == self.component.id
            ).all()
            
            for comp_material in component_materials:
                total_cost += comp_material.calculate_material_cost()
            
            # Update component material price
            self.component.material_price = total_cost
            self.component.update_unit_cost()
            
            self.session.commit()
            
            QMessageBox.information(
                self, "Success", 
                f"Material cost updated to {total_cost:.2f} CZK\n"
                f"Total component cost: {self.component.unit_cost:.2f} CZK"
            )
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error updating manufacturing cost: {str(e)}")
