import sqlite3
import os

print("🔧 Fixing database...")

# Delete old database if exists
if os.path.exists('dukaanai.db'):
    os.remove('dukaanai.db')
    print("✅ Old database deleted")

# Create new database with correct schema
conn = sqlite3.connect('dukaanai.db')
cursor = conn.cursor()

# Create tables with correct columns
cursor.execute('''
CREATE TABLE business (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    business_name VARCHAR(100),
    created_at TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE customer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER,
    phone VARCHAR(20),
    name VARCHAR(100),
    balance FLOAT DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    total_spent FLOAT DEFAULT 0,
    last_order_date TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES business(id)
)
''')

cursor.execute('''
CREATE TABLE product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER,
    name VARCHAR(200),
    price FLOAT,
    unit VARCHAR(20),
    stock INTEGER DEFAULT 0,
    total_sold INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES business(id)
)
''')

cursor.execute('''
CREATE TABLE "order" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER,
    customer_id INTEGER,
    items TEXT,
    total FLOAT,
    status VARCHAR(20) DEFAULT 'pending',
    source VARCHAR(20) DEFAULT 'whatsapp',
    payment_method VARCHAR(20) DEFAULT 'cash',
    notes TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES business(id),
    FOREIGN KEY(customer_id) REFERENCES customer(id)
)
''')

cursor.execute('''
CREATE TABLE conversation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    message TEXT,
    response TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customer(id)
)
''')

conn.commit()
conn.close()
print("✅ New database created with correct schema")

print("\n🎉 Fix complete! Now run 'python app.py'")