"""
Currency conversion utility for reports.
Converts all currencies to EUR for comparison purposes.

To update exchange rates, modify the EXCHANGE_RATES dictionary below.
You can also fetch real-time rates from an API if needed.
"""

# Exchange rates (you may want to make these configurable or fetch from an API)
# Last updated: 2025-01-09
# To update rates, modify this dictionary or implement API fetching
EXCHANGE_RATES = {
    'CZK': 0.041,  # 1 CZK = 0.041 EUR (approximate rate)
    'EUR': 1.0,    # Base currency
    'USD': 0.85,   # 1 USD = 0.85 EUR (approximate rate)
    'GBP': 1.18,   # 1 GBP = 1.18 EUR (approximate rate)
    'PLN': 0.22,   # 1 PLN = 0.22 EUR (approximate rate)
    'HUF': 0.0026, # 1 HUF = 0.0026 EUR (approximate rate)
    'RON': 0.20,   # 1 RON = 0.20 EUR (approximate rate)
}

def convert_to_eur(amount: float, from_currency: str) -> float:
    """
    Convert an amount from the specified currency to EUR.
    
    Args:
        amount: The amount to convert
        from_currency: The source currency code (e.g., 'CZK', 'EUR', 'USD')
    
    Returns:
        The amount converted to EUR
    """
    if not amount or amount == 0:
        return 0.0
    
    # Normalize currency code
    currency = from_currency.upper() if from_currency else 'EUR'
    
    # Get exchange rate
    rate = EXCHANGE_RATES.get(currency, 1.0)
    
    # Convert to EUR
    return amount * rate

def convert_to_czk(amount: float, from_currency: str) -> float:
    """
    Convert an amount from the specified currency to CZK.
    
    Args:
        amount: The amount to convert
        from_currency: The source currency code (e.g., 'CZK', 'EUR', 'USD')
    
    Returns:
        The amount converted to CZK
    """
    if not amount or amount == 0:
        return 0.0
    
    # Normalize currency code
    currency = from_currency.upper() if from_currency else 'EUR'
    
    # First convert to EUR, then to CZK
    eur_amount = convert_to_eur(amount, from_currency)
    
    # Convert EUR to CZK (1 EUR = 24.39 CZK approximately)
    return eur_amount / EXCHANGE_RATES.get('CZK', 0.041)

def convert_to_target_currency(amount: float, from_currency: str, target_currency: str) -> float:
    """
    Convert an amount from one currency to another.
    
    Args:
        amount: The amount to convert
        from_currency: The source currency code
        target_currency: The target currency code
    
    Returns:
        The amount converted to target currency
    """
    if target_currency.upper() == 'EUR':
        return convert_to_eur(amount, from_currency)
    elif target_currency.upper() == 'CZK':
        return convert_to_czk(amount, from_currency)
    else:
        # For other currencies, convert to EUR first
        return convert_to_eur(amount, from_currency)

def format_currency_display(amount: float, original_currency: str, target_currency: str = 'EUR', converted_amount: float = None) -> str:
    """
    Format currency for display in reports.
    
    Args:
        amount: Original amount
        original_currency: Original currency code
        target_currency: Target currency for display (default: EUR)
        converted_amount: Amount converted to target currency (if None, will convert)
    
    Returns:
        Formatted string showing both original and target currency amounts
    """
    if not amount or amount == 0:
        return f"0.00 {target_currency}"
    
    if converted_amount is None:
        converted_amount = convert_to_target_currency(amount, original_currency, target_currency)
    
    currency = original_currency.upper() if original_currency else 'EUR'
    
    if currency == target_currency.upper():
        return f"{amount:,.2f} {target_currency}"
    else:
        return f"{amount:,.2f} {currency} ({converted_amount:,.2f} {target_currency})"

def get_currency_info(customer_currency: str, customer_is_eu: bool) -> dict:
    """
    Get currency information for a customer.
    
    Args:
        customer_currency: Customer's currency code
        customer_is_eu: Whether customer is EU member
    
    Returns:
        Dictionary with currency information
    """
    currency = customer_currency.upper() if customer_currency else 'EUR'
    
    return {
        'currency': currency,
        'is_eu': customer_is_eu,
        'needs_conversion': currency != 'EUR',
        'exchange_rate': EXCHANGE_RATES.get(currency, 1.0)
    } 