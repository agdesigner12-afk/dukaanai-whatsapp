from app import app, db, Business, Customer, Product, Order

with app.app_context():
    print("✅ Testing database connection...")
    
    # Count records
    print(f"Businesses: {Business.query.count()}")
    print(f"Customers: {Customer.query.count()}")
    print(f"Products: {Product.query.count()}")
    print(f"Orders: {Order.query.count()}")
    
    # Add a test product if none exist
    if Product.query.count() == 0:
        business = Business.query.first()
        if business:
            product = Product(
                business_id=business.id,
                name="गोल्ड चाय पत्ती",
                price=250,
                unit="kg",
                stock=15
            )
            db.session.add(product)
            db.session.commit()
            print("✅ Added test product: गोल्ड चाय पत्ती")
    
    print("✅ Database test complete!")