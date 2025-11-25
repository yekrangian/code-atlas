"""
Tests for model classes.
"""

from ..models import Product, User, Order


def test_product_creation():
    """Test product creation and basic operations."""
    product = Product(1, "Test Product", 99.99, 10)
    assert product.is_available()
    assert product.get_price() == 99.99


def test_user_operations():
    """Test user operations."""
    user = User(1, "test@example.com", "Test User")
    assert user.get_order_count() == 0
    assert user.get_total_spent() == 0.0


def test_order_processing():
    """Test order creation and processing."""
    user = User(1, "test@example.com", "Test User")
    product = Product(1, "Test Product", 50.0, 5)
    
    order = Order(1, user)
    assert order.add_item(product, 2)
    assert order.get_total() == 100.0

