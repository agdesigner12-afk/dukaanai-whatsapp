"""
DukaanAI - WhatsApp Business Assistant
Phase 1 Complete Implementation
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
TWILIO_PHONE = os.getenv('TWILIO_PHONE')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None

# ============================================
# DATABASE MODELS
# ============================================

class Business(db.Model):
    __tablename__ = 'business'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default='My Store')
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
    
    business = db.relationship('Business', backref='customers')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'balance': float(self.balance) if self.balance else 0,
            'language_pref': self.language_pref,
            'visit_count': self.visit_count,
            'total_orders': self.total_orders,
            'total_spent': float(self.total_spent) if self.total_spent else 0,
            'is_verified': self.is_verified
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
    image_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    business = db.relationship('Business', backref='products')
    
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
    sku = db.Column(db.String(100))
    barcode = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    product = db.relationship('Product', backref='variants')
    
    def to_dict(self):
        return {
            'id': self.id,
            'weight': float(self.weight) if self.weight else None,
            'unit': self.unit,
            'price': float(self.price) if self.price else 0,
            'stock': self.stock,
            'sku': self.sku,
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
    payment_amount = db.Column(db.Numeric(10, 2))
    udhaar_balance_used = db.Column(db.Numeric(10, 2), default=0)
    stock_already_reduced = db.Column(db.Boolean, default=False)
    store_id = db.Column(db.Integer)
    delivery_address = db.Column(db.Text)
    delivery_latitude = db.Column(db.Numeric(10, 8))
    delivery_longitude = db.Column(db.Numeric(11, 8))
    payment_details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    business = db.relationship('Business', backref='orders')
    customer = db.relationship('Customer', backref='orders')
    
    def get_items(self):
        return json.loads(self.items) if self.items else []
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else 'Walk-in Customer',
            'customer_phone': self.customer.phone if self.customer else None,
            'items': self.get_items(),
            'total': float(self.total) if self.total else 0,
            'status': self.status,
            'payment_mode': self.payment_mode,
            'payment_status': self.payment_status,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
        }

class TempOrder(db.Model):
    __tablename__ = 'temp_order'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    business_id = db.Column(db.Integer)
    items = db.Column(db.Text)
    total = db.Column(db.Numeric(10, 2))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ConversationState(db.Model):
    __tablename__ = 'conversation_state'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False)
    store_id = db.Column(db.Integer)
    state = db.Column(db.String(50))
    context = db.Column(db.Text)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_context(self):
        return json.loads(self.context) if self.context else {}
    
    def set_context(self, data):
        self.context = json.dumps(data)

class AIConversationLog(db.Model):
    __tablename__ = 'ai_conversation_log'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer)
    store_id = db.Column(db.Integer)
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    used_ai = db.Column(db.Boolean)
    confidence_score = db.Column(db.Float)
    response_time = db.Column(db.Float)
    model_used = db.Column(db.String(50))
    tokens_used = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BalanceTransaction(db.Model):
    __tablename__ = 'balance_transaction'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer)
    amount = db.Column(db.Numeric(10, 2))
    type = db.Column(db.String(50))
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SellSession(db.Model):
    __tablename__ = 'sell_session'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    business_id = db.Column(db.Integer)
    state = db.Column(db.String(50))
    data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            shop_hours='8 AM - 10 PM',
            welcome_message='Welcome to our store! How can I help you?'
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
            language_pref='hi',
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
        print(f"[MOCK] Sending to {to_phone}: {message[:100]}...")
        return True
    
    try:
        twilio_client.messages.create(
            body=message,
            from_=f'whatsapp:{TWILIO_PHONE}',
            to=f'whatsapp:{to_phone}'
        )
        return True
    except Exception as e:
        print(f"Error sending WhatsApp: {e}")
        return False

def identify_category(text):
    text = text.lower()
    categories = {
        'tea': ['chai', 'tea', 'चाय', 'चायपत्ती'],
        'rice': ['chawal', 'rice', 'चावल', 'बासमती'],
        'sugar': ['chini', 'sugar', 'चीनी'],
        'oil': ['tel', 'oil', 'तेल', 'सरसों'],
        'dal': ['dal', 'दाल', 'तूर', 'मूंग', 'मसूर'],
        'milk': ['doodh', 'milk', 'दूध'],
        'wheat': ['gehu', 'wheat', 'गेहूं', 'आटा'],
    }
    for category, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return category
    return None

def get_greeting(business, customer):
    style = business.greeting_style
    name = customer.name if customer else None
    
    greetings = {
        'friendly': f"🛍️ Welcome back {name} ji!" if name else f"🛍️ Welcome to {business.name}!",
        'formal': f"Welcome Mr./Ms. {name}." if name else f"Welcome to {business.name}.",
        'simple': f"Kya chahiye {name} ji?" if name else "Kya chahiye?",
    }
    
    return greetings.get(style, greetings['friendly'])

def can_customer_see_products(customer, business):
    visibility = business.product_visibility
    
    if visibility == 'public':
        return True, None
    elif visibility == 'registered_only':
        if customer:
            return True, customer
        else:
            return False, "only_registered"
    elif visibility == 'hidden':
        return False, "hidden"
    
    return False, "unknown"

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
    
    emoji_map = {'tea': '🍵', 'rice': '🍚', 'sugar': '🍬', 'oil': '🛢️', 'dal': '🫘', 'milk': '🥛', 'wheat': '🌾'}
    emoji = emoji_map.get(category_name.lower(), '📦')
    
    response = f"{emoji} *{category_name.upper()} Options:*\n\n"
    
    for item in category_products[:5]:
        p = item['product']
        variants = item['variants']
        full_name = f"{p.brand} {p.name}".strip() if p.brand else p.name
        response += f"*{full_name}*\n"
        for v in variants[:3]:
            response += f"  {v.weight}{v.unit} - ₹{v.price}"
            if v.stock < 5:
                response += f" ⚠️({v.stock} left)"
            response += "\n"
        response += "\n"
    
    response += f"📦 *Kitna aur kaunsa chahiye?*\nExample: 'Tata Tea Gold 500g'"
    return response

def parse_product_selection(text, category_products):
    pattern1 = r'(\d+)\s*x\s*(.+?)\s+(\d+\.?\d*)\s*(g|kg)'
    match = re.search(pattern1, text, re.IGNORECASE)
    
    if match:
        qty = int(match.group(1))
        product_name = match.group(2).strip()
        weight = float(match.group(3))
        unit = match.group(4).lower()
        return qty, product_name, weight, unit
    
    pattern2 = r'(.+?)\s+(\d+\.?\d*)\s*(g|kg)'
    match = re.search(pattern2, text, re.IGNORECASE)
    
    if match:
        product_name = match.group(1).strip()
        weight = float(match.group(2))
        unit = match.group(3).lower()
        return 1, product_name, weight, unit
    
    return None, None, None, None

def find_variant(category_products, product_name, weight, unit):
    for item in category_products:
        p = item['product']
        full_name = f"{p.brand} {p.name}".strip().lower() if p.brand else p.name.lower()
        
        if product_name.lower() in full_name or full_name in product_name.lower():
            for v in item['variants']:
                if float(v.weight) == weight and v.unit.lower() == unit.lower():
                    return p, v
    
    return None, None

def reduce_stock_only_when_delivered(order):
    if order.status != 'delivered':
        return False, "Order not delivered yet"
    
    if order.stock_already_reduced:
        return False, "Stock already reduced"
    
    items = json.loads(order.items) if order.items else []
    
    for item in items:
        variant = ProductVariant.query.get(item.get('variant_id'))
        if variant:
            variant.stock -= item.get('quantity', 0)
    
    order.stock_already_reduced = True
    db.session.commit()
    
    return True, "Stock reduced successfully"

def save_conversation_state(phone, store_id, state, context):
    existing = ConversationState.query.filter_by(phone=phone).first()
    
    if existing:
        existing.state = state
        existing.set_context(context)
        existing.expires_at = datetime.utcnow() + timedelta(minutes=30)
    else:
        new_state = ConversationState(
            phone=phone,
            store_id=store_id,
            state=state,
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
    simple_commands = ['price', 'product', 'order', 'balance', 'location', 
                       'help', 'status', 'accept', 'payment', 'deliver', 
                       'cancel', 'pending', 'sell', 'menu']
    
    msg_lower = message.lower().strip()
    
    if msg_lower in simple_commands:
        return True
    
    if msg_lower.startswith(('order ', 'payment ', 'accept ', 'deliver ', 'cancel ', 'status ')):
        return True
    
    if re.match(r'\d+\s*(kg|g|packet|pack)\s+\w+', msg_lower):
        return True
    
    return False

def bot_response(message, business, customer, sender_number):
    msg_lower = message.lower().strip()
    
    # Product command - Conversational
    if msg_lower == 'product':
        can_view, reason = can_customer_see_products(customer, business)
        
        if can_view:
            greeting = get_greeting(business, customer)
            return f"{greeting}\n\nAapko kya chahiye?\n\nBatayein jaise:\n• chai\n• chawal\n• chini\n• tel\n• dal"
        elif reason == "only_registered":
            return f"⚠️ Product list only for registered customers.\n\nPlease visit the shop to register.\n📍 {business.address}\n📞 {business.phone}"
        else:
            return "ℹ️ Kya chahiye? Batao main price aur availability check karta hoon."
    
    # Location command
    if msg_lower == 'location':
        if business.shop_latitude and business.shop_longitude:
            maps_link = f"https://maps.google.com/?q={business.shop_latitude},{business.shop_longitude}"
            return f"🏪 *{business.name}*\n📍 {business.address}\n{business.shop_landmark or ''}\n🗺️ {maps_link}\n🕐 {business.shop_hours}"
        else:
            return f"🏪 *{business.name}*\n📍 {business.address}\n📞 {business.phone}"
    
    # Balance command
    if msg_lower == 'balance':
        if customer:
            if customer.balance > 0:
                return f"💰 Aapki udhaari: ₹{customer.balance}\n\nTotal orders: {customer.total_orders}"
            else:
                return f"✅ Aapki koi udhaari nahi hai!\nTotal orders: {customer.total_orders}"
        else:
            return "❌ Aap registered customer nahi hain."
    
    # Help command
    if msg_lower == 'help':
        if sender_number == SHOPKEEPER_PHONE:
            return """📋 *Shopkeeper Commands:*
            
• `sell` - Walk-in sale
• `accept <id>` - Accept order
• `payment <id> <mode>` - Record payment (cash/upi/card/udhaar)
• `deliver <id>` - Mark delivered (stock reduce hoga)
• `cancel <id>` - Cancel order
• `pending` - View pending orders
• `add udhaar <name> <amount>` - Add credit"""
        else:
            return """📋 *Commands:*
            
• `product` - Browse products
• `order <qty> <item>` - Place order
• `balance` - Check udhaar
• `location` - Shop address
• `help` - Yeh message"""
    
    # Pending orders (shopkeeper only)
    if msg_lower == 'pending' and sender_number == SHOPKEEPER_PHONE:
        pending = Order.query.filter_by(
            business_id=business.id
        ).filter(Order.status.in_(['pending', 'confirmed', 'payment_received'])).order_by(Order.created_at.desc()).limit(10).all()
        
        if not pending:
            return "📭 No pending orders."
        
        response = "📋 *Pending Orders:*\n\n"
        for o in pending:
            status_emoji = {'pending': '🆕', 'confirmed': '✅', 'payment_received': '💰'}.get(o.status, '📦')
            response += f"{status_emoji} #{o.id} | {o.customer.name if o.customer else 'Walk-in'}\n"
            response += f"   Items: {len(o.get_items())} | ₹{o.total}\n"
            response += f"   Status: {o.status}\n\n"
        return response
    
    # Accept order (shopkeeper)
    if msg_lower.startswith('accept ') and sender_number == SHOPKEEPER_PHONE:
        try:
            order_id = int(msg_lower.split(' ')[1])
            order = Order.query.get(order_id)
            
            if order and order.business_id == business.id:
                if order.status == 'pending':
                    order.status = 'confirmed'
                    db.session.commit()
                    
                    if order.customer:
                        send_whatsapp_message(
                            order.customer.phone,
                            f"✅ Order #{order.id} confirmed!\nTotal: ₹{order.total}\nPlease visit shop for pickup."
                        )
                    
                    return f"✅ Order #{order_id} confirmed."
                else:
                    return f"ℹ️ Order #{order_id} already {order.status}."
            return f"❌ Order #{order_id} not found."
        except:
            return "❌ Use: accept 123"
    
    # Payment command (shopkeeper)
    if msg_lower.startswith('payment ') and sender_number == SHOPKEEPER_PHONE:
        parts = msg_lower.split()
        if len(parts) >= 3:
            try:
                order_id = int(parts[1])
                mode = parts[2].lower()
                order = Order.query.get(order_id)
                
                if order and order.business_id == business.id:
                    order.payment_mode = mode
                    order.payment_status = 'received'
                    order.payment_received_at = datetime.utcnow()
                    
                    if mode == 'udhaar' and len(parts) >= 4:
                        amount = float(parts[3])
                        order.udhaar_balance_used = amount
                        if order.customer:
                            order.customer.balance = (order.customer.balance or 0) + amount
                    
                    order.status = 'payment_received'
                    db.session.commit()
                    
                    return f"✅ Payment recorded: {mode.upper()}\nStatus: payment_received\nNext: deliver {order_id}"
                
                return f"❌ Order #{order_id} not found."
            except:
                return "❌ Use: payment 123 cash\nOr: payment 123 udhaar 500"
    
    # Deliver command (shopkeeper)
    if msg_lower.startswith('deliver ') and sender_number == SHOPKEEPER_PHONE:
        try:
            order_id = int(msg_lower.split(' ')[1])
            order = Order.query.get(order_id)
            
            if order and order.business_id == business.id:
                if order.status in ['confirmed', 'payment_received']:
                    order.status = 'delivered'
                    order.delivered_at = datetime.utcnow()
                    order.completed_at = datetime.utcnow()
                    
                    success, msg = reduce_stock_only_when_delivered(order)
                    
                    if order.customer:
                        order.customer.total_orders = (order.customer.total_orders or 0) + 1
                        order.customer.total_spent = (order.customer.total_spent or 0) + float(order.total or 0)
                    
                    db.session.commit()
                    
                    if order.customer:
                        send_whatsapp_message(
                            order.customer.phone,
                            f"🎉 Order #{order_id} delivered!\nThank you for shopping with {business.name}!"
                        )
                    
                    return f"✅ Order #{order_id} delivered!\nStock reduced: {success}"
                else:
                    return f"❌ Cannot deliver order with status: {order.status}\nPay first: payment {order_id} <mode>"
            return f"❌ Order #{order_id} not found."
        except:
            return "❌ Use: deliver 123"
    
    # Cancel order (shopkeeper)
    if msg_lower.startswith('cancel ') and sender_number == SHOPKEEPER_PHONE:
        try:
            order_id = int(msg_lower.split(' ')[1])
            order = Order.query.get(order_id)
            
            if order and order.business_id == business.id:
                if order.status not in ['delivered', 'cancelled']:
                    order.status = 'cancelled'
                    db.session.commit()
                    
                    if order.customer:
                        send_whatsapp_message(
                            order.customer.phone,
                            f"❌ Order #{order_id} cancelled.\nContact shop: {business.phone}"
                        )
                    
                    return f"✅ Order #{order_id} cancelled."
                else:
                    return f"❌ Cannot cancel {order.status} order."
            return f"❌ Order #{order_id} not found."
        except:
            return "❌ Use: cancel 123"
    
    # Add Udhaar command (shopkeeper)
    if msg_lower.startswith('add udhaar ') and sender_number == SHOPKEEPER_PHONE:
        parts = msg_lower.split('add udhaar ')[1].strip().rsplit(' ', 1)
        if len(parts) == 2:
            try:
                name_or_phone = parts[0].strip()
                amount = float(parts[1])
                
                customer = Customer.query.filter(
                    (Customer.name.ilike(f'%{name_or_phone}%')) | 
                    (Customer.phone == name_or_phone)
                ).filter_by(business_id=business.id).first()
                
                if customer:
                    customer.balance = (customer.balance or 0) + amount
                    
                    txn = BalanceTransaction(
                        customer_id=customer.id,
                        amount=amount,
                        type='add',
                        reason='Added by shopkeeper'
                    )
                    db.session.add(txn)
                    db.session.commit()
                    
                    send_whatsapp_message(
                        customer.phone,
                        f"💰 Udhaar updated: +₹{amount}\nTotal balance: ₹{customer.balance}\n\n📍 {business.name}"
                    )
                    
                    return f"✅ ₹{amount} udhaar added for {customer.name}.\nTotal balance: ₹{customer.balance}"
                else:
                    return f"❌ Customer '{name_or_phone}' not found."
            except:
                return "❌ Use: add udhaar Suresh 500"
    
    # Order placement by customer
    order_match = re.match(r'(\d+)\s*(kg|g|packet|pack|piece)\s+(.+)', msg_lower)
    if order_match:
        qty = int(order_match.group(1))
        unit = order_match.group(2)
        item_name = order_match.group(3).strip()
        
        category = identify_category(item_name)
        
        if category:
            products = get_products_by_category(business.id, category)
            
            if products:
                p = products[0]['product']
                v = products[0]['variants'][0]
                
                total = v.price * qty
                
                temp = TempOrder(
                    phone=sender_number,
                    business_id=business.id,
                    items=json.dumps([{
                        'product_id': p.id,
                        'variant_id': v.id,
                        'product_name': f"{p.brand} {p.name}".strip(),
                        'quantity': qty,
                        'weight': float(v.weight),
                        'unit': v.unit,
                        'price': float(v.price),
                        'total': float(total)
                    }]),
                    total=total,
                    expires_at=datetime.utcnow() + timedelta(minutes=5)
                )
                db.session.add(temp)
                db.session.commit()
                
                save_conversation_state(sender_number, business.id, 'waiting_for_confirmation', {'temp_order_id': temp.id})
                
                return f"🛒 {qty} x {p.brand} {p.name} = ₹{total}\n\nConfirm order? (ha/nahi)"
            else:
                return f"❌ {category} stock mein nahi hai."
        else:
            return f"❌ '{item_name}' samajh nahi aaya. Try: product"
    
    # Default fallback
    return f"""Maaf kijiye, main samjha nahi.

Aap ye commands use kar sakte hain:
• product - Products dekhein
• location - Dukan ka pata
• balance - Udhaari check
• help - Madad"""

def handle_message_hybrid(message, sender_number, business, customer):
    state, context = get_conversation_state(sender_number)
    
    if state == 'waiting_for_confirmation':
        temp_id = context.get('temp_order_id')
        temp = TempOrder.query.get(temp_id) if temp_id else None
        
        msg_lower = message.lower().strip()
        
        if msg_lower in ['ha', 'haan', 'yes', 'confirm', 'ok', 'okay', 'ji']:
            if temp and temp.expires_at > datetime.utcnow():
                items_data = json.loads(temp.items)
                
                order = Order(
                    business_id=business.id,
                    customer_id=customer.id if customer else None,
                    items=temp.items,
                    total=temp.total,
                    status='pending',
                    source='whatsapp'
                )
                db.session.add(order)
                db.session.delete(temp)
                db.session.commit()
                
                clear_conversation_state(sender_number)
                
                if SHOPKEEPER_PHONE:
                    item_summary = items_data[0]['product_name'] if items_data else 'items'
                    send_whatsapp_message(
                        SHOPKEEPER_PHONE,
                        f"🆕 *New Order #{order.id}*\nCustomer: {customer.name if customer else 'New'}\n{sender_number}\n\nItems: {item_summary}\nTotal: ₹{order.total}\n\nReply: accept {order.id}"
                    )
                
                return f"✅ *Order #{order.id} placed!*\n\nTotal: ₹{order.total}\n\n📍 Visit shop:\n{business.address}", False
            else:
                clear_conversation_state(sender_number)
                return "⏰ Order expired. Please order again.", False
        
        elif msg_lower in ['nahi', 'na', 'no', 'cancel']:
            if temp:
                db.session.delete(temp)
                db.session.commit()
            clear_conversation_state(sender_number)
            return "❌ Order cancelled.", False
    
    if is_simple_command(message):
        return bot_response(message, business, customer, sender_number), False
    
    category = identify_category(message)
    if category:
        products = get_products_by_category(business.id, category)
        if products:
            save_conversation_state(sender_number, business.id, 'waiting_for_selection', {'category': category})
            return format_product_options(products, category), False
    
    return bot_response(message, business, customer, sender_number), False

# ============================================
# WHATSAPP WEBHOOK
# ============================================

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return str(request.args.get('hub.challenge', ''))
    
    sender_number = request.form.get('From', '').replace('whatsapp:', '')
    message_body = request.form.get('Body', '').strip()
    
    latitude = request.form.get('Latitude')
    longitude = request.form.get('Longitude')
    
    if latitude and longitude:
        message_body = f"[Location shared: {latitude}, {longitude}]"
    
    print(f"📱 Message from {sender_number}: {message_body}")
    
    business = get_or_create_business()
    customer = Customer.query.filter_by(phone=sender_number, business_id=business.id).first()
    
    if not customer:
        welcome = business.welcome_message or f"""👋 *Welcome to {business.name}!*

📍 {business.address}
{business.shop_landmark or ''}
🕐 {business.shop_hours}

*Quick Commands:*
• product - Browse items
• location - Get directions
• help - All commands

How can I help you today?"""
        
        send_whatsapp_message(sender_number, welcome)
        customer = get_or_create_customer(sender_number, business.id)
    
    response, used_ai = handle_message_hybrid(message_body, sender_number, business, customer)
    
    twilio_resp = MessagingResponse()
    twilio_resp.message(response)
    
    return str(twilio_resp)

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/business', methods=['GET'])
def get_business():
    business = get_or_create_business()
    return jsonify(business.to_dict())

@app.route('/api/business', methods=['PUT'])
def update_business():
    business = get_or_create_business()
    data = request.json
    
    updatable = ['name', 'phone', 'address', 'shop_latitude', 'shop_longitude',
                 'shop_landmark', 'shop_hours', 'product_visibility', 'greeting_style',
                 'preferred_language', 'upi_id', 'ai_enabled', 'welcome_message']
    
    for field in updatable:
        if field in data:
            setattr(business, field, data[field])
    
    db.session.commit()
    return jsonify({'success': True, 'business': business.to_dict()})

@app.route('/api/products', methods=['GET'])
def get_products():
    business = get_or_create_business()
    products = Product.query.filter_by(business_id=business.id).all()
    return jsonify([p.to_dict() for p in products])

@app.route('/api/products', methods=['POST'])
def create_product():
    business = get_or_create_business()
    data = request.json
    
    product = Product(
        business_id=business.id,
        category=data.get('category'),
        brand=data.get('brand'),
        name=data.get('name'),
        description=data.get('description'),
        is_loose=data.get('is_loose', False)
    )
    db.session.add(product)
    db.session.flush()
    
    for v in data.get('variants', []):
        variant = ProductVariant(
            product_id=product.id,
            weight=v.get('weight'),
            unit=v.get('unit', 'kg'),
            price=v.get('price'),
            stock=v.get('stock', 0),
            sku=v.get('sku')
        )
        db.session.add(variant)
    
    db.session.commit()
    return jsonify(product.to_dict())

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.json
    
    product.category = data.get('category', product.category)
    product.brand = data.get('brand', product.brand)
    product.name = data.get('name', product.name)
    
    db.session.commit()
    return jsonify(product.to_dict())

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    ProductVariant.query.filter_by(product_id=product_id).delete()
    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/variants/<int:variant_id>', methods=['PUT'])
def update_variant(variant_id):
    variant = ProductVariant.query.get_or_404(variant_id)
    data = request.json
    
    if 'price' in data:
        variant.price = data['price']
    if 'stock' in data:
        variant.stock = data['stock']
    
    db.session.commit()
    return jsonify(variant.to_dict())

@app.route('/api/customers', methods=['GET'])
def get_customers():
    business = get_or_create_business()
    customers = Customer.query.filter_by(business_id=business.id).order_by(Customer.name).all()
    return jsonify([c.to_dict() for c in customers])

@app.route('/api/customers', methods=['POST'])
def create_customer():
    business = get_or_create_business()
    data = request.json
    
    existing = Customer.query.filter_by(phone=data.get('phone'), business_id=business.id).first()
    if existing:
        return jsonify({'error': 'Customer already exists', 'customer': existing.to_dict()}), 400
    
    customer = Customer(
        business_id=business.id,
        name=data.get('name'),
        phone=data.get('phone'),
        language_pref=data.get('language_pref', 'hi')
    )
    db.session.add(customer)
    db.session.commit()
    
    return jsonify(customer.to_dict())

@app.route('/api/orders', methods=['GET'])
def get_orders():
    business = get_or_create_business()
    
    days = request.args.get('days', type=int)
    status = request.args.get('status')
    
    query = Order.query.filter_by(business_id=business.id)
    
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Order.created_at >= since)
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(Order.created_at.desc()).limit(100).all()
    return jsonify([o.to_dict() for o in orders])

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.json
    new_status = data.get('status')
    
    if new_status == 'delivered' and order.status != 'delivered':
        order.status = 'delivered'
        order.delivered_at = datetime.utcnow()
        order.completed_at = datetime.utcnow()
        reduce_stock_only_when_delivered(order)
        
        if order.customer:
            order.customer.total_orders = (order.customer.total_orders or 0) + 1
            order.customer.total_spent = (order.customer.total_spent or 0) + float(order.total or 0)
    else:
        order.status = new_status
    
    db.session.commit()
    return jsonify(order.to_dict())

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    business = get_or_create_business()
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    today_orders = Order.query.filter(
        Order.business_id == business.id,
        db.func.date(Order.created_at) == today
    ).all()
    
    today_revenue = sum(float(o.total or 0) for o in today_orders if o.status == 'delivered')
    today_pending = sum(1 for o in today_orders if o.status in ['pending', 'confirmed'])
    
    week_orders = Order.query.filter(
        Order.business_id == business.id,
        Order.created_at >= week_ago
    ).all()
    
    week_revenue = sum(float(o.total or 0) for o in week_orders if o.status == 'delivered')
    
    low_stock = ProductVariant.query.join(Product).filter(
        Product.business_id == business.id,
        ProductVariant.stock < 5
    ).count()
    
    total_balance = db.session.query(db.func.sum(Customer.balance)).filter(
        Customer.business_id == business.id
    ).scalar() or 0
    
    recent_orders = Order.query.filter_by(business_id=business.id).order_by(
        Order.created_at.desc()
    ).limit(10).all()
    
    return jsonify({
        'today': {
            'total_orders': len(today_orders),
            'revenue': today_revenue,
            'pending': today_pending
        },
        'week': {
            'total_orders': len(week_orders),
            'revenue': week_revenue
        },
        'low_stock_count': low_stock,
        'total_udhaar': float(total_balance),
        'total_customers': Customer.query.filter_by(business_id=business.id).count(),
        'recent_orders': [o.to_dict() for o in recent_orders]
    })

@app.route('/api/udhaar/customers', methods=['GET'])
def get_udhaar_customers():
    business = get_or_create_business()
    customers = Customer.query.filter(
        Customer.business_id == business.id,
        Customer.balance > 0
    ).order_by(Customer.balance.desc()).all()
    return jsonify([c.to_dict() for c in customers])

@app.route('/api/udhaar/add', methods=['POST'])
def add_udhaar():
    data = request.json
    customer = Customer.query.get_or_404(data.get('customer_id'))
    amount = float(data.get('amount', 0))
    
    customer.balance = (customer.balance or 0) + amount
    
    txn = BalanceTransaction(
        customer_id=customer.id,
        amount=amount,
        type='add',
        reason=data.get('reason', 'Added by shopkeeper')
    )
    db.session.add(txn)
    db.session.commit()
    
    business = get_or_create_business()
    send_whatsapp_message(
        customer.phone,
        f"💰 Udhaar updated: +₹{amount}\nTotal balance: ₹{customer.balance}\n\n📍 {business.name}"
    )
    
    return jsonify(customer.to_dict())

@app.route('/api/udhaar/transactions/<int:customer_id>', methods=['GET'])
def get_transactions(customer_id):
    transactions = BalanceTransaction.query.filter_by(customer_id=customer_id).order_by(
        BalanceTransaction.created_at.desc()
    ).limit(50).all()
    
    return jsonify([{
        'id': t.id,
        'amount': float(t.amount),
        'type': t.type,
        'reason': t.reason,
        'created_at': t.created_at.isoformat()
    } for t in transactions])

@app.route('/trigger_reminders', methods=['POST'])
def trigger_reminders():
    business = get_or_create_business()
    customers = Customer.query.filter(
        Customer.business_id == business.id,
        Customer.balance > 0
    ).all()
    
    sent = 0
    for c in customers:
        if not c.last_reminder_date or c.last_reminder_date < datetime.utcnow() - timedelta(days=7):
            send_whatsapp_message(
                c.phone,
                f"📋 Reminder: Aapki udhaari ₹{c.balance} hai.\nKripya jald payment karein.\n📍 {business.name}\n📞 {business.phone}"
            )
            c.last_reminder_date = datetime.utcnow()
            sent += 1
    
    db.session.commit()
    return jsonify({'sent': sent, 'total': len(customers)})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        get_or_create_business()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)