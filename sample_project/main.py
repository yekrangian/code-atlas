"""
Main entry point for the sample e-commerce application.
Demonstrates usage of various components.
"""

from .models import Product, User, Order
from .services import OrderService, PaymentService
from .utils import validate_email, calculate_total, format_currency, get_final_price


def create_sample_data():
    """Create sample products and users for testing."""
    products = [
        Product(1, "Laptop", 999.99, 10),
        Product(2, "Mouse", 29.99, 50),
        Product(3, "Keyboard", 79.99, 30),
    ]
    
    users = [
        User(1, "alice@example.com", "Alice"),
        User(2, "bob@example.com", "Bob"),
    ]
    
    return products, users


def process_sample_order():
    """Process a sample order to demonstrate the system."""
    products, users = create_sample_data()
    
    # Create order service
    order_service = OrderService()
    
    # Create an order
    user = users[0]
    items = [(products[0], 1), (products[1], 2)]
    
    order = order_service.create_order(user, items)
    
    if order:
        print(f"Order created: {order.order_id}")
        total = order.get_total()
        print(f"Total: {format_currency(total)}")
        
        # Process payment
        if order_service.process_order(order):
            print("Order processed successfully!")
            final_price = get_final_price(total, discount=10.0)
            print(f"Final price with discount: {format_currency(final_price)}")
        else:
            print("Payment processing failed")
    else:
        print("Failed to create order")


def demonstrate_user_statistics():
    """Demonstrate user statistics calculation."""
    products, users = create_sample_data()
    order_service = OrderService()
    
    user = users[0]
    
    # Create multiple orders
    for i in range(3):
        items = [(products[i % len(products)], 1)]
        order = order_service.create_order(user, items)
        if order:
            order_service.process_order(order)
    
    # Display statistics
    print(f"User: {user.name}")
    print(f"Total orders: {user.get_order_count()}")
    print(f"Total spent: {format_currency(user.get_total_spent())}")


def main():
    """Main function to run the demonstration."""
    print("=" * 50)
    print("E-Commerce System Demonstration")
    print("=" * 50)
    
    # Validate email
    test_email = "test@example.com"
    if validate_email(test_email):
        print(f"Email validation passed: {test_email}")
    
    # Process sample order
    print("\n--- Processing Sample Order ---")
    process_sample_order()
    
    # Demonstrate statistics
    print("\n--- User Statistics ---")
    demonstrate_user_statistics()
    
    print("\n" + "=" * 50)
    print("Demonstration complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()

