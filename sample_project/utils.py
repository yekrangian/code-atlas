"""
Utility functions for the e-commerce system.
"""

import re
from typing import List, Tuple
from .models import Product


def validate_email(email: str) -> bool:
    """Validate email address format."""
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def calculate_total(items: List[Tuple[Product, int]]) -> float:
    """Calculate total price for a list of items."""
    total = 0.0
    for product, quantity in items:
        price = product.get_price()
        total += price * quantity
    return total


def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    return f"${amount:.2f}"


def apply_discount(amount: float, discount_percent: float) -> float:
    """Apply discount percentage to an amount."""
    if discount_percent < 0 or discount_percent > 100:
        return amount
    
    discount = amount * (discount_percent / 100)
    return amount - discount


def calculate_tax(amount: float, tax_rate: float = 0.1) -> float:
    """Calculate tax on an amount."""
    return amount * tax_rate


def get_final_price(amount: float, discount: float = 0.0, tax_rate: float = 0.1) -> float:
    """Calculate final price after discount and tax."""
    discounted = apply_discount(amount, discount)
    tax = calculate_tax(discounted, tax_rate)
    return discounted + tax

