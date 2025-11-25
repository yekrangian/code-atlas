"""
Tests for utility functions.
"""

from ..utils import validate_email, calculate_total, apply_discount
from ..models import Product


def test_email_validation():
    """Test email validation."""
    assert validate_email("test@example.com") is True
    assert validate_email("invalid-email") is False
    assert validate_email("") is False


def test_calculate_total():
    """Test total calculation."""
    product1 = Product(1, "Item 1", 10.0, 5)
    product2 = Product(2, "Item 2", 20.0, 5)
    
    items = [(product1, 2), (product2, 1)]
    total = calculate_total(items)
    assert total == 40.0


def test_discount_calculation():
    """Test discount application."""
    result = apply_discount(100.0, 10.0)
    assert result == 90.0

