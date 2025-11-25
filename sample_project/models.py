"""
Data models for the e-commerce system.
"""

from typing import List, Optional
from datetime import datetime


class Product:
    """Represents a product in the inventory."""
    
    def __init__(self, product_id: int, name: str, price: float, stock: int = 0):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.stock = stock
        self.created_at = datetime.now()
    
    def is_available(self) -> bool:
        """Check if product is in stock."""
        return self.stock > 0
    
    def reduce_stock(self, quantity: int) -> bool:
        """Reduce stock by given quantity."""
        if self.stock >= quantity:
            self.stock -= quantity
            return True
        return False
    
    def get_price(self) -> float:
        """Get the current price of the product."""
        return self.price
    
    def update_price(self, new_price: float) -> None:
        """Update the product price."""
        if new_price > 0:
            self.price = new_price


class User:
    """Represents a user/customer."""
    
    def __init__(self, user_id: int, email: str, name: str):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.orders: List['Order'] = []
    
    def add_order(self, order: 'Order') -> None:
        """Add an order to user's order history."""
        self.orders.append(order)
    
    def get_total_spent(self) -> float:
        """Calculate total amount spent by user."""
        total = 0.0
        for order in self.orders:
            total += order.get_total()
        return total
    
    def get_order_count(self) -> int:
        """Get the number of orders placed by user."""
        return len(self.orders)


class Order:
    """Represents an order."""
    
    def __init__(self, order_id: int, user: User):
        self.order_id = order_id
        self.user = user
        self.items: List[tuple[Product, int]] = []  # (product, quantity)
        self.status = "pending"
        self.created_at = datetime.now()
    
    def add_item(self, product: Product, quantity: int) -> bool:
        """Add a product to the order."""
        if product.is_available() and product.reduce_stock(quantity):
            self.items.append((product, quantity))
            return True
        return False
    
    def get_total(self) -> float:
        """Calculate total order amount."""
        from .utils import calculate_total
        return calculate_total(self.items)
    
    def complete(self) -> None:
        """Mark order as completed."""
        self.status = "completed"
        self.user.add_order(self)
    
    def cancel(self) -> None:
        """Cancel the order and restore stock."""
        for product, quantity in self.items:
            product.stock += quantity
        self.status = "cancelled"

