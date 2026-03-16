from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import json
import re
from dotenv import load_dotenv
import sys
import io
from twilio.rest import Client
from google import genai
import traceback

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for frontend
CORS(app)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dukaanai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Initialize Twilio client
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Initialize Google Gemini
gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# ========== DATABASE MODELS ==========
class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    business_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    phone = db.Column(db.String(20))
    name = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0)
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    last_order_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    name = db.Column(db.String(200))
    price = db.Column(db.Float)
    unit = db.Column(db.String(20))
    stock = db.Column(db.Integer, default=0)
    total_sold = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    items = db.Column(db.Text)
    total = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')
    source = db.Column(db.String(20), default='whatsapp')
    payment_method = db.Column(db.String(20), default='cash')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Database created fresh!")

    # Create a default business
    default_business = Business(
        phone="owner",
        name="Test Shop",
        business_name="DukaanAI Demo"
    )
    db.session.add(default_business)
    db.session.commit()
    print("✅ Default business created")
    
    # Add sample products
    business = Business.query.first()
    products = [
        Product(business_id=business.id, name="गोल्ड चाय पत्ती", price=250, unit="kg", stock=15, total_sold=0),
        Product(business_id=business.id, name="Tata नमक", price=25, unit="kg", stock=8, total_sold=0),
        Product(business_id=business.id, name="फोर्ट बिस्कुट", price=10, unit="piece", stock=45, total_sold=0)
    ]
    db.session.add_all(products)
    db.session.commit()
    print("✅ Sample products added")
    
    # Add sample customers
    customers = [
        Customer(business_id=business.id, name="रमेश कुमार", phone="9876543210", balance=500),
        Customer(business_id=business.id, name="सुरेश पटेल", phone="9876543211", balance=250),
        Customer(business_id=business.id, name="महेश शर्मा", phone="9876543212", balance=0)
    ]
    db.session.add_all(customers)
    db.session.commit()
    print("✅ Sample customers added")

# ========== ORDER CREATION FUNCTION ==========
def create_order(from_number, product_name, quantity):
    """Create a new order in database"""
    try:
        print(f"\n📦 Creating order: {product_name} x{quantity} for {from_number}")
        
        # Get customer
        customer = Customer.query.filter_by(phone=from_number).first()
        if not customer:
            print("❌ Customer not found")
            return "❌ Customer not found"
        
        # Find product
        product = None
        product_search = product_name.lower()
        
        # Product mapping
        if any(word in product_search for word in ['चावल', 'rice', 'chawal']):
            product = Product.query.filter(Product.name.contains('चावल')).first()
        elif any(word in product_search for word in ['नमक', 'salt', 'namak']):
            product = Product.query.filter(Product.name.contains('नमक')).first()
        elif any(word in product_search for word in ['चाय', 'tea', 'chai', 'patti']):
            product = Product.query.filter(Product.name.contains('चाय')).first()
        elif any(word in product_search for word in ['बिस्कुट', 'biscuit']):
            product = Product.query.filter(Product.name.contains('बिस्कुट')).first()
        
        if not product:
            print(f"❌ Product '{product_name}' not found")
            return f"❌ प्रोडक्ट '{product_name}' नहीं मिला। प्रोडक्ट लिस्ट के लिए 'product' लिखें।"
        
        print(f"✅ Found product: {product.name} (Stock: {product.stock})")
        
        # Check stock
        if product.stock < quantity:
            print(f"❌ Insufficient stock: have {product.stock}, need {quantity}")
            return f"❌ केवल {product.stock} {product.unit} स्टॉक में है।"
        
        # Create order items JSON
        items = json.dumps([{
            'product_id': product.id,
            'name': product.name,
            'quantity': quantity,
            'price': product.price
        }])
        
        total = product.price * quantity
        
        # Create order
        order = Order(
            business_id=customer.business_id,
            customer_id=customer.id,
            items=items,
            total=total,
            status='pending',
            source='whatsapp',
            payment_method='cash',
            created_at=datetime.utcnow()
        )
        
        db.session.add(order)
        
        # Update stock and customer stats
        old_stock = product.stock
        product.stock -= quantity
        product.total_sold += quantity
        customer.total_orders += 1
        customer.total_spent += total
        customer.last_order_date = datetime.utcnow()
        
        print(f"📊 Stock updated: {old_stock} -> {product.stock}")
        
        # Commit all changes
        db.session.commit()
        print(f"✅ Order #{order.id} created successfully")
        
        return f"""✅ *ऑर्डर कन्फर्म!*

{quantity} {product.unit} {product.name}
कुल: ₹{total}

ऑर्डर ID: #{order.id}

धन्यवाद! 🙏"""
        
    except Exception as e:
        print(f"❌ Error creating order: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return "❌ ऑर्डर बनाने में समस्या हुई। कृपया बाद में try करें।"

# ========== AI FUNCTIONS ==========
def get_ai_response(customer, message):
    """Get AI-powered response using Google Gemini"""
    try:
        print(f"\n🤖 Getting Gemini response for: {message}")
        
        # Get recent conversation history
        recent_chats = Conversation.query.filter_by(customer_id=customer.id).order_by(Conversation.created_at.desc()).limit(5).all()
        recent_chats.reverse()
        
        # Get products for context
        products = Product.query.all()
        product_list = "\n".join([f"- {p.name}: ₹{p.price} per {p.unit} (स्टॉक: {p.stock})" for p in products])
        
        # Get customer's orders
        orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).limit(3).all()
        order_list = "\n".join([f"- ऑर्डर #{o.id}: ₹{o.total} - {o.status}" for o in orders]) if orders else "कोई ऑर्डर नहीं"
        
        # Create prompt with order creation instruction
        prompt = f"""You are DukaanAI, a friendly Hindi/English WhatsApp assistant for a small Indian shop.

Customer Name: {customer.name}
Customer Balance: ₹{customer.balance}
Total Orders: {customer.total_orders}
Total Spent: ₹{customer.total_spent}

Available Products:
{product_list}

Recent Orders:
{order_list}

Current message: "{message}"

CRITICAL INSTRUCTION - ORDER DETECTION:
If the message contains a product name AND a quantity (like "2 kg chai", "do kg namak", "5 piece biscuit"), you MUST:
1. Detect the product and quantity
2. Create the order immediately
3. Respond with order confirmation including the order ID
4. DO NOT ask for confirmation - create order directly

Examples:
- "2 kg chai" → Create order for 2kg tea
- "5 नमक" → Create order for 5kg salt  
- "ek kilo biscuit" → Create order for 1kg biscuit

Otherwise, respond normally:
1. Respond in Hinglish (mix of Hindi and English)
2. Be warm, friendly, and helpful
3. Use emojis occasionally 😊
4. If they ask about products, list them
5. If they ask about balance, tell them
6. Keep responses concise (2-3 sentences)

Response:"""

        print(f"📝 Sending to Gemini...")
        
        # Get AI response
        response = gemini_client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=prompt
        )
        
        ai_response = response.text.strip()
        print(f"✅ AI response received")
        
        # Also check manually for order patterns (backup)
        message_lower = message.lower()
        
        # Pattern: number + kg/piece + product
        patterns = [
            (r'(\d+)\s*(?:kg|किलो)\s*(?:चाय|chai|tea|patti)', 'चाय'),
            (r'(\d+)\s*(?:kg|किलो)\s*(?:नमक|namak|salt)', 'नमक'),
            (r'(\d+)\s*(?:piece|पीस)\s*(?:बिस्कुट|biscuit)', 'बिस्कुट'),
            (r'(?:चाय|chai|tea|patti)\s*(\d+)\s*(?:kg|किलो)', 'चाय'),
            (r'(?:नमक|namak|salt)\s*(\d+)\s*(?:kg|किलो)', 'नमक'),
            (r'(?:बिस्कुट|biscuit)\s*(\d+)\s*(?:piece|पीस)', 'बिस्कुट')
        ]
        
        for pattern, product_type in patterns:
            match = re.search(pattern, message_lower)
            if match:
                quantity = int(match.group(1))
                print(f"🔍 Manual pattern detected: {product_type} {quantity}")
                order_result = create_order(customer.phone, product_type, quantity)
                ai_response = order_result
                break
        
        # Save to conversation history
        conv = Conversation(
            customer_id=customer.id,
            message=message,
            response=ai_response
        )
        db.session.add(conv)
        db.session.commit()
        
        return ai_response
        
    except Exception as e:
        print(f"\n❌ ERROR in get_ai_response: {type(e).__name__}: {e}")
        traceback.print_exc()
        return "🤖 माफ करें, अभी थोड़ी समस्या है। कृपया थोड़ी देर में try करें।"

# ========== WHATSAPP MESSAGE HANDLING ==========
@app.route('/')
def home():
    return "✅ AI-Powered DukaanAI WhatsApp Bot is Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Receive messages from WhatsApp via Twilio"""
    data = request.form
    
    from_number = data.get('From')
    body = data.get('Body', '').strip()
    
    print(f"\n📩 WhatsApp message from {from_number}: {body}")
    
    # Get or create customer
    customer = Customer.query.filter_by(phone=from_number).first()
    if not customer:
        business = Business.query.first()
        customer = Customer(
            business_id=business.id,
            phone=from_number,
            name=f"Customer_{from_number[-4:]}"
        )
        db.session.add(customer)
        db.session.commit()
        print(f"✅ New customer created: {customer.name}")
    
    # Get AI response
    response_text = get_ai_response(customer, body)
    
    # Send response back via WhatsApp
    if response_text:
        try:
            message = twilio_client.messages.create(
                body=response_text,
                from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
                to=from_number
            )
            print(f"✅ Message sent! SID: {message.sid}")
        except Exception as e:
            print(f"❌ Twilio Error: {e}")
    
    return "OK", 200

# ========== API ENDPOINTS ==========
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': p.price,
        'stock': p.stock,
        'unit': p.unit,
        'total_sold': p.total_sold
    } for p in products])

@app.route('/api/products', methods=['POST'])
def create_product():
    """Add a new product"""
    try:
        data = request.json
        print(f"📥 Received product data: {data}")
        
        business = Business.query.first()
        
        new_product = Product(
            business_id=business.id,
            name=data['name'],
            price=float(data['price']),
            unit=data['unit'],
            stock=int(data['stock']),
            total_sold=0
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        print(f"✅ Product added: {new_product.name}")
        
        return jsonify({
            'success': True,
            'product': {
                'id': new_product.id,
                'name': new_product.name,
                'price': new_product.price,
                'unit': new_product.unit,
                'stock': new_product.stock
            }
        }), 201
        
    except Exception as e:
        print(f"❌ Error adding product: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'balance': c.balance,
        'total_orders': c.total_orders,
        'total_spent': c.total_spent,
        'last_order_date': c.last_order_date.strftime('%Y-%m-%d') if c.last_order_date else 'Never',
        'created_at': c.created_at.strftime('%Y-%m-%d')
    } for c in customers])

@app.route('/api/orders', methods=['GET'])
def get_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        customer = Customer.query.get(o.customer_id)
        result.append({
            'id': o.id,
            'customer': customer.name if customer else 'Unknown',
            'total': o.total,
            'status': o.status,
            'source': o.source,
            'payment_method': o.payment_method,
            'date': o.created_at.strftime('%Y-%m-%d'),
            'time': o.created_at.strftime('%H:%M')
        })
    return jsonify(result)

@app.route('/api/orders/<int:order_id>', methods=['PATCH'])
def update_order_status(order_id):
    """Update order status"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        data = request.json
        order.status = data.get('status', order.status)
        
        db.session.commit()
        
        return jsonify({'success': True, 'status': order.status})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    today_orders = Order.query.filter(db.func.date(Order.created_at) == today).count()
    today_revenue = db.session.query(db.func.sum(Order.total)).filter(db.func.date(Order.created_at) == today).scalar() or 0
    pending_orders = Order.query.filter_by(status='pending').count()
    low_stock = Product.query.filter(Product.stock < 10).count()
    customers = Customer.query.count()
    new_customers = Customer.query.filter(db.func.date(Customer.created_at) >= week_ago).count()
    
    return jsonify({
        'today': {'orders': today_orders, 'revenue': float(today_revenue)},
        'pending': pending_orders,
        'lowStock': low_stock,
        'customers': {'total': customers, 'new': new_customers}
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting AI-Powered DukaanAI Bot")
    print("="*60)
    print(f"📱 Twilio Number: {os.getenv('TWILIO_WHATSAPP_NUMBER')}")
    print(f"🤖 Google Gemini: {'✅ Connected' if os.getenv('GEMINI_API_KEY') else '❌ Missing'}")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)