from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QLabel, QDoubleSpinBox,
    QComboBox, QSpinBox, QMenu
)
from PyQt6.QtCore import Qt
from sqlalchemy.orm import Session
from models.database import Product, Component, ProductComponent

class ProductComponentsDialog(QDialog):
    def __init__(self, session: Session, product: Product, parent=None):
        super().__init__(parent)
        self.session = session
        self.product = product
        self.setWindowTitle(f"Manage Components - {product.name}")
        self.setModal(True)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Product info
        product_info = QLabel(f"Product: {self.product.name}")
        product_info.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(product_info)
        
        if self.product.description:
            desc_info = QLabel(f"Description: {self.product.description}")
            layout.addWidget(desc_info)
        
        # Add component section
        layout.addWidget(QLabel("Add Component:"))
        
        add_layout = QFormLayout()
        
        # Component selection
        component_layout = QHBoxLayout()
        self.component_combo = QComboBox()
        self.component_combo.setMinimumWidth(300)
        component_layout.addWidget(self.component_combo)
        
        # Create new component button
        create_component_button = QPushButton("Create New")
        create_component_button.clicked.connect(self.create_new_component)
        component_layout.addWidget(create_component_button)
        
        add_layout.addRow("Component:", component_layout)
        
        # Quantity
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setDecimals(2)
        self.quantity_input.setMinimum(0.01)
        self.quantity_input.setMaximum(10000.0)
        self.quantity_input.setValue(1.0)
        add_layout.addRow("Quantity:", self.quantity_input)
        
        # Add button
        add_button = QPushButton("Add Component")
        add_button.clicked.connect(self.add_component)
        add_layout.addRow("", add_button)
        
        layout.addLayout(add_layout)
        
        # Components table
        layout.addWidget(QLabel("Current Components:"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Component", "Description", "Unit Cost (CZK)", "Quantity", "Total Cost (CZK)"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Enable context menu for the table
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)
        
        # Summary
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; color: blue;")
        layout.addWidget(self.summary_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Remove component button
        remove_button = QPushButton("Remove Selected Component")
        remove_button.clicked.connect(self.remove_component)
        remove_button.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        button_layout.addWidget(remove_button)
        
        button_layout.addStretch()  # Add space between buttons
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Load data
        self.load_components()
        self.load_product_components()
        self.update_summary()
        
    def load_components(self):
        """Load available components into combo box"""
        self.component_combo.clear()
        components = self.session.query(Component).order_by(Component.name).all()
        
        for component in components:
            display_text = f"{component.name}"
            if component.supplier:
                display_text += f" ({component.supplier})"
            if component.unit_cost:
                display_text += f" - {component.unit_cost:.2f} CZK"
            
            self.component_combo.addItem(display_text, component.id)
    
    def load_product_components(self):
        """Load current product components into table"""
        product_components = self.session.query(ProductComponent).filter(
            ProductComponent.product_id == self.product.id
        ).all()
        
        self.table.setRowCount(len(product_components))
        
        for i, pc in enumerate(product_components):
            component = pc.component
            
            # Component name
            name_item = QTableWidgetItem(component.name)
            self.table.setItem(i, 0, name_item)
            
            # Description
            desc_item = QTableWidgetItem(component.description or "")
            self.table.setItem(i, 1, desc_item)
            
            # Unit cost
            cost_item = QTableWidgetItem(f"{component.unit_cost:.2f}" if component.unit_cost else "0.00")
            self.table.setItem(i, 2, cost_item)
            
            # Quantity
            qty_item = QTableWidgetItem(f"{pc.quantity:.2f}")
            self.table.setItem(i, 3, qty_item)
            
            # Total cost
            total_cost = (component.unit_cost or 0) * pc.quantity
            total_item = QTableWidgetItem(f"{total_cost:.2f}")
            self.table.setItem(i, 4, total_item)
    
    def update_summary(self):
        """Update the summary with total cost and component count"""
        product_components = self.session.query(ProductComponent).filter(
            ProductComponent.product_id == self.product.id
        ).all()
        
        total_cost = 0.0
        for pc in product_components:
            component = pc.component
            component_cost = (component.unit_cost or 0) * pc.quantity
            total_cost += component_cost
        
        self.summary_label.setText(
            f"Total Components: {len(product_components)} | "
            f"Total Cost: {total_cost:.2f} CZK"
        )
    
    def add_component(self):
        """Add a component to the product"""
        if self.component_combo.count() == 0:
            QMessageBox.warning(self, "No Components", "No components available to add.")
            return
        
        component_id = self.component_combo.currentData()
        quantity = self.quantity_input.value()
        
        # Check if component is already added
        existing = self.session.query(ProductComponent).filter(
            ProductComponent.product_id == self.product.id,
            ProductComponent.component_id == component_id
        ).first()
        
        if existing:
            QMessageBox.warning(
                self, "Component Exists", 
                "This component is already added to the product."
            )
            return
        
        try:
            product_component = ProductComponent(
                product_id=self.product.id,
                component_id=component_id,
                quantity=quantity
            )
            self.session.add(product_component)
            self.session.commit()
            
            self.load_product_components()
            self.update_summary()
            
            QMessageBox.information(self, "Success", "Component added successfully")
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error adding component: {str(e)}")
    
    def remove_component(self):
        """Remove selected component from product"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select a component to remove")
            return
        
        row = selected_rows[0].row()
        component_name = self.table.item(row, 0).text()
        
        confirm = QMessageBox.question(
            self,
            "Confirm Remove",
            f"Are you sure you want to remove '{component_name}' from this product?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                # Find the component by name
                component = self.session.query(Component).filter(
                    Component.name == component_name
                ).first()
                
                if component:
                    product_component = self.session.query(ProductComponent).filter(
                        ProductComponent.product_id == self.product.id,
                        ProductComponent.component_id == component.id
                    ).first()
                    
                    if product_component:
                        self.session.delete(product_component)
                        self.session.commit()
                        
                        self.load_product_components()
                        self.update_summary()
                        
                        QMessageBox.information(self, "Success", "Component removed successfully")
                    else:
                        QMessageBox.warning(self, "Error", "Component not found in product")
                else:
                    QMessageBox.warning(self, "Error", "Component not found")
                    
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Error removing component: {str(e)}")
    
    def create_new_component(self):
        """Create a new component and add it to the combo box"""
        from views.tabs.components_tab import ComponentDialog
        
        # Create a new component dialog
        dialog = ComponentDialog(self.session, None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    # Create the new component
                    new_component = Component(
                        name=data['name'],
                        description=data.get('description', ''),
                        category=data.get('category', ''),
                        supplier=data.get('supplier', ''),
                        buy_price=data.get('buy_price', 0.0),
                        material_price=data.get('material_price', 0.0),
                        manufacturing_price=data.get('manufacturing_price', 0.0),
                        surface_treatment_price=data.get('surface_treatment_price', 0.0),
                        unit_cost=data.get('unit_cost', 0.0),
                        cost_currency=data.get('cost_currency', 'CZK'),
                        component_type=data.get('component_type', 'bought')
                    )
                    
                    self.session.add(new_component)
                    self.session.commit()
                    
                    # Refresh the components list
                    self.load_components()
                    
                    # Select the newly created component
                    for i in range(self.component_combo.count()):
                        if self.component_combo.itemData(i) == new_component.id:
                            self.component_combo.setCurrentIndex(i)
                            break
                    
                    QMessageBox.information(self, "Success", f"Component '{new_component.name}' created successfully")
                    
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Error creating component: {str(e)}")
    
    def show_context_menu(self, position):
        """Show context menu for the components table"""
        item = self.table.itemAt(position)
        if item is None:
            return
        
        # Create context menu
        context_menu = QMenu(self)
        
        # Add remove action
        remove_action = context_menu.addAction("Remove Component")
        remove_action.triggered.connect(self.remove_component)
        
        # Show context menu
        context_menu.exec(self.table.mapToGlobal(position)) 