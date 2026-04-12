"""
DukaanAI - WhatsApp Business Assistant
Phase 1 Complete - Auto Table Creation on Startup
"""

import os
import json
import re
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dukaanai.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)

# Constants
SHOPKEEPER_PHONE = os.getenv('SHOPKEEPER_PHONE', '')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE = os.getenv('TWILIO_PHONE') or os.getenv('TWILIO_WHATSAPP_NUMBER', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Twilio client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("✅ Twilio client initialized")
    except Exception as e:
        logger.error(f"❌ Twilio client error: {e}")

# ============================================
# DATABASE MODELS
# ============================================

class Business(db.Model):
    __tablename__ = 'business'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default='DukaanAI Store')
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    shop_latitude = db.Column(db.Numeric(10, 8))
    shop_longitude = db.Column(db.Numeric(11, 8))
    shop_landmark = db.Column(db.Text)
    shop_hours = db.Column(db.String(100), default='8 AM - 10 PM')
    welcome_message = db.Column(db.Text)
    product_visibility = db.Column(db.String(20), default='public')
    allow_price_inquiry = db.Column(db.Boolean, default=True)
    greeting_style = db.Column(db.String(20), default='friendly')
    ai_enabled = db.Column(db.Boolean, default=True)
    preferred_language = db.Column(db.String(10), default='hi')
    upi_id = db.Column(db.String(100))
    gstin = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address,
            'shop_latitude': float(self.shop_latitude) if self.shop_latitude else None,
            'shop_longitude': float(self.shop_longitude) if self.shop_longitude else None,
            'shop_landmark': self.shop_landmark,
            'shop_hours': self.shop_hours,
            'product_visibility': self.product_visibility,
            'greeting_style': self.greeting_style,
            'preferred_language': self.preferred_language,
            'upi_id': self.upi_id,
            'ai_enabled': self.ai_enabled
        }

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    name = db.Column(db.String(200))
    phone = db.Column(db.String(20), nullable=False)
    balance = db.Column(db.Numeric(10, 2), default=0)
    language_pref = db.Column(db.String(10), default='hi')
    visit_count = db.Column(db.Integer, default=0)
    last_visit = db.Column(db.DateTime)
    home_store_id = db.Column(db.Integer)
    is_verified = db.Column(db.Boolean, default=False)
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_reminder_date = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'balance': float(self.balance) if self.balance else 0,
            'language_pref': self.language_pref,
            'visit_count': self.visit_count,
            'total_orders': self.total_orders,
            'total_spent': float(self.total_spent) if self.total_spent else 0
        }

class Product(db.Model):
    __tablename__ = 'products_new'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    category = db.Column(db.String(100))
    brand = db.Column(db.String(100))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_loose = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        variants = ProductVariant.query.filter_by(product_id=self.id).all()
        return {
            'id': self.id,
            'category': self.category,
            'brand': self.brand,
            'name': self.name,
            'full_name': f"{self.brand} {self.name}".strip() if self.brand else self.name,
            'is_loose': self.is_loose,
            'variants': [v.to_dict() for v in variants]
        }

class ProductVariant(db.Model):
    __tablename__ = 'product_variants'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products_new.id'))
    weight = db.Column(db.Numeric(10, 3))
    unit = db.Column(db.String(10), default='kg')
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'weight': float(self.weight) if self.weight else None,
            'unit': self.unit,
            'price': float(self.price) if self.price else 0,
            'stock': self.stock,
            'display': f"{self.weight}{self.unit} - ₹{self.price}"
        }

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    items = db.Column(db.Text)
    total = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(50), default='pending')
    source = db.Column(db.String(50), default='whatsapp')
    payment_mode = db.Column(db.String(20))
    payment_status = db.Column(db.String(20), default='pending')
    payment_received_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    udhaar_balance_used = db.Column(db.Numeric(10, 2), default=0)
    stock_already_reduced = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def get_items(self):
        return json.loads(self.items) if self.items else []
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else 'Walk-in',
            'items': self.get_items(),
            'total': float(self.total) if self.total else 0,
            'status': self.status,
            'payment_mode': self.payment_mode,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ConversationState(db.Model):
    __tablename__ = 'conversation_state'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False)
    store_id = db.Column(db.Integer)
    state = db.Column(db.String(50))
    context = db.Column(db.Text)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_context(self):
        return json.loads(self.context) if self.context else {}
    
    def set_context(self, data):
        self.context = json.dumps(data)

class TempOrder(db.Model):
    __tablename__ = 'temp_order'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    business_id = db.Column(db.Integer)
    items = db.Column(db.Text)
    total = db.Column(db.Numeric(10, 2))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BalanceTransaction(db.Model):
    __tablename__ = 'balance_transaction'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer)
    amount = db.Column(db.Numeric(10, 2))
    type = db.Column(db.String(50))
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# FORCE CREATE TABLES ON STARTUP
# ============================================

def init_database():
    """Create all tables and default business"""
    with app.app_context():
        logger.info("🔧 Creating database tables...")
        db.create_all()
        logger.info("✅ Tables created!")
        
        # Create default business
        business = Business.query.first()
        if not business:
            business = Business(
                name='DukaanAI Store',
                phone=SHOPKEEPER_PHONE,
                address='Your Shop Address, City',
                shop_hours='8 AM - 10 PM',
                welcome_message='👋 Welcome to DukaanAI Store! How can I help you today?'
            )
            db.session.add(business)
            db.session.commit()
            logger.info("✅ Default business created!")
        
        logger.info("🎉 Database initialization complete!")

# Run initialization IMMEDIATELY
try:
    init_database()
except Exception as e:
    logger.error(f"❌ Database init error: {e}")

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_or_create_business():
    business = Business.query.first()
    if not business:
        business = Business(
            name='DukaanAI Store',
            phone=SHOPKEEPER_PHONE,
            address='Your Shop Address',
            shop_hours='8 AM - 10 PM'
        )
        db.session.add(business)
        db.session.commit()
    return business

def get_or_create_customer(phone, business_id, name=None):
    customer = Customer.query.filter_by(phone=phone, business_id=business_id).first()
    
    if not customer:
        customer = Customer(
            phone=phone,
            business_id=business_id,
            name=name,
            visit_count=1,
            last_visit=datetime.utcnow()
        )
        db.session.add(customer)
        db.session.commit()
    else:
        customer.visit_count = (customer.visit_count or 0) + 1
        customer.last_visit = datetime.utcnow()
        db.session.commit()
    
    return customer

def send_whatsapp_message(to_phone, message):
    if not twilio_client:
        logger.info(f"[MOCK] To {to_phone}: {message[:50]}...")
        return True
    
    try:
        twilio_client.messages.create(
            body=message,
            from_=f'whatsapp:{TWILIO_PHONE}',
            to=f'whatsapp:{to_phone}'
        )
        return True
    except Exception as e:
        logger.error(f"WhatsApp error: {e}")
        return False

def identify_category(text):
    text = text.lower()
    categories = {
        'tea': ['chai', 'tea', 'चाय'],
        'rice': ['chawal', 'rice', 'चावल'],
        'sugar': ['chini', 'sugar', 'चीनी'],
        'oil': ['tel', 'oil', 'तेल'],
        'dal': ['dal', 'दाल'],
        'milk': ['doodh', 'milk', 'दूध'],
    }
    for category, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return category
    return None

def get_greeting(business, customer):
    style = business.greeting_style
    name = customer.name if customer else None
    
    if name:
        return f"🛍️ Welcome back {name} ji!"
    return f"🛍️ Welcome to {business.name}!"

def get_products_by_category(business_id, category):
    products = Product.query.filter_by(business_id=business_id, category=category).all()
    result = []
    for p in products:
        variants = ProductVariant.query.filter_by(product_id=p.id).filter(ProductVariant.stock > 0).all()
        if variants:
            result.append({'product': p, 'variants': variants})
    return result

def format_product_options(category_products, category_name):
    if not category_products:
        return f"❌ {category_name} stock mein nahi hai."
    
    emoji_map = {'tea': '🍵', 'rice': '🍚', 'sugar': '🍬', 'oil': '🛢️', 'dal': '🫘', 'milk': '🥛'}
    emoji = emoji_map.get(category_name.lower(), '📦')
    
    response = f"{emoji} *{category_name.upper()} Options:*\n\n"
    
    for item in category_products[:3]:
        p = item['product']
        variants = item['variants']
        full_name = f"{p.brand} {p.name}".strip() if p.brand else p.name
        response += f"*{full_name}*\n"
        for v in variants[:3]:
            response += f"  {v.weight}{v.unit} - ₹{v.price}\n"
        response += "\n"
    
    response += f"📦 *Kitna aur kaunsa chahiye?*"
    return response

def save_conversation_state(phone, store_id, state, context):
    existing = ConversationState.query.filter_by(phone=phone).first()
    if existing:
        existing.state = state
        existing.set_context(context)
        existing.expires_at = datetime.utcnow() + timedelta(minutes=30)
    else:
        new_state = ConversationState(
            phone=phone, store_id=store_id, state=state,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        new_state.set_context(context)
        db.session.add(new_state)
    db.session.commit()

def get_conversation_state(phone):
    state = ConversationState.query.filter_by(phone=phone).first()
    if state and state.expires_at and state.expires_at > datetime.utcnow():
        return state.state, state.get_context()
    return None, {}

def clear_conversation_state(phone):
    ConversationState.query.filter_by(phone=phone).delete()
    db.session.commit()

def is_simple_command(message):
    simple = ['hi', 'hello', 'product', 'location', 'balance', 'help', 'pending', 'accept', 'payment', 'deliver', 'cancel']
    msg = message.lower().strip()
    if msg in simple:
        return True
    if msg.startswith(('order ', 'accept ', 'payment ', 'deliver ', 'cancel ')):
        return True
    if re.match(r'\d+\s*(kg|g|packet)\s+\w+', msg):
        return True
    return False

def bot_response(message, business, customer, sender_number):
    msg = message.lower().strip()
    
    if msg in ['hi', 'hello', 'hey']:
        return f"{get_greeting(business, customer)}\n\nHow can I help you?\n• product\n• location\n• help"
    
    if msg == 'product':
        greeting = get_greeting(business, customer)
        return f"{greeting}\n\nAapko kya chahiye?\n\nBatayein: chai, chawal, chini, tel, dal"
    
    if msg == 'location':
        if business.shop_latitude and business.shop_longitude:
            link = f"https://maps.google.com/?q={business.shop_latitude},{business.shop_longitude}"
            return f"🏪 *{business.name}*\n📍 {business.address}\n🗺️ {link}\n🕐 {business.shop_hours}"
        return f"🏪 *{business.name}*\n📍 {business.address}\n📞 {business.phone}"
    
    if msg == 'balance':
        if customer:
            if customer.balance > 0:
                return f"💰 Aapki udhaari: ₹{customer.balance}"
            return "✅ Koi udhaari nahi hai!"
        return "❌ Aap registered nahi hain."
    
    if msg == 'help':
        if sender_number == SHOPKEEPER_PHONE:
            return "📋 *Shopkeeper:*\n• pending\n• accept <id>\n• payment <id> cash/upi/card/udhaar\n• deliver <id>\n• cancel <id>"
        return "📋 *Commands:*\n• product\n• location\n• balance\n• help"
    
    # Pending orders
    if msg == 'pending' and sender_number == SHOPKEEPER_PHONE:
        pending = Order.query.filter_by(business_id=business.id).filter(
            Order.status.in_(['pending', 'confirmed', 'payment_received'])
        ).limit(5).all()
        if not pending:
            return "📭 No pending orders."
        resp = "📋 *Pending:*\n"
        for o in pending:
            resp += f"#{o.id} | {o.customer.name if o.customer else 'Walk-in'} | ₹{o.total} | {o.status}\n"
        return resp
    
    # Accept
    if msg.startswith('accept ') and sender_number == SHOPKEEPER_PHONE:
        try:
            oid = int(msg.split()[1])
            order = Order.query.get(oid)
            if order and order.business_id == business.id:
                order.status = 'confirmed'
                db.session.commit()
                return f"✅ Order #{oid} confirmed."
        except:
            pass
        return "❌ Use: accept 123"
    
    # Payment
    if msg.startswith('payment ') and sender_number == SHOPKEEPER_PHONE:
        parts = msg.split()
        if len(parts) >= 3:
            try:
                oid = int(parts[1])
                mode = parts[2]
                order = Order.query.get(oid)
                if order and order.business_id == business.id:
                    order.payment_mode = mode
                    order.payment_status = 'received'
                    order.payment_received_at = datetime.utcnow()
                    order.status = 'payment_received'
                    db.session.commit()
                    return f"✅ Payment: {mode.upper()}\nNext: deliver {oid}"
            except:
                pass
        return "❌ Use: payment 123 cash"
    
    # Deliver
    if msg.startswith('deliver ') and sender_number == SHOPKEEPER_PHONE:
        try:
            oid = int(msg.split()[1])
            order = Order.query.get(oid)
            if order and order.business_id == business.id:
                order.status = 'delivered'
                order.delivered_at = datetime.utcnow()
                order.completed_at = datetime.utcnow()
                
                items = json.loads(order.items) if order.items else []
                for item in items:
                    variant = ProductVariant.query.get(item.get('variant_id'))
                    if variant:
                        variant.stock -= item.get('quantity', 0)
                order.stock_already_reduced = True
                
                if order.customer:
                    order.customer.total_orders = (order.customer.total_orders or 0) + 1
                    order.customer.total_spent = (order.customer.total_spent or 0) + float(order.total or 0)
                
                db.session.commit()
                return f"✅ Order #{oid} delivered! Stock reduced."
        except:
            pass
        return "❌ Use: deliver 123"
    
    # Cancel
    if msg.startswith('cancel ') and sender_number == SHOPKEEPER_PHONE:
        try:
            oid = int(msg.split()[1])
            order = Order.query.get(oid)
            if order and order.business_id == business.id and order.status != 'delivered':
                order.status = 'cancelled'
                db.session.commit()
                return f"✅ Order #{oid} cancelled."
        except:
            pass
        return "❌ Use: cancel 123"
    
    # Order placement
    match = re.match(r'(\d+)\s*(kg|g|packet)\s+(.+)', msg)
    if match:
        qty = int(match.group(1))
        item_name = match.group(3)
        cat = identify_category(item_name)
        if cat:
            products = get_products_by_category(business.id, cat)
            if products:
                p = products[0]['product']
                v = products[0]['variants'][0]
                total = v.price * qty
                
                temp = TempOrder(
                    phone=sender_number, business_id=business.id,
                    items=json.dumps([{'product_id': p.id, 'variant_id': v.id, 'product_name': p.name, 'quantity': qty, 'price': float(v.price)}]),
                    total=total, expires_at=datetime.utcnow() + timedelta(minutes=5)
                )
                db.session.add(temp)
                db.session.commit()
                save_conversation_state(sender_number, business.id, 'waiting', {'temp_id': temp.id})
                return f"🛒 {qty} x {p.name} = ₹{total}\nConfirm? (ha/nahi)"
    
    return "Maaf kijiye, samjha nahi.\nCommands: product, location, help"

def handle_message_hybrid(message, sender_number, business, customer):
    state, ctx = get_conversation_state(sender_number)
    
    if state == 'waiting':
        temp_id = ctx.get('temp_id')
        temp = TempOrder.query.get(temp_id) if temp_id else None
        msg = message.lower().strip()
        
        if msg in ['ha', 'haan', 'yes', 'ok']:
            if temp and temp.expires_at > datetime.utcnow():
                order = Order(
                    business_id=business.id,
                    customer_id=customer.id if customer else None,
                    items=temp.items, total=temp.total, status='pending'
                )
                db.session.add(order)
                db.session.delete(temp)
                db.session.commit()
                clear_conversation_state(sender_number)
                
                if SHOPKEEPER_PHONE:
                    send_whatsapp_message(SHOPKEEPER_PHONE, f"🆕 Order #{order.id}\nTotal: ₹{order.total}\nReply: accept {order.id}")
                
                return f"✅ Order #{order.id} placed!\nTotal: ₹{order.total}\n📍 {business.address}", False
            else:
                clear_conversation_state(sender_number)
                return "⏰ Expired. Try again.", False
        elif msg in ['nahi', 'no', 'cancel']:
            if temp:
                db.session.delete(temp)
                db.session.commit()
            clear_conversation_state(sender_number)
            return "❌ Cancelled.", False
    
    if is_simple_command(message):
        return bot_response(message, business, customer, sender_number), False
    
    cat = identify_category(message)
    if cat:
        products = get_products_by_category(business.id, cat)
        if products:
            return format_product_options(products, cat), False
    
    return bot_response(message, business, customer, sender_number), False

# ============================================
# WHATSAPP WEBHOOK
# ============================================

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return str(request.args.get('hub.challenge', ''))
    
    sender = request.form.get('From', '').replace('whatsapp:', '')
    body = request.form.get('Body', '').strip()
    
    logger.info(f"📱 {sender}: {body}")
    
    business = get_or_create_business()
    customer = Customer.query.filter_by(phone=sender, business_id=business.id).first()
    
    if not customer:
        welcome = f"👋 *Welcome to {business.name}!*\n\n📍 {business.address}\n🕐 {business.shop_hours}\n\n• product\n• location\n• help"
        send_whatsapp_message(sender, welcome)
        customer = get_or_create_customer(sender, business.id)
    
    response, _ = handle_message_hybrid(body, sender, business, customer)
    
    twilio_resp = MessagingResponse()
    twilio_resp.message(response)
    return str(twilio_resp)

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/business', methods=['GET'])
def get_business():
    return jsonify(get_or_create_business().to_dict())

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    business = get_or_create_business()
    today = datetime.utcnow().date()
    
    today_orders = Order.query.filter(
        Order.business_id == business.id,
        db.func.date(Order.created_at) == today
    ).all()
    
    revenue = sum(float(o.total or 0) for o in today_orders if o.status == 'delivered')
    
    return jsonify({
        'today': {'total_orders': len(today_orders), 'revenue': revenue},
        'total_customers': Customer.query.filter_by(business_id=business.id).count()
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)