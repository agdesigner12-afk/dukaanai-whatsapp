from app import app, db, Product, Customer, Order
from datetime import datetime, timedelta
import random

with app.app_context():
    # Only keep the structure, but we will seed historical orders and customers
    today = datetime.now()
    
    products = Product.query.all()
    if not products:
        print("No products. Please run add_data.py first.")
        exit()
        
    print("Generating 30 days of mock data...")
    
    # Generate mock customers over 30 days
    names = ["Amit", "Rohit", "Sneha", "Kavita", "Vikas", "Pooja", "Vikram", "Anjali", "Suresh", "Meena"]
    mock_customers = []
    
    for _ in range(25):
        days_ago = random.randint(0, 30)
        c_date = today - timedelta(days=days_ago)
        c = Customer(
            name=random.choice(names) + " " + str(random.randint(1, 99)),
            phone="9" + "".join([str(random.randint(0, 9)) for _ in range(9)]),
            balance=random.choice([0, 0, 0, 50, 120]),
            created_at=c_date
        )
        db.session.add(c)
        mock_customers.append(c)
        
    # Generate mock orders over 30 days
    statuses = ['completed', 'completed', 'completed', 'pending', 'cancelled']
    sources = ['whatsapp', 'whatsapp', 'walk-in']
    
    for _ in range(80):
        days_ago = random.randint(0, 30)
        o_date = today - timedelta(days=days_ago)
        
        # Pick random customer
        c = random.choice(mock_customers) if mock_customers else None
        c_name = c.name if c else "Walk-in Customer"
        c_phone = c.phone if c else ""
        
        # Random total between 100 and 2000
        total = round(random.uniform(100, 2000), 2)
        
        o = Order(
            customer_name=c_name,
            customer_phone=c_phone,
            total=total,
            status=random.choice(statuses),
            source=random.choice(sources),
            created_at=o_date
        )
        db.session.add(o)
        
        # If completed, update product sold count to make top products data
        if o.status == 'completed':
            for _ in range(random.randint(1, 4)):
                p = random.choice(products)
                qty = random.randint(1, 5)
                p.total_sold = (p.total_sold or 0) + qty
                db.session.add(p)
                
    db.session.commit()
    print("✅ Successfully injected historical mock data!")
