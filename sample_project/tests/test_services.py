"""
Tests for service classes.
"""

from ..models import Product, User
from ..services import OrderService, PaymentService
from ..utils import validate_email


def test_order_service():
    """Test order service operations."""
    service = OrderService()
    user = User(1, "test@example.com", "Test User")
    product = Product(1, "Test Product", 50.0, 5)
    
    order = service.create_order(user, [(product, 2)])
    assert order is not None
    assert order.order_id == 1


def test_payment_service():
    """Test payment service operations."""
    service = PaymentService()
    user = User(1, "test@example.com", "Test User")
    
    result = service.process_payment(user, 100.0)
    assert result is True
    assert service.get_payment_count() == 1

