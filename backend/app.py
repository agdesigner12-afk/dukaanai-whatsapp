from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import re
import json
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from twilio.rest import Client

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dukaanai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Twilio client
twilio_client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

# DeepSeek client (OpenAI-compatible)
deepseek_client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com/v1"
)

executor = ThreadPoolExecutor(max_workers=5)

# ========== DATABASE MODELS ==========
class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), default="My Shop")
    address = db.Column(db.String(200), default="")
    gstin = db.Column(db.String(20), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(20), default='kg')
    total_sold = db.Column(db.Integer, default=0)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True)
    balance = db.Column(db.Float, default=0)
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0)
    last_order_date = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    total = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='pending')
    source = db.Column(db.String(20), default='whatsapp')
    items = db.Column(db.Text, default='[]')
    customer_gstin = db.Column(db.String(20), default='')
    created_at = db.Column(db.DateTime, default=datetime.now)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)

# ========== CREATE TABLES & MIGRATE ==========
with app.app_context():
    db.create_all()
    # Add missing columns if needed
    try:
        db.session.execute('ALTER TABLE business ADD COLUMN name VARCHAR(100) DEFAULT "My Shop"')
    except: pass
    try:
        db.session.execute('ALTER TABLE business ADD COLUMN address VARCHAR(200) DEFAULT ""')
    except: pass
    try:
        db.session.execute('ALTER TABLE business ADD COLUMN gstin VARCHAR(20) DEFAULT ""')
    except: pass
    try:
        db.session.execute('ALTER TABLE "order" ADD COLUMN items TEXT DEFAULT "[]"')
    except: pass
    try:
        db.session.execute('ALTER TABLE "order" ADD COLUMN customer_gstin VARCHAR(20) DEFAULT ""')
    except: pass

    # Create default business if none exists
    if Business.query.count() == 0:
        default_biz = Business(
            phone=os.getenv('TWILIO_WHATSAPP_NUMBER', '+14155238886'),
            name="DukaanAI Shop",
            address="123, Main Market, New Delhi",
            gstin="07AAACA1234A1Z"
        )
        db.session.add(default_biz)
        db.session.commit()
    print("✅ Database ready")

# ========== HELPER: GET BUSINESS DETAILS ==========
def get_business():
    biz = Business.query.first()
    if not biz:
        biz = Business(phone=os.getenv('TWILIO_WHATSAPP_NUMBER'))
        db.session.add(biz)
        db.session.commit()
    return biz

# ========== API ROUTES ==========
@app.route('/api/business', methods=['GET'])
def api_get_business():
    biz = get_business()
    return jsonify({
        'name': biz.name,
        'address': biz.address,
        'phone': biz.phone,
        'gstin': biz.gstin
    })

@app.route('/api/business', methods=['PUT'])
def api_update_business():
    data = request.json
    biz = get_business()
    if 'name' in data: biz.name = data['name']
    if 'address' in data: biz.address = data['address']
    if 'phone' in data: biz.phone = data['phone']
    if 'gstin' in data: biz.gstin = data['gstin']
    db.session.commit()
    return jsonify({'message': 'Business details updated'})

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': p.price,
        'stock': p.stock,
        'unit': p.unit,
        'total_sold': p.total_sold or 0
    } for p in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    product = Product(
        name=data['name'],
        price=float(data['price']),
        stock=int(data['stock']),
        unit=data['unit']
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({'message': 'Product added', 'id': product.id}), 201

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = Product.query.get_or_404(id)
    data = request.json
    if 'name' in data: product.name = data['name']
    if 'price' in data: product.price = float(data['price'])
    if 'stock' in data: product.stock = int(data['stock'])
    if 'unit' in data: product.unit = data['unit']
    db.session.commit()
    return jsonify({'message': 'Product updated'})

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Product deleted'})

@app.route('/api/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'balance': float(c.balance),
        'total_orders': c.total_orders,
        'total_spent': float(c.total_spent) if c.total_spent else 0,
        'last_order_date': c.last_order_date
    } for c in customers])

@app.route('/api/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()
    return jsonify([{
        'id': o.id,
        'customer': o.customer_name,
        'customer_phone': o.customer_phone,
        'total': float(o.total),
        'status': o.status,
        'source': o.source,
        'date': o.created_at.strftime('%Y-%m-%d'),
        'time': o.created_at.strftime('%H:%M'),
        'items': json.loads(o.items) if o.items else []
    } for o in orders])

@app.route('/api/orders/<int:id>', methods=['PATCH'])
def update_order_status(id):
    order = Order.query.get_or_404(id)
    data = request.json
    if 'status' in data:
        order.status = data['status']
        db.session.commit()
    return jsonify({'message': 'Order updated'})

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    today = datetime.now().date()
    today_orders = Order.query.filter(db.func.date(Order.created_at) == today).all()
    return jsonify({
        'today': {
            'orders': len(today_orders),
            'revenue': sum(o.total for o in today_orders)
        },
        'pending': Order.query.filter_by(status='pending').count(),
        'lowStock': Product.query.filter(Product.stock < 10).count(),
        'customers': {
            'total': Customer.query.count(),
            'new': Customer.query.filter(db.func.date(Customer.created_at) == today).count()
        }
    })

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    # Simple placeholder – you can expand later
    return jsonify({
        'revenueTrends': [],
        'topProducts': [],
        'customerGrowth': [],
        'orderCompletion': []
    })

# ========== WHATSAPP BOT WITH DEEPSEEK ==========
def get_business_details():
    biz = get_business()
    return {
        'name': biz.name,
        'address': biz.address,
        'phone': biz.phone,
        'gstin': biz.gstin
    }

def get_ai_response_bot(customer, message):
    """AI response using DeepSeek API"""
    try:
        # Fetch products for context (limit to 3 for speed)
        products = Product.query.limit(3).all()
        product_list = "\n".join([f"{p.name}: ₹{p.price}" for p in products]) if products else "कोई प्रोडक्ट नहीं"

        prompt = f"""Customer: {customer.name}
Balance: ₹{customer.balance}
Message: {message}
Products: {product_list}

Short Hinglish reply (1-2 lines):"""

        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are DukaanAI, a friendly Hindi/English WhatsApp assistant for a small shop. Keep replies very short (1-2 lines)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=80
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ DeepSeek API error: {e}")
        return "थोड़ी देर में try करें। 🙏"

def process_whatsapp_message(from_number, body):
    try:
        with app.app_context():
            customer = Customer.query.filter_by(phone=from_number).first()
            if not customer:
                customer = Customer(
                    phone=from_number,
                    name=f"User_{from_number[-4:]}",
                    balance=0
                )
                db.session.add(customer)
                db.session.commit()

            reply = get_ai_response_bot(customer, body)

        twilio_client.messages.create(
            body=reply,
            from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
            to=from_number
        )
        print(f"✅ Replied to {from_number}: {reply[:50]}...")
    except Exception as e:
        print(f"❌ WhatsApp error: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    from_number = request.form.get('From')
    body = request.form.get('Body', '').strip()
    print(f"📲 Message from {from_number}: {body}")
    executor.submit(process_whatsapp_message, from_number, body)
    return "OK", 200

# ========== ROOT ==========
@app.route('/')
def home():
    return jsonify({'message': 'DukaanAI API is running with DeepSeek AI!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)