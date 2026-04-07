from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import re
import json
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai
from twilio.rest import Client

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for React

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dukaanai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Twilio + Gemini setup
twilio_client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
executor = ThreadPoolExecutor(max_workers=5)

# Models
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
    created_at = db.Column(db.DateTime, default=datetime.now)

# API Routes
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
    if 'name' in data:
        product.name = data['name']
    if 'price' in data:
        product.price = float(data['price'])
    if 'stock' in data:
        product.stock = int(data['stock'])
    if 'unit' in data:
        product.unit = data['unit']
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

@app.route('/api/customers', methods=['POST'])
def add_customer():
    data = request.json
    customer = Customer(
        name=data['name'],
        phone=data['phone'],
        balance=float(data.get('balance', 0))
    )
    db.session.add(customer)
    db.session.commit()
    return jsonify({'message': 'Customer added', 'id': customer.id}), 201

@app.route('/api/customers/<int:id>', methods=['PUT'])
def update_customer(id):
    customer = Customer.query.get_or_404(id)
    data = request.json
    if 'name' in data:
        customer.name = data['name']
    if 'phone' in data:
        customer.phone = data['phone']
    if 'balance' in data:
        customer.balance = float(data['balance'])
    db.session.commit()
    return jsonify({'message': 'Customer updated'})

@app.route('/api/customers/<int:id>', methods=['DELETE'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    return jsonify({'message': 'Customer deleted'})

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
        'time': o.created_at.strftime('%H:%M')
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
    from datetime import timedelta
    today = datetime.now().date()
    seven_days_ago = today - timedelta(days=6)
    
    all_orders = Order.query.all()
    
    revenue_trends = {}
    for i in range(7):
        d = today - timedelta(days=i)
        revenue_trends[d.strftime('%m-%d')] = 0
        
    completed_orders = 0
    cancelled_orders = 0
    pending_orders = 0
    
    for order in all_orders:
        if order.status == 'completed':
            completed_orders += 1
        elif order.status == 'cancelled':
            cancelled_orders += 1
        else:
            pending_orders += 1
            
        order_date = order.created_at.date()
        if order.status == 'completed' and order_date >= seven_days_ago:
            date_str = order_date.strftime('%m-%d')
            if date_str in revenue_trends:
                revenue_trends[date_str] += order.total
                
    trend_data = [{'date': k, 'revenue': v} for k, v in sorted(revenue_trends.items())]
    
    top_products = Product.query.order_by(Product.total_sold.desc()).limit(5).all()
    top_products_data = [{'name': p.name, 'sold': p.total_sold} for p in top_products]
    
    all_customers = Customer.query.all()
    customer_growth = {}
    for i in range(7):
        d = today - timedelta(days=i)
        customer_growth[d.strftime('%m-%d')] = 0
        
    for c in all_customers:
        c_date = c.created_at.date()
        if c_date >= seven_days_ago:
            date_str = c_date.strftime('%m-%d')
            if date_str in customer_growth:
                customer_growth[date_str] += 1
                
    # Calculate cumulative for area chart
    growth_data = []
    running_total = Customer.query.filter(db.func.date(Customer.created_at) < seven_days_ago).count()
    for k, v in sorted(customer_growth.items()):
        running_total += v
        growth_data.append({'date': k, 'customers': running_total})
    
    completion_rate = [
        {'name': 'Completed', 'value': completed_orders},
        {'name': 'Pending', 'value': pending_orders},
        {'name': 'Cancelled', 'value': cancelled_orders}
    ]
    
    return jsonify({
        'revenueTrends': trend_data,
        'topProducts': top_products_data,
        'customerGrowth': growth_data,
        'orderCompletion': completion_rate
    })

@app.route('/')
def home():
    return jsonify({'message': 'DukaanAI API is running!'})

# ========== WHATSAPP BOT ==========
def get_ai_response_bot(customer, message):
    """AI response with multiple Gemini model fallback"""
    
    # List of models to try in order (without 'models/' prefix)
    models_to_try = [
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-flash-latest',
        'gemini-pro',
        'gemini-1.0-pro'
    ]
    
    # Get products for context
    products = Product.query.limit(3).all()
    product_list = "\n".join([f"{p.name}: ₹{p.price}" for p in products]) if products else "कोई प्रोडक्ट नहीं"
    
    prompt = f"""Customer: {customer.name}
Balance: ₹{customer.balance}
Message: {message}
Products: {product_list}

Short Hinglish reply (1-2 lines):"""
    
    # Try each model until one works
    for model_name in models_to_try:
        try:
            print(f"🤖 Trying model: {model_name}")
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.5,
                    'max_output_tokens': 100
                }
            )
            
            ai_response = response.text.strip()
            print(f"✅ Success with model: {model_name}")
            return ai_response
            
        except Exception as e:
            print(f"⚠️ Model {model_name} failed: {e}")
            continue
    
    # If all models fail
    print("❌ All models failed")
    return "थोड़ी देर में try करें। 🙏"

def process_whatsapp_message(from_number, body):
    """Process message and send reply via Twilio"""
    # Remove any leading "Please wait" from message history
    body = body.replace("Please wait", "").strip()
    
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

            ai_reply = get_ai_response_bot(customer, body)

        twilio_client.messages.create(
            body=ai_reply,
            from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
            to=from_number
        )
        print(f"✅ Replied to {from_number}: {ai_reply[:50]}...")
    except Exception as e:
        print(f"❌ WhatsApp error: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    """WhatsApp webhook - processes message and replies directly (no 'please wait')"""
    from_number = request.form.get('From')
    body = request.form.get('Body', '').strip()
    print(f"📲 Message from {from_number}: {body}")
    # Process in background thread so Twilio doesn't timeout
    executor.submit(process_whatsapp_message, from_number, body)
    return "OK", 200


# Create tables
with app.app_context():
    db.create_all()
    print("✅ Database tables created!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)