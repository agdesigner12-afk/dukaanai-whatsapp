from app import app, db
from app import Product
import sqlite3
import os

print("🔧 Starting database migration...")

with app.app_context():
    # Delete old database if exists
    if os.path.exists('dukaanai.db'):
        os.remove('dukaanai.db')
        print("✅ Old database deleted")
    
    # Create new database with all columns
    db.create_all()
    print("✅ New database created with all columns")
    
    # Add sample products
    from app import Business
    if not Business.query.first():
        business = Business(
            phone="owner",
            name="Test Shop",
            business_name="DukaanAI Demo"
        )
        db.session.add(business)
        db.session.commit()
        print("✅ Default business created")
    
    # Add sample products
    products = [
        Product(business_id=1, name="गोल्ड चाय पत्ती", price=250, unit="kg", stock=15, total_sold=0),
        Product(business_id=1, name="Tata नमक", price=25, unit="kg", stock=8, total_sold=0),
        Product(business_id=1, name="फोर्ट बिस्कुट", price=10, unit="piece", stock=45, total_sold=0)
    ]
    for p in products:
        db.session.add(p)
    db.session.commit()
    print("✅ Sample products added")
    
    print("\n🎉 Migration complete! Database is ready.")