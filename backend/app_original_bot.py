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
import traceback
import time
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai

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

# Configure Gemini with latest API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Available Gemini models (latest)
# gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro, gemini-pro
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

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
    print("Γ£à Database created/verified!")

    # Create a default business if none exists
    if not Business.query.first():
        default_business = Business(
            phone="owner",
            name="Test Shop",
            business_name="DukaanAI Demo"
        )
        db.session.add(default_business)
        db.session.commit()
        print("Γ£à Default business created")
    
    # Add sample products if none exist
    if Product.query.count() == 0:
        business = Business.query.first()
        products = [
            Product(business_id=business.id, name="αñùαÑïαñ▓αÑìαñí αñÜαñ╛αñ» αñ¬αññαÑìαññαÑÇ", price=250, unit="kg", stock=15, total_sold=0),
            Product(business_id=business.id, name="Tata αñ¿αñ«αñò", price=25, unit="kg", stock=8, total_sold=0),
            Product(business_id=business.id, name="αñ½αÑïαñ░αÑìαñƒ αñ¼αñ┐αñ╕αÑìαñòαÑüαñƒ", price=10, unit="piece", stock=45, total_sold=0)
        ]
        db.session.add_all(products)
        db.session.commit()
        print("Γ£à Sample products added")
    
    # Add sample customers if none exist
    if Customer.query.count() == 0:
        business = Business.query.first()
        customers = [
            Customer(business_id=business.id, name="αñ░αñ«αÑçαñ╢ αñòαÑüαñ«αñ╛αñ░", phone="9876543210", balance=500),
            Customer(business_id=business.id, name="αñ╕αÑüαñ░αÑçαñ╢ αñ¬αñƒαÑçαñ▓", phone="9876543211", balance=250),
            Customer(business_id=business.id, name="αñ«αñ╣αÑçαñ╢ αñ╢αñ░αÑìαñ«αñ╛", phone="9876543212", balance=0)
        ]
        db.session.add_all(customers)
        db.session.commit()
        print("Γ£à Sample customers added")

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
        print(f"Γ¥î Error creating order from temp: {e}")
        db.session.rollback()
        return False, str(e)

# ========== AI FUNCTIONS WITH LATEST GEMINI ==========
def get_ai_response(customer, message):
    """AI response with latest Gemini model"""
    start_time = time.time()
    
    try:
        print(f"\n≡ƒñû Processing with {GEMINI_MODEL}: {message[:30]}...")
        
        # Check for pending temp order
        pending_order = TempOrder.query.filter_by(customer_id=customer.id).first()
        
        if pending_order:
            if datetime.utcnow() > pending_order.expires_at:
                db.session.delete(pending_order)
                db.session.commit()
                pending_order = None
                print("≡ƒº╣ Expired temp order cleaned up")
            else:
                msg_lower = message.lower()
                
                confirm_words = ['ha', 'han', 'haan', 'yes', 'confirm', 'ok', 'αñáαÑÇαñò αñ╣αÑê', 'αñ╣αñ╛αñü', 'αñòαñ¿αÑìαñ½αñ░αÑìαñ«']
                cancel_words = ['nahi', 'no', 'cancel', 'mat karo', 'αñ¿αñ╣αÑÇαñé', 'αñòαÑêαñéαñ╕αñ▓']
                
                if any(word in msg_lower for word in confirm_words):
                    success, result = create_order_from_temp(pending_order)
                    if success:
                        order = result
                        return f"""Γ£à *αñæαñ░αÑìαñíαñ░ αñòαñ¿αÑìαñ½αñ░αÑìαñ«!*

{pending_order.quantity} {pending_order.unit} {pending_order.product_name}
αñòαÑüαñ▓: Γé╣{pending_order.total}

αñæαñ░αÑìαñíαñ░ ID: #{order.id}

αñºαñ¿αÑìαñ»αñ╡αñ╛αñª! ≡ƒÖÅ"""
                    else:
                        return f"Γ¥î {result}"
                
                elif any(word in msg_lower for word in cancel_words):
                    db.session.delete(pending_order)
                    db.session.commit()
                    return "Γ¥î αñæαñ░αÑìαñíαñ░ αñòαÑêαñéαñ╕αñ▓ αñòαñ░ αñªαñ┐αñ»αñ╛ αñùαñ»αñ╛αÑñ"
                
                else:
                    minutes_left = max(1, int((pending_order.expires_at - datetime.utcnow()).total_seconds() / 60))
                    return f"""≡ƒñö *αñæαñ░αÑìαñíαñ░ αñ¬αÑçαñéαñíαñ┐αñéαñù αñ╣αÑê*

{pending_order.quantity} {pending_order.unit} {pending_order.product_name}
αñòαÑüαñ▓: Γé╣{pending_order.total}

Γ£à *αñòαñ¿αÑìαñ½αñ░αÑìαñ« αñòαÑç αñ▓αñ┐αñÅ*: "ha" αñ»αñ╛ "confirm"
Γ¥î *αñòαÑêαñéαñ╕αñ▓ αñòαÑç αñ▓αñ┐αñÅ*: "nahi" αñ»αñ╛ "cancel"

ΓÅ│ {minutes_left} αñ«αñ┐αñ¿αñƒ αñ¼αñÜαÑç αñ╣αÑêαñéαÑñ"""
        
        # Check for new order patterns
        message_lower = message.lower()
        
        patterns = [
            (r'(\d+)\s*(?:kg|αñòαñ┐αñ▓αÑï)\s*(?:αñÜαñ╛αñ»|chai|tea|patti)', 'αñÜαñ╛αñ»', 'kg'),
            (r'(\d+)\s*(?:kg|αñòαñ┐αñ▓αÑï)\s*(?:αñ¿αñ«αñò|namak|salt)', 'αñ¿αñ«αñò', 'kg'),
            (r'(\d+)\s*(?:piece|αñ¬αÑÇαñ╕)\s*(?:αñ¼αñ┐αñ╕αÑìαñòαÑüαñƒ|biscuit)', 'αñ¼αñ┐αñ╕αÑìαñòαÑüαñƒ', 'piece'),
        ]
        
        for pattern, product_type, unit in patterns:
            match = re.search(pattern, message_lower)
            if match:
                quantity = int(match.group(1))
                print(f"≡ƒöì Order detected: {product_type} {quantity} {unit}")
                
                product = None
                if product_type == 'αñÜαñ╛αñ»':
                    product = Product.query.filter(Product.name.contains('αñÜαñ╛αñ»')).first()
                elif product_type == 'αñ¿αñ«αñò':
                    product = Product.query.filter(Product.name.contains('αñ¿αñ«αñò')).first()
                elif product_type == 'αñ¼αñ┐αñ╕αÑìαñòαÑüαñƒ':
                    product = Product.query.filter(Product.name.contains('αñ¼αñ┐αñ╕αÑìαñòαÑüαñƒ')).first()
                
                if product:
                    if product.stock < quantity:
                        return f"Γ¥î αñòαÑçαñ╡αñ▓ {product.stock} {product.unit} αñ╕αÑìαñƒαÑëαñò αñ«αÑçαñé αñ╣αÑêαÑñ"
                    
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
                    
                    return f"""≡ƒñö *αñòαñ¿αÑìαñ½αñ░αÑìαñ«αÑçαñ╢αñ¿*

{quantity} {unit} {product.name}
αñòαÑüαñ▓: Γé╣{total}

Γ£à *αñòαñ¿αÑìαñ½αñ░αÑìαñ« αñòαÑç αñ▓αñ┐αñÅ*: "ha" αñ»αñ╛ "confirm"
Γ¥î *αñòαÑêαñéαñ╕αñ▓ αñòαÑç αñ▓αñ┐αñÅ*: "nahi" αñ»αñ╛ "cancel"

αñòαñ¿αÑìαñ½αñ░αÑìαñ« αñòαñ░αñ¿αñ╛ αñ╣αÑê?"""
        
        # Normal conversation - use Gemini
        products = Product.query.limit(3).all()
        product_list = "\n".join([f"{p.name}: Γé╣{p.price}" for p in products]) if products else "αñòαÑïαñê αñ¬αÑìαñ░αÑïαñíαñòαÑìαñƒ αñ¿αñ╣αÑÇαñé"
        
        prompt = f"""Customer: {customer.name}
Balance: Γé╣{customer.balance}
Message: {message}
Products: {product_list}

Short Hinglish reply (1-2 lines):"""

        print(f"≡ƒô¥ Sending to {GEMINI_MODEL}...")
        
        # Latest Gemini API call
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.5,
                'max_output_tokens': 80,
                'top_p': 0.8,
                'top_k': 40
            }
        )
        
        ai_response = response.text.strip()
        
        # Save conversation
        conv = Conversation(customer_id=customer.id, message=message, response=ai_response)
        db.session.add(conv)
        db.session.commit()
        
        end_time = time.time()
        print(f"Γ£à Gemini response time: {end_time - start_time:.2f}s")
        
        return ai_response
        
    except Exception as e:
        print(f"Γ¥î Gemini Error: {e}")
        traceback.print_exc()
        return "ΓÜá∩╕Å αñÑαÑïαñíαñ╝αÑÇ αñªαÑçαñ░ αñ«αÑçαñé try αñòαñ░αÑçαñéαÑñ ≡ƒÖÅ"

# ========== ASYNC WEBHOOK HANDLER ==========
def send_quick_ack(from_number):
    """Send immediate acknowledgment"""
    try:
        twilio_client.messages.create(
            body="ΓÅ│ Please wait...",
            from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
            to=from_number
        )
    except Exception as e:
        print(f"Γ¥î Ack Error: {e}")

def process_ai_response_async(from_number, body, customer_data):
    """Process AI in background with app context"""
    try:
        with app.app_context():
            customer = Customer.query.get(customer_data['id'])
            if not customer:
                print(f"Γ¥î Customer not found: {customer_data['id']}")
                return
            response = get_ai_response(customer, body)
        
        if response:
            twilio_client.messages.create(
                body=response,
                from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
                to=from_number
            )
    except Exception as e:
        print(f"Γ¥î Process Error: {e}")
        traceback.print_exc()
        try:
            twilio_client.messages.create(
                body="ΓÜá∩╕Å αñÑαÑïαñíαñ╝αÑÇ αñªαÑçαñ░ αñ«αÑçαñé try αñòαñ░αÑçαñéαÑñ ≡ƒÖÅ",
                from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
                to=from_number
            )
        except:
            pass

@app.route('/webhook', methods=['POST'])
def webhook():
    """Async webhook handler with proper app context"""
    data = request.form
    from_number = data.get('From')
    body = data.get('Body', '').strip()
    
    print(f"\n≡ƒô⌐ New message from {from_number}")
    
    with app.app_context():
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
            print(f"Γ£à New customer: {customer.name}")
        
        customer_data = {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'balance': customer.balance
        }
    
    # Process AI directly (no 'please wait' acknowledgment)
    executor.submit(process_ai_response_async, from_number, body, customer_data)
    
    return "OK", 200

# ========== HEALTH AND STATUS ENDPOINTS ==========
@app.route('/')
def home():
    return f"Γ£à DukaanAI Bot with {GEMINI_MODEL}!"

@app.route('/health')
def health():
    return jsonify({
        "status": "alive",
        "time": datetime.now().isoformat(),
        "version": "2.0",
        "model": GEMINI_MODEL
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
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "="*60)
    print("≡ƒÜÇ DukaanAI Bot with Latest Gemini API")
    print("="*60)
    print(f"≡ƒñû Model: {GEMINI_MODEL}")
    print(f"Γ£à Port: {port}")
    print("Γ£à Order Confirmation: Enabled")
    print("Γ£à Temp Orders: 5 min expiry")
    print("="*60 + "\n")
    app.run(debug=False, host='0.0.0.0', port=port)
