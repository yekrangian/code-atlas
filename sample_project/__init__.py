"""
Sample Project - A demonstration project for code analysis.
This project simulates a simple e-commerce system.
"""

from .models import Product, User, Order
from .services import OrderService, PaymentService
from .utils import validate_email, calculate_total

__all__ = [
    'Product',
    'User', 
    'Order',
    'OrderService',
    'PaymentService',
    'validate_email',
    'calculate_total'
]

