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
import threading
import time
from concurrent.futures import ThreadPoolExecutor

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

# Thread pool for async processing
executor = ThreadPoolExecutor(max_workers=5)

# ========== DATABASE MODELS ==========
class Business(db.Model):
    __tablename__ = 'business'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    business_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    phone = db.Column(db.String(20), index=True)
    name = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0)
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    last_order_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    name = db.Column(db.String(200))
    price = db.Column(db.Float)
    unit = db.Column(db.String(20))
    stock = db.Column(db.Integer, default=0)
    total_sold = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    items = db.Column(db.Text)
    total = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending', index=True)
    source = db.Column(db.String(20), default='whatsapp')
    payment_method = db.Column(db.String(20), default='cash')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)

class Conversation(db.Model):
    __tablename__ = 'conversation'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TempOrder(db.Model):
    __tablename__ = 'temp_order'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), index=True)
    product_id = db.Column(db.Integer)
    product_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer)
    unit = db.Column(db.String(20))
    price = db.Column(db.Float)
    total = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=5))

# Create tables
with app.app_context():
    db.create_all()
    print("✅ Database created/verified!")

    # Create a default business if none exists
    if not Business.query.first():
        default_business = Business(
            phone="owner",
            name="Test Shop",
            business_name="DukaanAI Demo"
        )
        db.session.add(default_business)
        db.session.commit()
        print("✅ Default business created")
    
    # Add sample products if none exist
    if Product.query.count() == 0:
        business = Business.query.first()
        products = [
            Product(business_id=business.id, name="गोल्ड चाय पत्ती", price=250, unit="kg", stock=15, total_sold=0),
            Product(business_id=business.id, name="Tata नमक", price=25, unit="kg", stock=8, total_sold=0),
            Product(business_id=business.id, name="फोर्ट बिस्कुट", price=10, unit="piece", stock=45, total_sold=0)
        ]
        db.session.add_all(products)
        db.session.commit()
        print("✅ Sample products added")
    
    # Add sample customers if none exist
    if Customer.query.count() == 0:
        business = Business.query.first()
        customers = [
            Customer(business_id=business.id, name="रमेश कुमार", phone="9876543210", balance=500),
            Customer(business_id=business.id, name="सुरेश पटेल", phone="9876543211", balance=250),
            Customer(business_id=business.id, name="महेश शर्मा", phone="9876543212", balance=0)
        ]
        db.session.add_all(customers)
        db.session.commit()
        print("✅ Sample customers added")

# ========== ORDER CREATION FUNCTION ==========
def create_order_from_temp(temp_order):
    """Create actual order from temp order"""
    try:
        customer = Customer.query.get(temp_order.customer_id)
        product = Product.query.get(temp_order.product_id)
        
        if not customer or not product:
            return False, "Customer or product not found"
        
        if product.stock < temp_order.quantity:
            return False, f"Only {product.stock} {product.unit} available"
        
        items = json.dumps([{
            'product_id': product.id,
            'name': product.name,
            'quantity': temp_order.quantity,
            'price': product.price
        }])
        
        order = Order(
            business_id=customer.business_id,
            customer_id=customer.id,
            items=items,
            total=temp_order.total,
            status='pending',
            source='whatsapp',
            payment_method='cash',
            created_at=datetime.utcnow()
        )
        
        db.session.add(order)
        
        # Update stock and customer stats
        product.stock -= temp_order.quantity
        product.total_sold += temp_order.quantity
        customer.total_orders += 1
        customer.total_spent += temp_order.total
        customer.last_order_date = datetime.utcnow()
        
        db.session.delete(temp_order)
        db.session.commit()
        
        return True, order
        
    except Exception as e:
        print(f"❌ Error creating order from temp: {e}")
        db.session.rollback()
        return False, str(e)

# ========== AI FUNCTIONS WITH CONFIRMATION ==========
def get_ai_response(customer, message):
    """AI response with order confirmation"""
    start_time = time.time()
    
    try:
        print(f"\n🤖 Processing: {message[:30]}...")
        
        # Check for pending temp order
        pending_order = TempOrder.query.filter_by(customer_id=customer.id).first()
        
        if pending_order:
            if datetime.utcnow() > pending_order.expires_at:
                db.session.delete(pending_order)
                db.session.commit()
                pending_order = None
                print("🧹 Expired temp order cleaned up")
            else:
                msg_lower = message.lower()
                
                confirm_words = ['ha', 'han', 'haan', 'yes', 'confirm', 'ok', 'ठीक है', 'हाँ', 'कन्फर्म']
                cancel_words = ['nahi', 'no', 'cancel', 'mat karo', 'नहीं', 'कैंसल']
                
                if any(word in msg_lower for word in confirm_words):
                    success, result = create_order_from_temp(pending_order)
                    if success:
                        order = result
                        return f"""✅ *ऑर्डर कन्फर्म!*

{pending_order.quantity} {pending_order.unit} {pending_order.product_name}
कुल: ₹{pending_order.total}

ऑर्डर ID: #{order.id}

धन्यवाद! 🙏"""
                    else:
                        return f"❌ {result}"
                
                elif any(word in msg_lower for word in cancel_words):
                    db.session.delete(pending_order)
                    db.session.commit()
                    return "❌ ऑर्डर कैंसल कर दिया गया।"
                
                else:
                    minutes_left = max(1, int((pending_order.expires_at - datetime.utcnow()).total_seconds() / 60))
                    return f"""🤔 *ऑर्डर पेंडिंग है*

{pending_order.quantity} {pending_order.unit} {pending_order.product_name}
कुल: ₹{pending_order.total}

✅ *कन्फर्म के लिए*: "ha" या "confirm" लिखें
❌ *कैंसल के लिए*: "nahi" या "cancel" लिखें

⏳ {minutes_left} मिनट बचे हैं।"""
        
        # Check for new order patterns
        message_lower = message.lower()
        
        patterns = [
            (r'(\d+)\s*(?:kg|किलो)\s*(?:चाय|chai|tea|patti)', 'चाय', 'kg'),
            (r'(\d+)\s*(?:kg|किलो)\s*(?:नमक|namak|salt)', 'नमक', 'kg'),
            (r'(\d+)\s*(?:piece|पीस)\s*(?:बिस्कुट|biscuit)', 'बिस्कुट', 'piece'),
            (r'(?:चाय|chai|tea|patti)\s*(\d+)\s*(?:kg|किलो)', 'चाय', 'kg'),
            (r'(?:नमक|namak|salt)\s*(\d+)\s*(?:kg|किलो)', 'नमक', 'kg'),
            (r'(?:बिस्कुट|biscuit)\s*(\d+)\s*(?:piece|पीस)', 'बिस्कुट', 'piece'),
        ]
        
        order_detected = False
        for pattern, product_type, unit in patterns:
            match = re.search(pattern, message_lower)
            if match:
                quantity = int(match.group(1))
                print(f"🔍 Order detected: {product_type} {quantity} {unit}")
                order_detected = True
                
                product = None
                if product_type == 'चाय':
                    product = Product.query.filter(Product.name.contains('चाय')).first()
                elif product_type == 'नमक':
                    product = Product.query.filter(Product.name.contains('नमक')).first()
                elif product_type == 'बिस्कुट':
                    product = Product.query.filter(Product.name.contains('बिस्कुट')).first()
                
                if product:
                    if product.stock < quantity:
                        return f"❌ केवल {product.stock} {product.unit} स्टॉक में है।"
                    
                    total = product.price * quantity
                    
                    temp_order = TempOrder(
                        customer_id=customer.id,
                        product_id=product.id,
                        product_name=product.name,
                        quantity=quantity,
                        unit=unit,
                        price=product.price,
                        total=total
                    )
                    db.session.add(temp_order)
                    db.session.commit()
                    
                    return f"""🤔 *कन्फर्मेशन*

{quantity} {unit} {product.name}
कुल: ₹{total}

✅ *कन्फर्म के लिए*: "ha" या "confirm"
❌ *कैंसल के लिए*: "nahi" या "cancel"

कन्फर्म करना है?"""
        
        if not order_detected:
            products = Product.query.limit(3).all()
            product_list = "\n".join([f"{p.name}: ₹{p.price}" for p in products]) if products else "कोई प्रोडक्ट नहीं"
            
            recent_chats = Conversation.query.filter_by(customer_id=customer.id).order_by(Conversation.created_at.desc()).limit(2).all()
            recent_chats.reverse()
            chat_history = ""
            for chat in recent_chats:
                chat_history += f"User: {chat.message}\nBot: {chat.response}\n"
            
            prompt = f"""Customer: {customer.name}
Balance: ₹{customer.balance}
Message: {message}
Products: {product_list}

Short Hinglish reply (1-2 lines):"""

            print(f"📝 Sending to Gemini 1.5 Flash...")
            
            try:
                response = gemini_client.models.generate_content(
                    model='models/gemini-1.5-flash',
                    contents=prompt,
                    config={
                        'temperature': 0.5,
                        'max_output_tokens': 80,
                        'top_p': 0.8
                    }
                )
                ai_response = response.text.strip()
            except Exception as ai_error:
                print(f"❌ Gemini API Error: {ai_error}")
                ai_response = "थोड़ी देर में try करें। 😊"
            
            conv = Conversation(customer_id=customer.id, message=message, response=ai_response)
            db.session.add(conv)
            db.session.commit()
            
            end_time = time.time()
            print(f"✅ Response time: {end_time - start_time:.2f}s")
            
            return ai_response
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return "ज़रा रुको, फिर से try करो 🙏"

# ========== ASYNC WEBHOOK HANDLER ==========
def send_quick_ack(from_number):
    try:
        twilio_client.messages.create(
            body="⏳ Please wait...",
            from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
            to=from_number
        )
    except Exception as e:
        print(f"❌ Ack Error: {e}")

def process_ai_response_async(from_number, body, customer):
    try:
        response = get_ai_response(customer, body)
        twilio_client.messages.create(
            body=response,
            from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
            to=from_number
        )
    except Exception as e:
        print(f"❌ Process Error: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form
    from_number = data.get('From')
    body = data.get('Body', '').strip()
    
    print(f"\n📩 New message from {from_number}")
    
    customer = Customer.query.filter_by(phone=from_number).first()
    if not customer:
        business = Business.query.first()
        customer = Customer(
            business_id=business.id,
            phone=from_number,
            name=f"User_{from_number[-4:]}"
        )
        db.session.add(customer)
        db.session.commit()
        print(f"✅ New customer: {customer.name}")
    
    executor.submit(send_quick_ack, from_number)
    executor.submit(process_ai_response_async, from_number, body, customer)
    
    return "OK", 200

# ========== HEALTH AND STATUS ENDPOINTS ==========
@app.route('/')
def home():
    return "✅ DukaanAI Bot with Order Confirmation!"

@app.route('/health')
def health():
    return jsonify({
        "status": "alive",
        "time": datetime.now().isoformat(),
        "version": "2.0"
    })

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
            'date': o.created_at.strftime('%Y-%m-%d')
        })
    return jsonify(result)

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
    temp_orders = TempOrder.query.count()
    
    return jsonify({
        'today': {'orders': today_orders, 'revenue': float(today_revenue)},
        'pending': pending_orders,
        'lowStock': low_stock,
        'customers': {'total': customers, 'new': new_customers},
        'tempOrders': temp_orders
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 DukaanAI Bot with Order Confirmation")
    print("="*60)
    print(f"🤖 Model: Gemini 1.5 Flash")
    print("✅ Order Confirmation: Enabled")
    print("✅ Temp Orders: 5 min expiry")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)