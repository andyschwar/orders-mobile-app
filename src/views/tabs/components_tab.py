from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox,
    QDialog, QFormLayout, QDoubleSpinBox, QComboBox, QLabel,
    QHeaderView, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from models.database import Component
from utils.permissions import get_permissions_manager


class ComponentDialog(QDialog):
    def __init__(self, session: Session, component=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.component = component
        self.setWindowTitle("Add Component" if not component else "Edit Component")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # Create fields
        self.name = QLineEdit()
        self.description = QLineEdit()
        self.category = QComboBox()
        self.category.setEditable(True)  # Allow adding new categories
        
        # Price breakdown fields (all in CZK)
        self.buy_price = QDoubleSpinBox()
        self.buy_price.setDecimals(2)
        self.buy_price.setMaximum(100000.0)
        self.buy_price.setSuffix(" CZK")
        
        self.material_price = QDoubleSpinBox()
        self.material_price.setDecimals(2)
        self.material_price.setMaximum(100000.0)
        self.material_price.setSuffix(" CZK")
        
        self.manufacturing_price = QDoubleSpinBox()
        self.manufacturing_price.setDecimals(2)
        self.manufacturing_price.setMaximum(100000.0)
        self.manufacturing_price.setSuffix(" CZK")
        
        self.surface_treatment_price = QDoubleSpinBox()
        self.surface_treatment_price.setDecimals(2)
        self.surface_treatment_price.setMaximum(100000.0)
        self.surface_treatment_price.setSuffix(" CZK")
        
        # Total cost display (CZK only)
        cost_layout = QHBoxLayout()
        self.total_cost_czk_label = QLabel("0.00 CZK")
        self.total_cost_czk_label.setStyleSheet("font-weight: bold; color: blue;")
        cost_layout.addWidget(QLabel("Total Cost:"))
        cost_layout.addWidget(self.total_cost_czk_label)
        cost_layout.addStretch()
        
        # Unit cost field (read-only, calculated, CZK only)
        self.unit_cost = QDoubleSpinBox()
        self.unit_cost.setDecimals(2)
        self.unit_cost.setMaximum(100000.0)
        self.unit_cost.setSuffix(" CZK")
        self.unit_cost.setReadOnly(True)
        
        self.supplier = QLineEdit()
        
        self.component_type = QComboBox()
        self.component_type.addItems(["bought", "manufactured", "outsourced", "to review"])
        
        # Add fields to layout
        layout.addRow("Name*:", self.name)
        layout.addRow("Description:", self.description)
        layout.addRow("Category:", self.category)
        
        # Load existing categories
        self.load_categories()
        layout.addRow("Buy Price:", self.buy_price)
        layout.addRow("Material Price:", self.material_price)
        layout.addRow("Manufacturing Price:", self.manufacturing_price)
        layout.addRow("Surface Treatment Price:", self.surface_treatment_price)
        layout.addRow("", cost_layout)
        layout.addRow("Supplier:", self.supplier)
        layout.addRow("Type:", self.component_type)
        
        # Connect price fields to update total
        self.buy_price.valueChanged.connect(self.update_total_cost)
        self.material_price.valueChanged.connect(self.update_total_cost)
        self.manufacturing_price.valueChanged.connect(self.update_total_cost)
        self.surface_treatment_price.valueChanged.connect(self.update_total_cost)
        
        # Add buttons
        button_box = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_box.addStretch()
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        layout.addRow("", button_box)
        
        # If editing, populate fields
        if self.component:
            self.name.setText(self.component.name)
            self.description.setText(self.component.description or "")
            # Set category in combo box
            if self.component.category:
                index = self.category.findText(self.component.category)
                if index >= 0:
                    self.category.setCurrentIndex(index)
                else:
                    # If category doesn't exist in list, add it
                    self.category.addItem(self.component.category)
                    self.category.setCurrentText(self.component.category)
            self.buy_price.setValue(self.component.buy_price or 0.0)
            self.material_price.setValue(self.component.material_price or 0.0)
            self.manufacturing_price.setValue(self.component.manufacturing_price or 0.0)
            self.surface_treatment_price.setValue(self.component.surface_treatment_price or 0.0)
            self.unit_cost.setValue(self.component.unit_cost or 0.0)
            self.supplier.setText(self.component.supplier or "")
            self.component_type.setCurrentText(self.component.component_type or "bought")
        
        self.setLayout(layout)
        self.update_total_cost()
    
    def load_categories(self):
        """Load existing categories from database into combo box"""
        # Get all unique categories from existing components
        categories = self.session.query(Component.category).filter(
            Component.category.isnot(None),
            Component.category != ""
        ).distinct().order_by(Component.category).all()
        
        # Clear existing items and add empty option
        self.category.clear()
        self.category.addItem("")  # Empty option
        
        # Add existing categories
        for (category,) in categories:
            if category and category.strip():
                self.category.addItem(category.strip())
    
    def get_selected_category(self):
        """Get the selected category text, handling both existing and new entries"""
        category_text = self.category.currentText().strip()
        return category_text if category_text else None
    
    def update_total_cost(self):
        """Update the total cost display"""
        total_czk = (self.buy_price.value() + self.material_price.value() + 
                self.manufacturing_price.value() + self.surface_treatment_price.value())
        
        self.total_cost_czk_label.setText(f"{total_czk:.2f} CZK")
        self.unit_cost.setValue(total_czk)
    
    def get_data(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return None
            
        total_czk = self.unit_cost.value()
        
        return {
            "name": self.name.text().strip(),
            "description": self.description.text().strip() or None,
            "category": self.get_selected_category(),
            "buy_price": self.buy_price.value(),
            "material_price": self.material_price.value(),
            "manufacturing_price": self.manufacturing_price.value(),
            "surface_treatment_price": self.surface_treatment_price.value(),
            "unit_cost": total_czk,  # Calculated total in CZK
            "cost_currency": "CZK",  # Always CZK
            "supplier": self.supplier.text().strip() or None,
            "component_type": self.component_type.currentText()
        }

class ComponentsTab(QWidget):
    component_updated = pyqtSignal()
    component_created = pyqtSignal()
    component_deleted = pyqtSignal()
    
    def __init__(self, session: Session, user=None):
        super().__init__()
        self.session = session
        self.user = user
        self.permissions_manager = get_permissions_manager()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search components...")
        self.search_input.textChanged.connect(self.search_components)
        search_layout.addWidget(self.search_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Component")
        self.add_button.clicked.connect(self.add_component)
        button_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton("Edit Component")
        self.edit_button.clicked.connect(self.edit_component)
        button_layout.addWidget(self.edit_button)
        
        self.materials_button = QPushButton("Material Calculation")
        self.materials_button.clicked.connect(self.manage_materials)
        button_layout.addWidget(self.materials_button)
        
        self.delete_button = QPushButton("Delete Component")
        self.delete_button.clicked.connect(self.delete_component)
        button_layout.addWidget(self.delete_button)
        
        # Add export template button
        self.export_template_button = QPushButton("Export Template")
        self.export_template_button.clicked.connect(self.export_template)
        button_layout.addWidget(self.export_template_button)
        
        # Add refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        layout.addLayout(search_layout)
        layout.addLayout(button_layout)
        
        # Table
        self.table = QTableWidget()
        # Determine visible columns based on permissions
        visible_columns = self.permissions_manager.get_visible_columns(self.user, "components")
        # Always show these columns
        all_columns = [
            ("Name", "name"),
            ("Category", "category"),
            ("Description", "description"),
            ("Buy Price (CZK)", "buy_price"),
            ("Material Price (CZK)", "material_price"),
            ("Manufacturing Price (CZK)", "manufacturing_price"),
            ("Surface Treatment Price (CZK)", "surface_treatment_price"),
            ("Total Cost (CZK)", "unit_cost"),
            ("Supplier", "supplier"),
            ("Type", "component_type")
        ]
        # Build headers and index mapping
        self.column_indices = []
        headers = []
        for idx, (header, col_key) in enumerate(all_columns):
            # Only show price/currency columns if allowed
            if col_key in ["unit_cost", "cost_currency"] and not self.permissions_manager.can_access_column(self.user, "components", col_key):
                continue
            headers.append(header)
            self.column_indices.append(idx)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # Set table properties
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        
        # Set column widths immediately after setting headers
        self.set_initial_column_widths()
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        # Load initial data
        self.refresh_data()
    
    def set_initial_column_widths(self):
        """Set initial column widths based on headers"""
        header = self.table.horizontalHeader()
        column_count = self.table.columnCount()
        
        for col in range(column_count):
            header_text = self.table.horizontalHeaderItem(col).text()
            
            if "Name" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            elif "Category" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 120)
            elif "Description" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            elif "Buy Price" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 100)
            elif "Material Price" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 100)
            elif "Manufacturing Price" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 120)
            elif "Surface Treatment Price" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 120)
            elif "Total Cost" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 100)
            elif "Supplier" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            elif "Type" in header_text:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 100)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 100)
    
    def populate_table(self, components):
        self.table.setRowCount(len(components))
        for i, component in enumerate(components):
            row_data = [
                component.name,
                component.category or "",
                component.description or "",
                f"{component.buy_price:.2f}" if component.buy_price else "0.00",
                f"{component.material_price:.2f}" if component.material_price else "0.00",
                f"{component.manufacturing_price:.2f}" if component.manufacturing_price else "0.00",
                f"{component.surface_treatment_price:.2f}" if component.surface_treatment_price else "0.00",
                f"{component.unit_cost:.2f}" if component.unit_cost else "0.00",
                component.supplier or "",
                component.component_type or "bought"
            ]
            col = 0
            for idx in self.column_indices:
                self.table.setItem(i, col, QTableWidgetItem(row_data[idx]))
                col += 1
    
    def refresh_data(self):
        components = self.session.query(Component).order_by(Component.name).all()
        self.populate_table(components)
    
    def search_components(self, text):
        if not text:
            self.refresh_data()
            return
            
        search = f"%{text}%"
        components = self.session.query(Component).filter(
            or_(
                Component.name.ilike(search),
                Component.category.ilike(search),
                Component.description.ilike(search),
                Component.supplier.ilike(search)
            )
        ).order_by(Component.name).all()
        
        self.populate_table(components)
    
    def add_component(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "components", "create"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to add components.")
            return
            
        dialog = ComponentDialog(self.session, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    component = Component(**data)
                    component.update_unit_cost()  # This will also update EUR conversion
                    self.session.add(component)
                    self.session.commit()
                    self.refresh_data()
                    self.component_created.emit()
                    QMessageBox.information(self, "Success", "Component added successfully")
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error adding component: {str(e)}")
    
    def edit_component(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "components", "edit"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit components.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a component to edit")
            return
            
        component_name = self.table.item(selected_rows[0].row(), 0).text()
        component = self.session.query(Component).filter(Component.name == component_name).first()
        
        dialog = ComponentDialog(self.session, component, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    component.name = data["name"]
                    component.description = data["description"]
                    component.category = data["category"]
                    component.buy_price = data["buy_price"]
                    component.material_price = data["material_price"]
                    component.manufacturing_price = data["manufacturing_price"]
                    component.surface_treatment_price = data["surface_treatment_price"]
                    component.cost_currency = "CZK"  # Always CZK
                    component.supplier = data["supplier"]
                    component.component_type = data["component_type"]
                    
                    component.update_unit_cost()  # This will calculate total cost
                    
                    self.session.commit()
                    self.refresh_data()
                    self.component_updated.emit()
                    QMessageBox.information(self, "Success", "Component updated successfully")
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error updating component: {str(e)}")
    
    def delete_component(self):
        # Check permissions
        if self.user and not self.permissions_manager.has_permission(self.user, "components", "delete"):
            QMessageBox.warning(self, "Permission Denied", "You don't have permission to delete components.")
            return
            
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a component to delete")
            return
            
        component_name = self.table.item(selected_rows[0].row(), 0).text()
        component = self.session.query(Component).filter(Component.name == component_name).first()
        
        # Check if component is used in any products
        if component.product_components:
            QMessageBox.warning(
                self, "Cannot Delete", 
                f"Component '{component.name}' is used in {len(component.product_components)} product(s). "
                "Remove it from all products first."
            )
            return
        
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete component '{component.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.session.delete(component)
                self.session.commit()
                self.refresh_data()
                self.component_deleted.emit()
                QMessageBox.information(self, "Success", "Component deleted successfully")
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error deleting component: {str(e)}")
    
    def manage_materials(self):
        """Open manufacturing materials dialog for selected component"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a component to manage materials")
            return
            
        component_name = self.table.item(selected_rows[0].row(), 0).text()
        component = self.session.query(Component).filter(Component.name == component_name).first()
        
        if not component:
            QMessageBox.warning(self, "Warning", "Component not found")
            return
        
        # Only allow for manufactured components
        if component.component_type != 'manufactured':
            QMessageBox.information(
                self, "Information", 
                "Manufacturing materials can only be managed for components with type 'manufactured'.\n"
                f"Current type: {component.component_type}"
            )
            return
        
        from views.dialogs.component_materials_dialog import ComponentMaterialsDialog
        
        dialog = ComponentMaterialsDialog(self.session, component, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
            self.component_updated.emit()
    
    def export_template(self):
        """Export components template"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Template", "components_template.xlsx", "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                import pandas as pd
                
                # Create template with sample data
                template_data = {
                    'name': ['M6 Nut', 'M8 Bolt', 'O-ring 10mm', 'Steel Washer', 'Aluminum Plate'],
                    'description': ['Standard M6 hex nut', 'M8x20 hex head bolt', '10mm diameter rubber o-ring', 'M6 steel washer', '2mm thick aluminum plate'],
                    'supplier': ['Fastener Supply', 'Fastener Supply', 'Seal Supplier', 'Fastener Supply', 'Metal Supplier'],
                    'unit_cost': [0.15, 0.25, 0.05, 0.08, 2.50],
                    'cost_currency': ['CZK', 'CZK', 'CZK', 'CZK', 'CZK']
                }
                
                df = pd.DataFrame(template_data)
                df.to_excel(file_path, index=False)
                
                QMessageBox.information(self, "Success", f"Template exported to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting template: {str(e)}") 