#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

def create_template():
    # Create a directory for templates if it doesn't exist
    template_dir = Path("templates")
    template_dir.mkdir(exist_ok=True)
    
    # Create Excel writer
    with pd.ExcelWriter(template_dir / "import_template.xlsx", engine='openpyxl') as writer:
        # Customers template
        customers_df = pd.DataFrame(columns=[
            'name_index',  # Required
            'name',        # Required
            'street',
            'city',
            'country',
            'email1',
            'email2',
            'email3',
            'atest_email',
            'invoice_email',
            'ico_vat',
            'ic_dph',
            'currency',
            'is_eu',
            'delivery_address'
        ])
        customers_df.loc[0] = ['ARAD', 'Example Company', 'Street 123', 'City', 'Country', 
                              'email@example.com', '', '', '', '', '12345', '67890', 'EUR', 
                              True, 'Delivery Address']
        customers_df.to_excel(writer, sheet_name='Customers', index=False)
        
        # Products template
        products_df = pd.DataFrame(columns=[
            'name',           # Required
            'description',
            'weight_per_unit'
        ])
        products_df.loc[0] = ['Product Name', 'Product Description', 1.5]
        products_df.to_excel(writer, sheet_name='Products', index=False)
        
        # Items template
        items_df = pd.DataFrame(columns=[
            'customer_index',     # Required (must match customer name_index)
            'product_name',       # Required (must match product name)
            'customer_code',      # Required
            'customer_item_name',
            'item_type',
            'similar_item'
        ])
        items_df.loc[0] = ['ARAD', 'Product Name', 'ITEM001', 'Customer Item Name', 'Type A', '']
        items_df.to_excel(writer, sheet_name='Items', index=False)
        
        # Employees template
        employees_df = pd.DataFrame(columns=[
            'name',      # Required
            'address',
            'phone',
            'email',
            'birthday',
            'name_day',
            'is_active'
        ])
        employees_df.loc[0] = ['John Doe', '123 Main St', '+1234567890', 'john@example.com', 
                              '1990-01-01', '2000-01-01', True]
        employees_df.to_excel(writer, sheet_name='Employees', index=False)
        
        # Orders template
        orders_df = pd.DataFrame(columns=[
            'order_number',       # Required
            'customer_index',     # Required (must match customer name_index)
            'order_date',         # Required
            'item_code',          # Required (must match item customer_code)
            'quantity',           # Required
            'price',
            'delivery_date',      # Required
            'delivered_quantity',
            'last_delivery_date'
        ])
        orders_df.loc[0] = ['ORD001', 'ARAD', '2024-01-01', 'ITEM001', 100, 10.50, 
                           '2024-02-01', 0, None]
        orders_df.to_excel(writer, sheet_name='Orders', index=False)
    
    print(f"\nTemplate file created at: {template_dir}/import_template.xlsx")
    print("\nImport your data using:")
    print("python src/import_data.py path/to/your/file.xlsx --type TYPE")
    print("\nWhere TYPE is one of: customers, products, items, employees, orders")
    print("Optional: --sheet SHEET_NAME to specify a different sheet name")

if __name__ == "__main__":
    create_template() 