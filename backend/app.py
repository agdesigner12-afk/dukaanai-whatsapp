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
import requests
import traceback
import time
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dukaanai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

twilio_client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
executor = ThreadPoolExecutor(max_workers=5)

# ------------------------- DATABASE MODELS -------------------------
class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), default="My Shop")
    business_name = db.Column(db.String(100), default="DukaanAI Demo")
    address = db.Column(db.String(200), default="")
    gstin = db.Column(db.String(20), default="")
    upi_id = db.Column(db.String(100), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    phone = db.Column(db.String(20), index=True)
    name = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0)
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    last_order_date = db.Column(db.DateTime, nullable=True)
    last_reminder_date = db.Column(db.DateTime, nullable=True)
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

class TempOrder(db.Model):
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

class SellSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shopkeeper_phone = db.Column(db.String(20), index=True)
    step = db.Column(db.String(20))
    data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BalanceTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    amount = db.Column(db.Float)
    new_balance = db.Column(db.Float)
    reason = db.Column(db.String(200))
    source = db.Column(db.String(20), default='web')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PaymentRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    amount = db.Column(db.Float)
    upi_link = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')
    screenshot_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

class PaymentScreenshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_request_id = db.Column(db.Integer, db.ForeignKey('payment_request.id'))
    media_url = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------------- INIT DB & MIGRATIONS -------------------------
with app.app_context():
    db.create_all()
    # Add missing columns (SQLite workaround)
    try:
        db.session.execute('ALTER TABLE business ADD COLUMN address VARCHAR(200) DEFAULT ""')
    except: pass
    try:
        db.session.execute('ALTER TABLE business ADD COLUMN gstin VARCHAR(20) DEFAULT ""')
    except: pass
    try:
        db.session.execute('ALTER TABLE business ADD COLUMN upi_id VARCHAR(100) DEFAULT ""')
    except: pass
    try:
        db.session.execute('ALTER TABLE customer ADD COLUMN last_reminder_date TIMESTAMP')
    except: pass
    db.session.commit()

    if not Business.query.first():
        biz = Business(
            phone=os.getenv('TWILIO_WHATSAPP_NUMBER'),
            name="रमेश किराना स्टोर",
            business_name="DukaanAI Demo",
            address="123, Main Market, New Delhi",
            gstin="07AAACA1234A1Z",
            upi_id="ramesh@okhdfcbank"
        )
        db.session.add(biz)
        db.session.commit()

    if Product.query.count() == 0:
        biz = Business.query.first()
        db.session.add_all([
            Product(business_id=biz.id, name="गोल्ड चाय पत्ती", price=250, unit="kg", stock=15),
            Product(business_id=biz.id, name="Tata नमक", price=25, unit="kg", stock=8),
            Product(business_id=biz.id, name="फोर्ट बिस्कुट", price=10, unit="piece", stock=45)
        ])
        db.session.commit()

    if Customer.query.count() == 0:
        biz = Business.query.first()
        db.session.add_all([
            Customer(business_id=biz.id, name="रमेश कुमार", phone="9876543210", balance=500),
            Customer(business_id=biz.id, name="सुरेश पटेल", phone="9876543211", balance=250),
            Customer(business_id=biz.id, name="महेश शर्मा", phone="9876543212", balance=0)
        ])
        db.session.commit()
    print("✅ Database ready")

# ------------------------- HELPERS -------------------------
def create_order_from_temp(temp):
    try:
        customer = Customer.query.get(temp.customer_id)
        product = Product.query.get(temp.product_id)
        if not customer or not product:
            return False, "Customer or product not found"
        if product.stock < temp.quantity:
            return False, f"Only {product.stock} {product.unit} available"
        items = json.dumps([{
            'product_id': product.id,
            'name': product.name,
            'quantity': temp.quantity,
            'price': product.price
        }])
        order = Order(
            business_id=customer.business_id,
            customer_id=customer.id,
            items=items,
            total=temp.total,
            status='pending',
            source='whatsapp'
        )
        db.session.add(order)
        # Stock reduction moved to order completion (by shopkeeper)
        customer.total_orders += 1
        customer.total_spent += temp.total
        customer.last_order_date = datetime.utcnow()
        customer.balance += temp.total
        db.session.delete(temp)
        db.session.commit()
        return True, order
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def get_ai_reply(customer, message):
    try:
        products = Product.query.limit(5).all()
        product_list = "\n".join([f"{p.name}: ₹{p.price}" for p in products]) if products else "कोई प्रोडक्ट नहीं"
        prompt = f"""Customer: {customer.name}
Balance: ₹{customer.balance}
Message: {message}
Products: {product_list}

Short Hinglish reply (1-2 lines):"""
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            return "थोड़ी देर में try करें। 🙏"
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are DukaanAI, a friendly Hindi/English WhatsApp assistant. Keep replies very short (1-2 lines)."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 80
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content'].strip()
        else:
            print(f"DeepSeek error {resp.status_code}: {resp.text}")
            return "थोड़ी देर में try करें। 🙏"
    except Exception as e:
        print(f"AI error: {e}")
        return "थोड़ी देर में try करें। 🙏"

def add_balance(customer_phone, amount, reason="", source="whatsapp"):
    customer = Customer.query.filter_by(phone=customer_phone).first()
    if not customer:
        return False, "Customer not found"
    old_balance = customer.balance
    customer.balance += amount
    db.session.commit()
    trans = BalanceTransaction(
        customer_id=customer.id,
        amount=amount,
        new_balance=customer.balance,
        reason=reason or f"Udhaar added via {source}",
        source=source
    )
    db.session.add(trans)
    db.session.commit()
    biz = Business.query.first()
    shop_name = biz.name if biz else "Shop"
    msg = f"📢 *{shop_name}* has added ₹{amount} to your account.\n\nPrevious balance: ₹{old_balance}\nNew balance: ₹{customer.balance}\nReason: {reason}\n\nIf this seems incorrect, please contact the shopkeeper."
    try:
        twilio_client.messages.create(
            body=msg,
            from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
            to=customer_phone
        )
    except Exception as e:
        print(f"Failed to send notification: {e}")
    return True, f"₹{amount} added to {customer.name}'s balance. Total due: ₹{customer.balance}"

def reduce_balance(customer_phone, amount, reason="", source="whatsapp"):
    customer = Customer.query.filter_by(phone=customer_phone).first()
    if not customer:
        return False, "Customer not found"
    if amount > customer.balance:
        return False, f"Amount exceeds current due ₹{customer.balance}"
    old_balance = customer.balance
    customer.balance -= amount
    db.session.commit()
    trans = BalanceTransaction(
        customer_id=customer.id,
        amount=-amount,
        new_balance=customer.balance,
        reason=reason or f"Payment received via {source}",
        source=source
    )
    db.session.add(trans)
    db.session.commit()
    biz = Business.query.first()
    shop_name = biz.name if biz else "Shop"
    msg = f"💰 *{shop_name}* has received ₹{amount} from you.\n\nPrevious balance: ₹{old_balance}\nNew balance: ₹{customer.balance}\nThank you!"
    try:
        twilio_client.messages.create(
            body=msg,
            from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
            to=customer_phone
        )
    except Exception as e:
        print(f"Failed to send payment notification: {e}")
    return True, f"Payment of ₹{amount} received. Remaining due: ₹{customer.balance}"

# ------------------------- WHATSAPP MESSAGE HANDLER -------------------------
def process_message(from_number, body):
    try:
        with app.app_context():
            customer = Customer.query.filter_by(phone=from_number).first()
            if not customer:
                biz = Business.query.first()
                customer = Customer(business_id=biz.id, phone=from_number, name=f"User_{from_number[-4:]}")
                db.session.add(customer)
                db.session.commit()
            msg_lower = body.lower().strip()
            biz = Business.query.first()
            shopkeeper_phone = biz.phone if biz else None

            # ---- SELL SESSION (shopkeeper only) ----
            active_session = SellSession.query.filter_by(shopkeeper_phone=from_number).order_by(SellSession.created_at.desc()).first()
            if active_session:
                session = active_session
                step = session.step
                data = json.loads(session.data) if session.data else {}
                
                if step == 'customer_name':
                    customer_name = body.strip()
                    cust = Customer.query.filter_by(name=customer_name).first()
                    if cust:
                        data['customer_id'] = cust.id
                        data['customer_name'] = cust.name
                        data['customer_phone'] = cust.phone
                        session.step = 'product'
                        session.data = json.dumps(data)
                        db.session.commit()
                        reply = f"👤 Customer found: {cust.name} ({cust.phone})\nNow send the **product name** (e.g., 'चाय'):"
                    else:
                        data['customer_name'] = customer_name
                        session.step = 'customer_phone'
                        session.data = json.dumps(data)
                        db.session.commit()
                        reply = f"🆕 New customer '{customer_name}'. Please send their **phone number** (10 digits):"
                    twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                    return
                
                elif step == 'customer_phone':
                    phone = body.strip()
                    if not phone.isdigit() or len(phone) < 10:
                        reply = "❌ Invalid phone number. Please send a 10‑digit number:"
                        twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                        return
                    biz = Business.query.first()
                    new_cust = Customer(business_id=biz.id, name=data['customer_name'], phone=phone, balance=0)
                    db.session.add(new_cust)
                    db.session.commit()
                    data['customer_id'] = new_cust.id
                    data['customer_phone'] = phone
                    session.step = 'product'
                    session.data = json.dumps(data)
                    db.session.commit()
                    reply = f"✅ Customer {data['customer_name']} added with phone {phone}.\nNow send the **product name**:"
                    twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                    return
                
                elif step == 'product':
                    product_name = body.strip()
                    product = Product.query.filter(Product.name.contains(product_name)).first()
                    if not product:
                        reply = f"❌ Product '{product_name}' not found. Send 'product' to see list, or try another name:"
                        twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                        return
                    data['product_id'] = product.id
                    data['product_name'] = product.name
                    data['product_price'] = product.price
                    data['product_unit'] = product.unit
                    session.step = 'quantity'
                    session.data = json.dumps(data)
                    db.session.commit()
                    reply = f"📦 Product: {product.name} (₹{product.price}/{product.unit})\nSend **quantity** (e.g., 2):"
                    twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                    return
                
                elif step == 'quantity':
                    try:
                        qty = int(body.strip())
                        if qty <= 0:
                            raise ValueError
                    except:
                        reply = "❌ Invalid quantity. Please send a positive number:"
                        twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                        return
                    product = Product.query.get(data['product_id'])
                    if product.stock < qty:
                        reply = f"❌ Only {product.stock} {product.unit} available. Send a smaller quantity or cancel with 'cancel sell':"
                        twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                        return
                    data['quantity'] = qty
                    data['total'] = product.price * qty
                    session.step = 'payment_type'
                    session.data = json.dumps(data)
                    db.session.commit()
                    reply = f"💰 Total: ₹{data['total']}\nIs this **cash** or **credit**? Reply with 'cash' or 'credit':"
                    twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                    return
                
                elif step == 'payment_type':
                    payment = body.lower().strip()
                    if payment not in ['cash', 'credit', 'udhaar']:
                        reply = "❌ Please reply with 'cash' or 'credit':"
                        twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                        return
                    data['payment_type'] = payment
                    session.step = 'confirm'
                    session.data = json.dumps(data)
                    db.session.commit()
                    cust = Customer.query.get(data['customer_id'])
                    product = Product.query.get(data['product_id'])
                    reply = f"📋 *Confirm Sale*\nCustomer: {cust.name}\nProduct: {data['quantity']} {product.unit} {product.name}\nTotal: ₹{data['total']}\nPayment: {payment.upper()}\n\nReply 'yes' to confirm, or 'cancel' to abort."
                    twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                    return
                
                elif step == 'confirm':
                    if body.lower().strip() == 'yes':
                        customer = Customer.query.get(data['customer_id'])
                        product = Product.query.get(data['product_id'])
                        qty = data['quantity']
                        total = data['total']
                        items = json.dumps([{
                            'product_id': product.id,
                            'name': product.name,
                            'quantity': qty,
                            'price': product.price
                        }])
                        order = Order(
                            business_id=customer.business_id,
                            customer_id=customer.id,
                            items=items,
                            total=total,
                            status='completed' if data['payment_type'] == 'cash' else 'pending',
                            source='shop'
                        )
                        db.session.add(order)
                        product.stock -= qty
                        product.total_sold += qty
                        customer.total_orders += 1
                        customer.total_spent += total
                        customer.last_order_date = datetime.utcnow()
                        if data['payment_type'] == 'credit':
                            customer.balance += total
                        db.session.commit()
                        reply = f"✅ Sale completed!\n{customer.name} bought {qty} {product.unit} {product.name} for ₹{total}."
                        if data['payment_type'] == 'credit':
                            reply += f"\nNew balance: ₹{customer.balance}"
                        db.session.delete(session)
                        db.session.commit()
                    elif body.lower().strip() == 'cancel':
                        db.session.delete(session)
                        db.session.commit()
                        reply = "❌ Sale cancelled."
                    else:
                        reply = "Please reply 'yes' to confirm or 'cancel' to abort."
                    twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                    return

            # ---- START NEW SELL SESSION ----
            if msg_lower == "sell":
                if from_number != shopkeeper_phone:
                    reply = "❌ Unauthorized. Only the shopkeeper can use this command."
                    twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                    return
                SellSession.query.filter_by(shopkeeper_phone=from_number).delete()
                db.session.commit()
                new_session = SellSession(shopkeeper_phone=from_number, step='customer_name', data='{}')
                db.session.add(new_session)
                db.session.commit()
                reply = "👤 *Start a walk‑in sale*\n\nPlease send the **customer name**:"
                twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                return

            # ---- KHATABOOK COMMANDS ----
            if msg_lower.startswith("add udhaar "):
                parts = body.split()
                if len(parts) >= 4:
                    target = parts[2]
                    try:
                        amount = float(parts[3])
                    except:
                        reply = "❌ Invalid amount"
                        twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                        return
                    cust = Customer.query.filter((Customer.phone == target) | (Customer.name == target)).first()
                    if cust and amount > 0:
                        success, reply = add_balance(cust.phone, amount, source='whatsapp')
                    else:
                        reply = "❌ Customer not found or invalid amount"
                else:
                    reply = "Usage: add udhaar <customer name/phone> <amount>"
                twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                return

            if msg_lower.startswith("pay "):
                parts = body.split()
                if len(parts) >= 2:
                    try:
                        amount = float(parts[1])
                        if amount <= 0:
                            raise ValueError
                        # Create UPI link (optional)
                        biz = Business.query.first()
                        upi_id = biz.upi_id if biz and biz.upi_id else "shopkeeper@okhdfcbank"
                        upi_link = f"upi://pay?pa={upi_id}&pn={biz.name if biz else 'Shop'}&am={amount}&cu=INR"
                        # Store payment request (optional)
                        payment_req = PaymentRequest(
                            customer_id=customer.id,
                            amount=amount,
                            upi_link=upi_link,
                            status='pending'
                        )
                        db.session.add(payment_req)
                        db.session.commit()
                        reply = f"💰 Please pay ₹{amount} using this link:\n{upi_link}\n\nAfter successful payment, send the screenshot here. I will forward it to the shopkeeper for verification."
                    except:
                        reply = "❌ Invalid amount"
                else:
                    reply = "Usage: pay <amount>"
                twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                return

            if msg_lower in ['balance', 'बाकी', 'kitna baki hai', 'my balance']:
                reply = f"💰 {customer.name}, आपका ₹{customer.balance} बकाया है।"
                twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                return

            # ---- ORDER FLOW ----
            pending = TempOrder.query.filter_by(customer_id=customer.id).first()
            if pending:
                if any(w in msg_lower for w in ['ha','han','haan','yes','confirm','ok','ठीक है','हाँ','कन्फर्म']):
                    ok, result = create_order_from_temp(pending)
                    if ok:
                        reply = f"""✅ *ऑर्डर कन्फर्म!*

{pending.quantity} {pending.unit} {pending.product_name}
कुल: ₹{pending.total}
ऑर्डर ID: #{result.id}
धन्यवाद! 🙏"""
                    else:
                        reply = f"❌ {result}"
                elif any(w in msg_lower for w in ['nahi','no','cancel','mat karo','नहीं','कैंसल']):
                    db.session.delete(pending)
                    db.session.commit()
                    reply = "❌ ऑर्डर कैंसल कर दिया गया।"
                else:
                    mins = max(1, int((pending.expires_at - datetime.utcnow()).total_seconds() / 60))
                    reply = f"""🤔 *ऑर्डर पेंडिंग है*

{pending.quantity} {pending.unit} {pending.product_name}
कुल: ₹{pending.total}

✅ कन्फर्म के लिए: "ha" या "confirm"
❌ कैंसल के लिए: "nahi" या "cancel"
⏳ {mins} मिनट बचे हैं।"""
                twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                return

            # New order detection
            patterns = [
                (r'(\d+)\s*(?:kg|किलो)\s*(?:चाय|chai|tea|patti)', 'चाय', 'kg'),
                (r'(\d+)\s*(?:kg|किलो)\s*(?:नमक|namak|salt)', 'नमक', 'kg'),
                (r'(\d+)\s*(?:piece|पीस)\s*(?:बिस्कुट|biscuit)', 'बिस्कुट', 'piece'),
            ]
            for pat, ptype, unit in patterns:
                m = re.search(pat, msg_lower)
                if m:
                    qty = int(m.group(1))
                    prod = None
                    if ptype == 'चाय':
                        prod = Product.query.filter(Product.name.contains('चाय')).first()
                    elif ptype == 'नमक':
                        prod = Product.query.filter(Product.name.contains('नमक')).first()
                    elif ptype == 'बिस्कुट':
                        prod = Product.query.filter(Product.name.contains('बिस्कुट')).first()
                    if prod and prod.stock >= qty:
                        total = prod.price * qty
                        temp = TempOrder(
                            customer_id=customer.id,
                            product_id=prod.id,
                            product_name=prod.name,
                            quantity=qty,
                            unit=unit,
                            price=prod.price,
                            total=total
                        )
                        db.session.add(temp)
                        db.session.commit()
                        reply = f"""🤔 *कन्फर्मेशन*

{qty} {unit} {prod.name}
कुल: ₹{total}

✅ कन्फर्म के लिए: "ha" या "confirm"
❌ कैंसल के लिए: "nahi" या "cancel"

कन्फर्म करना है?"""
                        twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                        return
                    elif prod and prod.stock < qty:
                        twilio_client.messages.create(body=f"❌ केवल {prod.stock} {prod.unit} स्टॉक में है।", from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                        return

            # Default: AI reply
            ai_reply = get_ai_reply(customer, body)
            twilio_client.messages.create(body=ai_reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
            print(f"✅ Replied to {from_number}")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        try:
            twilio_client.messages.create(body="⚠️ थोड़ी देर में try करें। 🙏", from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
        except:
            pass

def process_image(from_number, media_url):
    try:
        with app.app_context():
            customer = Customer.query.filter_by(phone=from_number).first()
            if not customer:
                return
            payment_req = PaymentRequest.query.filter_by(customer_id=customer.id, status='pending').order_by(PaymentRequest.created_at.desc()).first()
            if not payment_req:
                twilio_client.messages.create(
                    body="❌ No pending payment request found. Please use 'pay <amount>' first.",
                    from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
                    to=from_number
                )
                return
            screenshot = PaymentScreenshot(payment_request_id=payment_req.id, media_url=media_url)
            db.session.add(screenshot)
            payment_req.screenshot_url = media_url
            db.session.commit()
            biz = Business.query.first()
            shopkeeper_number = biz.phone if biz else os.getenv('TWILIO_WHATSAPP_NUMBER')
            msg = f"📸 *Payment Screenshot Received*\nCustomer: {customer.name} ({customer.phone})\nAmount: ₹{payment_req.amount}\n\nPlease verify and approve via dashboard or reply 'approve {payment_req.id}'"
            try:
                twilio_client.messages.create(
                    body=msg,
                    from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
                    to=shopkeeper_number
                )
            except Exception as e:
                print(f"Failed to notify shopkeeper: {e}")
            twilio_client.messages.create(
                body="✅ Screenshot received. The shopkeeper will verify and confirm your payment shortly.",
                from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
                to=from_number
            )
    except Exception as e:
        print(f"Error processing image: {e}")
        traceback.print_exc()

@app.route('/webhook', methods=['POST'])
def webhook():
    from_number = request.form.get('From')
    body = request.form.get('Body', '').strip()
    media_url = request.form.get('MediaUrl0')
    print(f"\n📩 {from_number}: {body} (Media: {media_url})")
    if media_url:
        executor.submit(process_image, from_number, media_url)
    else:
        executor.submit(process_message, from_number, body)
    return "OK", 200

@app.route('/')
def home():
    return "✅ DukaanAI Bot with Full Features"

@app.route('/health')
def health():
    return jsonify({"status": "alive", "time": datetime.now().isoformat()})

# ------------------------- BUSINESS SETTINGS API -------------------------
@app.route('/api/business', methods=['GET'])
def get_business():
    biz = Business.query.first()
    if not biz:
        biz = Business(phone=os.getenv('TWILIO_WHATSAPP_NUMBER'), name="My Shop", business_name="DukaanAI Shop")
        db.session.add(biz)
        db.session.commit()
    return jsonify({
        'name': biz.name,
        'address': biz.address,
        'phone': biz.phone,
        'gstin': biz.gstin,
        'upi_id': biz.upi_id
    })

@app.route('/api/business', methods=['PUT'])
def update_business():
    data = request.json
    biz = Business.query.first()
    if not biz:
        biz = Business(phone=os.getenv('TWILIO_WHATSAPP_NUMBER'))
        db.session.add(biz)
    if 'name' in data:
        biz.name = data['name']
    if 'address' in data:
        biz.address = data['address']
    if 'phone' in data:
        biz.phone = data['phone']
    if 'gstin' in data:
        biz.gstin = data['gstin']
    if 'upi_id' in data:
        biz.upi_id = data['upi_id']
    db.session.commit()
    return jsonify({'message': 'Business details updated'})

# ------------------------- API ROUTES (frontend) -------------------------
@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify([{
        'id': p.id, 'name': p.name, 'price': p.price, 'stock': p.stock,
        'unit': p.unit, 'total_sold': p.total_sold
    } for p in Product.query.all()])

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    biz = Business.query.first()
    p = Product(business_id=biz.id, name=data['name'], price=float(data['price']), unit=data['unit'], stock=int(data['stock']))
    db.session.add(p)
    db.session.commit()
    return jsonify({'message': 'Product added', 'id': p.id}), 201

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    p = Product.query.get_or_404(id)
    data = request.json
    if 'name' in data: p.name = data['name']
    if 'price' in data: p.price = float(data['price'])
    if 'stock' in data: p.stock = int(data['stock'])
    if 'unit' in data: p.unit = data['unit']
    db.session.commit()
    return jsonify({'message': 'Product updated'})

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    p = Product.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'message': 'Product deleted'})

@app.route('/api/customers', methods=['GET'])
def get_customers():
    return jsonify([{
        'id': c.id, 'name': c.name, 'phone': c.phone, 'balance': c.balance,
        'total_orders': c.total_orders, 'total_spent': c.total_spent,
        'last_order_date': c.last_order_date.strftime('%Y-%m-%d') if c.last_order_date else 'Never',
        'created_at': c.created_at.strftime('%Y-%m-%d')
    } for c in Customer.query.all()])

@app.route('/api/customers', methods=['POST'])
def add_customer():
    data = request.json
    biz = Business.query.first()
    c = Customer(business_id=biz.id, name=data['name'], phone=data['phone'], balance=float(data.get('balance', 0)))
    db.session.add(c)
    db.session.commit()
    return jsonify({'message': 'Customer added', 'id': c.id}), 201

@app.route('/api/orders', methods=['GET'])
def get_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        cust = Customer.query.get(o.customer_id)
        result.append({
            'id': o.id,
            'customer': cust.name if cust else 'Unknown',
            'total': o.total,
            'status': o.status,
            'source': o.source,
            'date': o.created_at.strftime('%Y-%m-%d'),
            'time': o.created_at.strftime('%H:%M')
        })
    return jsonify(result)

@app.route('/api/orders/<int:id>', methods=['PATCH'])
def update_order_status(id):
    order = Order.query.get_or_404(id)
    data = request.json
    old_status = order.status
    if 'status' in data:
        order.status = data['status']
        if old_status != 'completed' and order.status == 'completed':
            items = json.loads(order.items)
            for item in items:
                product = Product.query.get(item['product_id'])
                if product:
                    product.stock -= item['quantity']
                    product.total_sold += item['quantity']
        db.session.commit()
    return jsonify({'message': 'Order updated'})

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    today_orders = Order.query.filter(db.func.date(Order.created_at) == today).count()
    today_revenue = db.session.query(db.func.sum(Order.total)).filter(db.func.date(Order.created_at) == today).scalar() or 0
    pending = Order.query.filter_by(status='pending').count()
    low_stock = Product.query.filter(Product.stock < 10).count()
    customers = Customer.query.count()
    new_customers = Customer.query.filter(db.func.date(Customer.created_at) >= week_ago).count()
    total_balance = db.session.query(db.func.sum(Customer.balance)).scalar() or 0
    return jsonify({
        'today': {'orders': today_orders, 'revenue': float(today_revenue)},
        'pending': pending,
        'lowStock': low_stock,
        'customers': {'total': customers, 'new': new_customers},
        'totalBalance': float(total_balance)
    })

@app.route('/api/analytics', methods=['GET'])
def analytics():
    return jsonify({'revenueTrends': [], 'topProducts': [], 'customerGrowth': [], 'orderCompletion': []})

@app.route('/api/udhaar/customers', methods=['GET'])
def get_udhaar_customers():
    customers = Customer.query.filter(Customer.balance != 0).order_by(Customer.balance.desc()).all()
    result = [{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'balance': c.balance,
        'total_orders': c.total_orders,
        'last_order_date': c.last_order_date.strftime('%Y-%m-%d') if c.last_order_date else None
    } for c in customers]
    total_outstanding = db.session.query(db.func.sum(Customer.balance)).scalar() or 0
    return jsonify({'customers': result, 'totalOutstanding': total_outstanding})

@app.route('/api/udhaar/transactions/<int:customer_id>', methods=['GET'])
def get_udhaar_transactions(customer_id):
    transactions = BalanceTransaction.query.filter_by(customer_id=customer_id).order_by(BalanceTransaction.created_at.desc()).all()
    result = [{
        'id': t.id,
        'amount': t.amount,
        'new_balance': t.new_balance,
        'reason': t.reason,
        'source': t.source,
        'created_at': t.created_at.strftime('%Y-%m-%d %H:%M')
    } for t in transactions]
    return jsonify(result)

@app.route('/api/udhaar/add', methods=['POST'])
def api_add_udhaar():
    data = request.json
    customer_id = data.get('customer_id')
    amount = data.get('amount')
    reason = data.get('reason', 'Added via dashboard')
    if not customer_id or not amount or amount <= 0:
        return jsonify({'error': 'Invalid customer or amount'}), 400
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    success, msg = add_balance(customer.phone, amount, reason, source='web')
    if success:
        return jsonify({'message': msg, 'new_balance': customer.balance})
    else:
        return jsonify({'error': msg}), 400

@app.route('/api/udhaar/adjust', methods=['POST'])
def api_adjust_udhaar():
    data = request.json
    customer_id = data.get('customer_id')
    amount = data.get('amount')
    reason = data.get('reason', 'Manual adjustment')
    if not customer_id or amount == 0:
        return jsonify({'error': 'Invalid customer or amount'}), 400
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    if amount > 0:
        success, msg = add_balance(customer.phone, amount, reason, source='web')
    else:
        success, msg = reduce_balance(customer.phone, -amount, reason, source='web')
    if success:
        return jsonify({'message': msg, 'new_balance': customer.balance})
    else:
        return jsonify({'error': msg}), 400

@app.route('/api/udhaar/send_reminder', methods=['POST'])
def send_reminder():
    data = request.json
    customer_id = data.get('customer_id')
    if not customer_id:
        return jsonify({'error': 'Customer ID required'}), 400
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    if customer.balance <= 0:
        return jsonify({'error': 'Customer has no pending balance'}), 400
    biz = Business.query.first()
    shop_name = biz.name if biz else "Shop"
    msg = f"🔔 *Reminder from {shop_name}*\n\nनमस्ते {customer.name}, आपका ₹{customer.balance} बकाया है। कृपया जल्दी भुगतान करें।\nधन्यवाद! 🙏"
    try:
        twilio_client.messages.create(
            body=msg,
            from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
            to=customer.phone
        )
        return jsonify({'message': f'Reminder sent to {customer.name}'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payment_requests', methods=['GET'])
def get_payment_requests():
    requests = PaymentRequest.query.filter_by(status='pending').order_by(PaymentRequest.created_at.desc()).all()
    result = []
    for req in requests:
        cust = Customer.query.get(req.customer_id)
        result.append({
            'id': req.id,
            'customer_name': cust.name if cust else 'Unknown',
            'customer_phone': cust.phone if cust else '',
            'amount': req.amount,
            'screenshot_url': req.screenshot_url,
            'created_at': req.created_at.strftime('%Y-%m-%d %H:%M')
        })
    return jsonify(result)

@app.route('/api/payment_requests/<int:req_id>/approve', methods=['POST'])
def approve_payment_request(req_id):
    payment_req = PaymentRequest.query.get(req_id)
    if not payment_req or payment_req.status != 'pending':
        return jsonify({'error': 'Invalid request'}), 400
    customer = Customer.query.get(payment_req.customer_id)
    success, msg = reduce_balance(customer.phone, payment_req.amount, source='dashboard_approve')
    if success:
        payment_req.status = 'completed'
        payment_req.completed_at = datetime.utcnow()
        db.session.commit()
        try:
            twilio_client.messages.create(
                body=f"✅ Your payment of ₹{payment_req.amount} has been verified and approved. Your new balance is ₹{customer.balance}.",
                from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
                to=customer.phone
            )
        except: pass
        return jsonify({'message': 'Payment approved', 'new_balance': customer.balance})
    else:
        return jsonify({'error': msg}), 400

@app.route('/trigger_reminders', methods=['POST'])
def trigger_reminders():
    def send_reminders():
        with app.app_context():
            today = datetime.utcnow().date()
            customers = Customer.query.filter(Customer.balance > 0).all()
            biz = Business.query.first()
            shop_name = biz.name if biz else "DukaanAI Shop"
            sent = 0
            for cust in customers:
                if cust.last_reminder_date and (today - cust.last_reminder_date.date()).days < 7:
                    continue
                msg = f"🔔 *Reminder from {shop_name}*\n\nनमस्ते {cust.name}, आपका ₹{cust.balance} बकाया है। कृपया जल्दी भुगतान करें।\nधन्यवाद! 🙏"
                try:
                    twilio_client.messages.create(
                        body=msg,
                        from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}',
                        to=cust.phone
                    )
                    cust.last_reminder_date = datetime.utcnow()
                    db.session.commit()
                    sent += 1
                except Exception as e:
                    print(f"Failed to send reminder to {cust.name}: {e}")
            print(f"✅ Sent {sent} reminders")
    executor.submit(send_reminders)
    return jsonify({"status": "reminders triggered"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)