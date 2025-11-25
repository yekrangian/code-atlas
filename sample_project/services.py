"""
Business logic services for order and payment processing.
"""

from typing import Optional
from .models import Order, User, Product
from .utils import validate_email, calculate_total


class OrderService:
    """Service for managing orders."""
    
    def __init__(self):
        self.orders: list[Order] = []
    
    def create_order(self, user: User, items: list[tuple[Product, int]]) -> Optional[Order]:
        """Create a new order for a user."""
        if not validate_email(user.email):
            return None
        
        order = Order(len(self.orders) + 1, user)
        
        for product, quantity in items:
            if not order.add_item(product, quantity):
                return None  # Failed to add item
        
        self.orders.append(order)
        return order
    
    def process_order(self, order: Order) -> bool:
        """Process an order through payment."""
        from .services import PaymentService
        
        payment_service = PaymentService()
        total = order.get_total()
        
        if payment_service.process_payment(order.user, total):
            order.complete()
            return True
        return False
    
    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Retrieve an order by its ID."""
        for order in self.orders:
            if order.order_id == order_id:
                return order
        return None
    
    def get_user_orders(self, user: User) -> list[Order]:
        """Get all orders for a specific user."""
        return [order for order in self.orders if order.user.user_id == user.user_id]


class PaymentService:
    """Service for processing payments."""
    
    def __init__(self):
        self.processed_payments: list[tuple[User, float]] = []
    
    def process_payment(self, user: User, amount: float) -> bool:
        """Process a payment for a user."""
        if amount <= 0:
            return False
        
        # Simulate payment processing
        if self._validate_payment(user, amount):
            self.processed_payments.append((user, amount))
            return True
        return False
    
    def _validate_payment(self, user: User, amount: float) -> bool:
        """Validate if payment can be processed."""
        # Simple validation logic
        if not validate_email(user.email):
            return False
        
        if amount > 10000:  # Large amount check
            return False
        
        return True
    
    def get_total_revenue(self) -> float:
        """Calculate total revenue from all processed payments."""
        total = 0.0
        for user, amount in self.processed_payments:
            total += amount
        return total
    
    def get_payment_count(self) -> int:
        """Get the number of processed payments."""
        return len(self.processed_payments)

