from app import app, db, Product, Customer, Order
from datetime import datetime

with app.app_context():
    # Add sample products
    products = [
        Product(name='Tomato', price=40, stock=100, unit='kg'),
        Product(name='Onion', price=30, stock=150, unit='kg'),
        Product(name='Potato', price=25, stock=200, unit='kg'),
    ]
    for p in products:
        db.session.add(p)
    
    # Add sample customer
    customer = Customer(name='Rajesh Kumar', phone='9876543210', balance=0)
    db.session.add(customer)
    
    db.session.commit()
    print("✅ Sample data added!")
