print('***** LABEL GENERATOR MODULE IMPORTED *****')

# raise Exception('TEST: label_generator.py imported at label print time')

print('USING label_generator.py')
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics.barcode import code128
import os
import sys
import tempfile
import traceback
from datetime import date
from typing import Dict, List
from PIL import Image, ImageDraw, ImageFont
import logging
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def replace_czech_chars(text):
    """Replace Czech characters with ASCII equivalents for better font compatibility"""
    if text is None:
        return None
        
    replacements = {
        'Á': 'A', 'á': 'a',
        'Č': 'C', 'č': 'c',
        'Ď': 'D', 'ď': 'd',
        'É': 'E', 'é': 'e',
        'Ě': 'E', 'ě': 'e',
        'Í': 'I', 'í': 'i',
        'Ň': 'N', 'ň': 'n',
        'Ó': 'O', 'ó': 'o',
        'Ř': 'R', 'ř': 'r',
        'Š': 'S', 'š': 's',
        'Ť': 'T', 'ť': 't',
        'Ú': 'U', 'ú': 'u',
        'Ů': 'U', 'ů': 'u',
        'Ý': 'Y', 'ý': 'y',
        'Ž': 'Z', 'ž': 'z'
    }
    
    for czech_char, ascii_char in replacements.items():
        text = text.replace(czech_char, ascii_char)
    
    return text

def test_barcode_generation():
    """Test function to verify barcode generation works"""
    print("Testing barcode generation...")
    try:
        # Create a test barcode using ReportLab
        test_barcode = code128.Code128("TEST123", barHeight=30, barWidth=1.0)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            print(f"Saving test barcode to: {tmp.name}")
            test_barcode.drawOn(canvas.Canvas(tmp.name), 0, 0)
            print("Test barcode saved successfully")
            return tmp.name
            
    except Exception as e:
        print(f"Error in test barcode generation: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

class LabelGenerator:
    def __init__(self, export_dir):
        """Initialize the label generator"""
        self.export_dir = export_dir
        self.label_width = 100*mm
        self.label_height = 70*mm
        self.margin_left = 30*mm
        self.margin_top = 30*mm
        self.page_height = 297*mm
        self.font_size = 12
        
        # Label size configurations
        self.label_sizes = {
            "standard": {"width": 100*mm, "height": 70*mm},
            "large": {"width": 120*mm, "height": 85*mm},
            "small": {"width": 80*mm, "height": 55*mm},
            "custom": {"width": 100*mm, "height": 70*mm}
        }
        
        # Layout configurations
        self.layout_configs = {
            "2x3": {"cols": 2, "rows": 3, "per_page": 6},
            "3x2": {"cols": 3, "rows": 2, "per_page": 6},
            "2x2": {"cols": 2, "rows": 2, "per_page": 4},
            "1x4": {"cols": 1, "rows": 4, "per_page": 4},
            "4x1": {"cols": 4, "rows": 1, "per_page": 4}
        }
        
        # Test barcode generation on initialization
        test_file = test_barcode_generation()
        if test_file:
            print(f"Test barcode generated successfully at: {test_file}")
        else:
            print("Test barcode generation failed!")
    
    def get_label_dimensions(self, size="standard", layout_type="2x3"):
        """Get label dimensions for the specified size and layout"""
        config = self.label_sizes.get(size, self.label_sizes["standard"])
        width, height = config["width"], config["height"]
        
        # A4 page dimensions: 210mm x 297mm (portrait)
        # Available space after margins: ~190mm x ~277mm (portrait)
        
        if layout_type == "2x2":  # 4 labels per page - portrait
            # A4: 210mm x 297mm
            # Available space after margins: ~190mm x ~277mm
            page_width = 190*mm
            page_height = 277*mm
            
            # For 2x2 layout: 2 columns, 2 rows
            # Calculate optimal label size to fit 2x2 with margins
            margin_between = 10*mm  # Space between labels (reduced)
            margin_around = 2*mm    # Space around the grid (reduced)
            
            # Calculate available space for labels
            available_width = page_width - 2*margin_around - margin_between
            available_height = page_height - 2*margin_around - margin_between
            
            # Each label gets half the available space
            width = available_width / 2   # ~91.5mm (wider)
            height = (available_height / 2) * 0.85  # ~100mm (reduced height to fit on one page)
            
        else:  # 2x3 layout - use portrait
            # Portrait A4: 210mm x 297mm
            # Available space after margins: ~190mm x ~277mm
            page_width = 190*mm
            page_height = 277*mm
            margin = 5*mm
            width = (page_width - 3*margin) / 2  # ~92.5mm
            height = (page_height - 4*margin) / 3  # ~87mm
            
        return width, height
    
    def get_layout_config(self, layout="2x3"):
        """Get layout configuration for the specified layout"""
        return self.layout_configs.get(layout, self.layout_configs["2x3"])
    
    def apply_label_style(self, canvas, style="modern"):
        """Apply different label styles"""
        if style == "modern":
            # Modern style with rounded corners and shadows
            canvas.setStrokeColor(colors.grey)
            canvas.setLineWidth(0.5)
        elif style == "classic":
            # Classic style with bold borders
            canvas.setStrokeColor(colors.black)
            canvas.setLineWidth(1.0)
        elif style == "compact":
            # Compact style with minimal borders
            canvas.setStrokeColor(colors.lightgrey)
            canvas.setLineWidth(0.25)
        else:
            # Default modern style
            canvas.setStrokeColor(colors.grey)
            canvas.setLineWidth(0.5)

    def create_barcode(self, data: str):
        """Create a Code128 barcode Flowable for ReportLab"""
        return code128.Code128(data, barHeight=20, barWidth=1.2, humanReadable=True, fontSize=8, fontName='Helvetica')

    def _draw_label(self, canvas, x, y, order_item, box_qty, box_num, total_boxes, include_barcodes=True):

        """Draw a single label"""

        
        # Save canvas state
        canvas.saveState()
        
        # Move to label position
        canvas.translate(x, y)
        
        # Draw border for label FIRST
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(3)
        canvas.rect(0, 0, self.label_width, self.label_height, fill=0, stroke=1)
        
        # Draw white background for label content
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, self.label_width, self.label_height, fill=1, stroke=0)
        canvas.setFillColor(colors.black)
        
        # Company name at the top
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(5*mm, 60*mm, "A.V.Z.-KOVO s.r.o.")
        
        # Customer info
        canvas.setFont("Helvetica-Bold", 9)
        customer_name = order_item.order.customer.name
        name_index = replace_czech_chars(order_item.order.customer.name_index)
        canvas.drawString(5*mm, 52*mm, f"{name_index} - {customer_name}")
        
        # Check if customer has barcodes enabled
        is_valid_customer = order_item.order.customer.barcodes_enabled or False
        print(f"Customer: {customer_name}, name_index: {name_index}, barcodes_enabled: {is_valid_customer}")
        
        # Order info
        canvas.setFont("Helvetica", 8)
        order_text = f"Order: {order_item.order.order_number}"
        canvas.drawString(5*mm, 45*mm, order_text)
        
        # Item info
        item_name = order_item.item.customer_item_name or order_item.item.product.name
        canvas.drawString(5*mm, 40*mm, f"Item: {item_name}")
        item_code_text = f"Code: {order_item.item.customer_code}"
        canvas.drawString(5*mm, 35*mm, item_code_text)
        
        # Quantity info
        canvas.setFont("Helvetica-Bold", 10)
        qty_text = f"Quantity: {box_qty}"
        canvas.drawString(5*mm, 28*mm, qty_text)
        
        # Calculate total weight if available
        if order_item.item.product and order_item.item.product.weight_per_unit:
            total_weight = box_qty * order_item.item.product.weight_per_unit
            canvas.drawString(5*mm, 22*mm, f"Weight: {total_weight:.2f} kg")
        
        # Add barcodes for valid customers if requested
        if include_barcodes and is_valid_customer:
            try:
                print("Generating barcodes for valid customer")
                
                # Generate barcodes using customer-specific prefixes
                customer = order_item.order.customer
                order_barcode_data = f"{customer.order_barcode_prefix or ''}{order_item.order.order_number}"
                order_barcode_flowable = self.create_barcode(order_barcode_data)
                
                item_barcode_data = f"{customer.item_barcode_prefix or ''}{order_item.item.customer_code}"
                item_barcode_flowable = self.create_barcode(item_barcode_data)
                
                qty_barcode_data = f"{customer.quantity_barcode_prefix or ''}{box_qty}"
                qty_barcode_flowable = self.create_barcode(qty_barcode_data)
                
                # Calculate barcode positions
                barcode_width = 35*mm
                barcode_height = 10*mm
                
                # Draw barcodes
                order_barcode_flowable.drawOn(canvas, 30*mm, 45*mm)
                canvas.setFont("Helvetica", 6)
                canvas.drawString(30*mm, 44*mm, f"{customer.order_barcode_prefix or ''}{order_item.order.order_number}")
                
                item_barcode_flowable.drawOn(canvas, 30*mm, 35*mm)
                canvas.drawString(30*mm, 34*mm, f"{customer.item_barcode_prefix or ''}{order_item.item.customer_code}")
                
                qty_barcode_flowable.drawOn(canvas, 30*mm, 28*mm)
                canvas.drawString(30*mm, 27*mm, f"{customer.quantity_barcode_prefix or ''}{box_qty}")
                
                print("Barcodes generated and drawn successfully")
                
            except Exception as e:
                print(f"Error generating barcodes: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                # Continue without barcodes rather than failing completely
        else:
            if not include_barcodes:
                print("Barcodes not requested for this label")
            else:
                print("Customer not in valid list, skipping barcode generation")
        
        # Add delivery date
        canvas.setFont("Helvetica", 8)
        delivery_date = order_item.delivery_date.strftime("%Y-%m-%d") if order_item.delivery_date else "Not set"
        canvas.drawString(5*mm, 5*mm, f"Delivery: {delivery_date}")
        
        # Restore canvas state
        canvas.restoreState()
        print("Label drawing completed")

    def generate_labels(self, delivery_items, include_barcodes=True, formatting_options=None, printed_by=None, session=None):
        print(f"[DEBUG] LabelGenerator.generate_labels called with {len(delivery_items)} items")
        print(f"[DEBUG] include_barcodes: {include_barcodes}")
        print(f"[DEBUG] formatting_options: {formatting_options}")
        
        # Use formatting options if provided, otherwise use defaults
        if formatting_options is None:
            formatting_options = {
                "label_size": "standard",
                "layout_type": "2x3",
                "include_barcodes": include_barcodes,
                "include_weight": True,
                "include_delivery_date": True,
                "include_supplier_info": True,
                "font_size": 10,
                "label_style": "modern"
            }
        
        # Get label dimensions and layout config
        layout_type = formatting_options.get("layout_type", "2x3")
        label_width, label_height = self.get_label_dimensions(formatting_options.get("label_size", "standard"), layout_type)
        layout_config = self.get_layout_config(layout_type)
        
        # Get font size from formatting options and create custom styles
        font_size = formatting_options.get("font_size", 10)

        
        # Create custom styles with the specified font size
        styles = getSampleStyleSheet()
        custom_style = styles["Normal"]
        custom_style.fontSize = font_size
        custom_style.fontName = "Helvetica-Bold"
        
        # Get timestamp and customer name index for filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get customer name index from the first item (assuming all items are from same customer)
        customer_name_index = "UNKNOWN"
        if delivery_items:
            try:
                first_item = delivery_items[0]
                order_item = first_item["order_item"]
                customer_name_index = replace_czech_chars(order_item.order.customer.name_index)
            except Exception as e:
                pass
        
        filename = os.path.join(self.export_dir, f"labels_{customer_name_index}_{timestamp}.pdf")

        # Prepare all label Flowables
        styles = getSampleStyleSheet()
        labels = []
        
        for item in delivery_items:
            try:
                print(f"[DEBUG] Processing item: {item}")
                order_item = item["order_item"]
                boxes = item.get("boxes", [item["quantity"]])
                name_index = replace_czech_chars(order_item.order.customer.name_index)
                is_barcode_customer = order_item.order.customer.barcodes_enabled or False
                print(f"[DEBUG] order_item: {order_item}")
                print(f"[DEBUG] boxes: {boxes}")
                print(f"[DEBUG] name_index: {name_index}")
                print(f"[DEBUG] is_barcode_customer: {is_barcode_customer}")
                
            except Exception as e:
                print(f"[DEBUG] Error processing item: {e}")
                continue
            
            for box_num, box_qty in enumerate(boxes, 1):
                try:
                    label_flowables = []
                    
                    # Use exact same template for both layouts
                    if layout_type == "2x2":
                        # Exact same template as 6 labels, no modifications
                        label_flowables.append(Paragraph(f"Customer: {order_item.order.customer.name}", custom_style))
                    else:
                        # Original template for 2x3 layout
                        label_flowables.append(Paragraph(f"Customer: {order_item.order.customer.name}", custom_style))
                    
                    
                except Exception as e:
                    continue
                
                # Add item info
                label_flowables.append(Paragraph(f"Item: {order_item.item.customer_item_name or order_item.item.product.name}", custom_style))
                label_flowables.append(Paragraph(f"Code: {order_item.item.customer_code}", custom_style))
                
                # Add barcodes if enabled, or placeholder for consistent height
                print(f"[DEBUG] Barcode check: include_barcodes={formatting_options.get('include_barcodes', include_barcodes)}, is_barcode_customer={is_barcode_customer}")
                if formatting_options.get("include_barcodes", include_barcodes) and is_barcode_customer:
                    customer = order_item.order.customer
                    # Use prefix if set, otherwise no prefix
                    item_barcode = f"{customer.item_barcode_prefix or ''}{order_item.item.customer_code}"
                    print(f"[DEBUG] Generating item barcode: {item_barcode}")
                    label_flowables.append(self.create_barcode(item_barcode))
                else:
                    print(f"[DEBUG] Skipping item barcode generation")
                    # Add placeholder space to maintain consistent height
                    label_flowables.append(Paragraph("<br/><br/>", custom_style))
                
                # Add order info
                label_flowables.append(Paragraph(f"Order: {order_item.order.order_number}", custom_style))
                
                # Add order barcode if enabled, or placeholder for consistent height
                if formatting_options.get("include_barcodes", include_barcodes) and is_barcode_customer:
                    customer = order_item.order.customer
                    # Use prefix if set, otherwise no prefix
                    order_barcode = f"{customer.order_barcode_prefix or ''}{order_item.order.order_number}"
                    print(f"[DEBUG] Generating order barcode: {order_barcode}")
                    label_flowables.append(self.create_barcode(order_barcode))
                else:
                    print(f"[DEBUG] Skipping order barcode generation")
                    # Add placeholder space to maintain consistent height
                    label_flowables.append(Paragraph("<br/><br/>", custom_style))
                
                # Add quantity
                label_flowables.append(Paragraph(f"Quantity: {box_qty}", custom_style))
                
                # Add weight if enabled and available
                try:
                    if (formatting_options.get("include_weight", True) and 
                        order_item.item.product and 
                        hasattr(order_item.item.product, 'weight_per_unit') and 
                        order_item.item.product.weight_per_unit):
                        total_weight = box_qty * order_item.item.product.weight_per_unit
                        label_flowables.append(Paragraph(f"Weight: {total_weight:.2f} kg", custom_style))
                except Exception as e:
                    # Continue without weight
                    pass
                
                # Add quantity barcode if enabled, or placeholder for consistent height
                if formatting_options.get("include_barcodes", include_barcodes) and is_barcode_customer:
                    customer = order_item.order.customer
                    # Use prefix if set, otherwise no prefix
                    qty_barcode = f"{customer.quantity_barcode_prefix or ''}{box_qty}"
                    print(f"[DEBUG] Generating quantity barcode: {qty_barcode}")
                    label_flowables.append(self.create_barcode(qty_barcode))
                else:
                    print(f"[DEBUG] Skipping quantity barcode generation")
                    # Add placeholder space to maintain consistent height
                    label_flowables.append(Paragraph("<br/><br/>", custom_style))
                
                # Add supplier info if enabled
                if formatting_options.get("include_supplier_info", True):
                    label_flowables.append(Paragraph(f"Supplier: A.V.Z.-KOVO s.r.o.", custom_style))
                
                # Add delivery date if enabled
                try:
                    if formatting_options.get("include_delivery_date", True) and hasattr(order_item, 'delivery_date') and order_item.delivery_date:
                        delivery_date = order_item.delivery_date.strftime("%Y-%m-%d")
                        delivery_para = Paragraph(f"Delivery: {delivery_date}", custom_style)
                        # Create a table with bottom border for the delivery date
                        delivery_table = Table([[delivery_para]], colWidths=[label_width-4*mm])
                        delivery_table.setStyle(TableStyle([
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                        ]))
                        label_flowables.append(delivery_table)
                except Exception as e:
                    # Continue without delivery date
                    pass
                
                try:
                    labels.append(label_flowables)
                except Exception as e:
                    continue

        # Arrange labels according to layout configuration
        try:
            grid = []
            row = []
            for idx, label in enumerate(labels):
                try:
                    row.append(Table([[f] for f in label], colWidths=[label_width]))
                    if len(row) == layout_config["cols"]:
                        grid.append(row)
                        row = []
                    if len(grid) == layout_config["rows"]:
                        grid.append(["PAGE_BREAK"])
                except Exception as e:
                    continue
            if row:
                while len(row) < layout_config["cols"]:
                    row.append("")
                grid.append(row)
        except Exception as e:
            raise
        
        # Build the story
        story = []
        for r in grid:
            if r == ["PAGE_BREAK"]:
                story.append(PageBreak())
            else:
                col_widths = [label_width] * layout_config["cols"]
                # Use 1 row height since we're creating a table with 1 row of data
                row_heights = [label_height]
                # Add spacing between labels
                table = Table([r], colWidths=col_widths, rowHeights=row_heights)
                
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
                    ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                    # Force consistent height by setting minimum row height
                    ('MINROWHEIGHT', (0, 0), (-1, -1), label_height),
                ]))
                story.append(table)
                
                # Add spacing between rows for 2x3 layout
                if layout_type == "2x3":
                    from reportlab.platypus import Spacer
                    story.append(Spacer(1, 8*mm))  # 8mm spacing between rows for better cutting
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=5*mm,
            leftMargin=5*mm,
            topMargin=5*mm,
            bottomMargin=5*mm
        )
        doc.build(story)
        
        # Log the printed labels if session is provided
        print(f"[DEBUG] Logging check: session={session is not None}, printed_by={printed_by}")
        if session and printed_by:
            print(f"[DEBUG] Calling _log_printed_labels with {len(delivery_items)} items")
            self._log_printed_labels(delivery_items, include_barcodes, filename, printed_by, session)
        else:
            print(f"[DEBUG] Skipping logging: session={session is not None}, printed_by={printed_by}")
        
        return filename

    def _log_printed_labels(self, delivery_items, include_barcodes, pdf_filename, printed_by, session):
        """Log printed labels to the database"""
        print(f"[DEBUG] _log_printed_labels called with {len(delivery_items)} items")
        try:
            from src.models.database import LabelLog
            
            for item in delivery_items:
                order_item = item["order_item"]
                boxes = item.get("boxes", [item["quantity"]])
                
                # Get customer information
                customer = order_item.order.customer
                customer_name = customer.name
                customer_name_index = customer.name_index
                
                # Get item information
                item_name = order_item.item.customer_item_name or order_item.item.product.name
                item_code = order_item.item.customer_code
                
                # Get barcode information
                barcodes_included = include_barcodes or customer.barcodes_enabled
                item_barcode = f"{customer.item_barcode_prefix or ''}{item_code}" if barcodes_included else None
                order_barcode = f"{customer.order_barcode_prefix or ''}{order_item.order.order_number}" if barcodes_included else None
                
                # Log each box/quantity as a separate entry
                for box_qty in boxes:
                    quantity_barcode = f"{customer.quantity_barcode_prefix or ''}{box_qty}" if barcodes_included else None
                    
                    # Handle fake objects that don't have database IDs
                    order_item_id = getattr(order_item, 'id', None)
                    if order_item_id is None:
                        # For fake objects, we can't link to a real order_item
                        # We'll set it to None and handle it in the database
                        order_item_id = None
                    
                    label_log = LabelLog(
                        order_item_id=order_item_id,
                        customer_name=customer_name,
                        customer_name_index=customer_name_index,
                        order_number=order_item.order.order_number,
                        item_code=item_code,
                        item_name=item_name,
                        quantity=box_qty,
                        printed_quantity=1,  # Each box gets one label
                        barcodes_included=barcodes_included,
                        item_barcode=item_barcode,
                        order_barcode=order_barcode,
                        quantity_barcode=quantity_barcode,
                        printed_by=printed_by,
                        pdf_filename=pdf_filename
                    )
                    
                    session.add(label_log)
            
            session.commit()
            print(f"[DEBUG] Logged {len(delivery_items)} label print jobs to database")
            
        except Exception as e:
            print(f"[DEBUG] Error logging printed labels: {e}")
            session.rollback()

    def preview_label(self, order_item, box_qty, box_num, total_boxes):
        """Generate a single preview label for testing"""
        filename = os.path.join(self.export_dir, "preview_label.pdf")
        c = canvas.Canvas(filename, pagesize=A4)
        self._draw_label(c, 0, self.page_height - self.label_height, 
                        order_item, box_qty, box_num, total_boxes)
        c.showPage()
        c.save()
        return filename

    def create_single_label(self, data: Dict[str, str], include_barcodes: List[str] = None) -> Image.Image:
        """
        Create a single label with the given data
        """
        # Create blank label image
        label = Image.new('RGB', (self.label_width, self.label_height), 'white')
        draw = ImageDraw.Draw(label)
        
        # Start position for text
        x, y = 10, 10
        line_height = self.font_size + 4
        
        # Add text content
        for key, value in data.items():
            if key != 'barcodes':  # Skip barcode data in text section
                text = f"{key}: {value}"
                draw.text((x, y), text, fill='black', font=self.font)
                y += line_height
        
        # Add barcodes if requested
        if include_barcodes and 'barcodes' in data:
            barcode_y = y + 10
            for field in include_barcodes:
                if field in data['barcodes']:
                    barcode_img = self.create_barcode(data['barcodes'][field])
                    # Resize barcode to fit label width while maintaining aspect ratio
                    barcode_width = self.label_width - 20
                    ratio = barcode_width / barcode_img.width
                    barcode_height = int(barcode_img.height * ratio)
                    barcode_img = barcode_img.resize((barcode_width, barcode_height))
                    
                    # Paste barcode onto label
                    label.paste(barcode_img, (x, barcode_y))
                    barcode_y += barcode_height + 10
        
        return label

    def create_label_sheet(self, labels_data: List[Dict[str, str]], include_barcodes: List[str] = None) -> Image.Image:
        """
        Create a sheet of labels (6 per page, 2x3 layout)
        """
        # A4 size in pixels at 300 DPI
        page_width = 2480
        page_height = 3508
        
        # Calculate margins and spacing
        horizontal_margin = (page_width - (self.label_width * 2)) // 3
        vertical_margin = (page_height - (self.label_height * 3)) // 4
        
        # Create blank page
        page = Image.new('RGB', (page_width, page_height), 'white')
        
        for i, data in enumerate(labels_data):
            if i >= self.labels_per_page:
                break
                
            # Calculate position for this label
            row = i // 2
            col = i % 2
            
            x = horizontal_margin + (col * (self.label_width + horizontal_margin))
            y = vertical_margin + (row * (self.label_height + vertical_margin))
            
            # Create and paste individual label
            label = self.create_single_label(data, include_barcodes)
            page.paste(label, (x, y))
        
        return page

    def save_labels(self, labels_data: List[Dict[str, str]], output_path: str, include_barcodes: List[str] = None):
        """
        Save labels to PDF file
        """
        # Calculate number of pages needed
        num_pages = (len(labels_data) + self.labels_per_page - 1) // self.labels_per_page
        
        # Create list to store all pages
        pages = []
        
        for page_num in range(num_pages):
            start_idx = page_num * self.labels_per_page
            end_idx = start_idx + self.labels_per_page
            page_data = labels_data[start_idx:end_idx]
            
            page = self.create_label_sheet(page_data, include_barcodes)
            pages.append(page)
        
        # Save first page
        pages[0].save(
            output_path,
            "PDF",
            resolution=300.0,
            save_all=True,
            append_images=pages[1:] if len(pages) > 1 else []
        ) 