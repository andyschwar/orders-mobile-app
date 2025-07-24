def parse_price(price_str: str) -> float:
    """Parse price string to float, handling both . and , as decimal separators"""
    if not price_str:
        return None
        
    # Replace comma with dot if comma is used as decimal separator
    price_str = price_str.replace(',', '.')
    
    try:
        return float(price_str)
    except ValueError:
        raise ValueError("Invalid price format. Use . or , as decimal separator.") 