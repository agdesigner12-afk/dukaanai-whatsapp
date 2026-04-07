from app import app, db, Product, Customer, Order
from datetime import datetime, timedelta

with app.app_context():
    # Clear existing data
    Product.query.delete()
    Customer.query.delete()
    Order.query.delete()
    
    # Add products
    products = [
        Product(name='Fresh Tomatoes', price=40, stock=100, unit='kg'),
        Product(name='Red Onions', price=35, stock=150, unit='kg'),
        Product(name='Potatoes', price=25, stock=200, unit='kg'),
        Product(name='Green Chilies', price=20, stock=80, unit='kg'),
    ]
    for p in products:
        db.session.add(p)
    
    # Add customers
    customers = [
        Customer(name='Rajesh Kumar', phone='9876543210', balance=0),
        Customer(name='Priya Sharma', phone='9876543211', balance=0),
    ]
    for c in customers:
        db.session.add(c)
    
    # Add orders for today
    orders = [
        Order(customer_name='Rajesh Kumar', customer_phone='9876543210', total=450, status='pending', source='whatsapp', created_at=datetime.now()),
        Order(customer_name='Priya Sharma', customer_phone='9876543211', total=280, status='completed', source='whatsapp', created_at=datetime.now()),
    ]
    for o in orders:
        db.session.add(o)
    
    db.session.commit()
    print(f'✅ Added {Product.query.count()} products, {Customer.query.count()} customers, {Order.query.count()} orders')
