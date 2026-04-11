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
from apscheduler.schedulers.background import BackgroundScheduler

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
    name = db.Column(db.String(100))
    business_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))
    phone = db.Column(db.String(20), index=True)
    name = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0)          # positive = customer owes money
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    last_order_date = db.Column(db.DateTime, nullable=True)
    last_reminder_date = db.Column(db.DateTime, nullable=True)   # for weekly reminders
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

# ------------------------- INIT DB -------------------------
with app.app_context():
    db.create_all()
    if not Business.query.first():
        biz = Business(phone=os.getenv('TWILIO_WHATSAPP_NUMBER'), name="Test Shop", business_name="DukaanAI Demo")
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

# ------------------------- ORDER HELPERS -------------------------
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
        product.stock -= temp.quantity
        product.total_sold += temp.quantity
        customer.total_orders += 1
        customer.total_spent += temp.total
        customer.last_order_date = datetime.utcnow()
        # Increase balance (customer owes money)
        customer.balance += temp.total
        db.session.delete(temp)
        db.session.commit()
        return True, order
    except Exception as e:
        db.session.rollback()
        return False, str(e)

# ------------------------- DEEPSEEK AI (requests) -------------------------
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

# ------------------------- KHATABOOK FUNCTIONS (Udhaar) -------------------------
def add_balance(customer_phone, amount, description=""):
    """Increase customer's balance (customer owes more)"""
    customer = Customer.query.filter_by(phone=customer_phone).first()
    if not customer:
        return False, "Customer not found"
    customer.balance += amount
    db.session.commit()
    return True, f"₹{amount} added to {customer.name}'s balance. Total due: ₹{customer.balance}"

def reduce_balance(customer_phone, amount):
    """Reduce balance when customer pays"""
    customer = Customer.query.filter_by(phone=customer_phone).first()
    if not customer:
        return False, "Customer not found"
    if amount > customer.balance:
        return False, f"Amount exceeds current due ₹{customer.balance}"
    customer.balance -= amount
    db.session.commit()
    return True, f"Payment of ₹{amount} received. Remaining due: ₹{customer.balance}"

# ------------------------- WEEKLY REMINDER JOB -------------------------
def send_weekly_reminders():
    """Run every Sunday at 9 AM. Send reminder to customers with balance > 0."""
    with app.app_context():
        today = datetime.utcnow().date()
        # Only send if today is Sunday (weekday() returns 6 for Sunday)
        if today.weekday() != 6:
            return
        customers = Customer.query.filter(Customer.balance > 0).all()
        biz = Business.query.first()
        shop_name = biz.business_name if biz else "DukaanAI Shop"
        for cust in customers:
            # Skip if already reminded this week
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
                print(f"Reminder sent to {cust.name} ({cust.phone})")
            except Exception as e:
                print(f"Failed to send reminder to {cust.name}: {e}")

# Schedule weekly reminders – runs every Sunday at 9 AM
scheduler = BackgroundScheduler()
scheduler.add_job(func=send_weekly_reminders, trigger="cron", day_of_week='sun', hour=9, minute=0)
scheduler.start()

# ------------------------- WHATSAPP HANDLER -------------------------
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

            # ---- KHATABOOK COMMANDS (for shopkeeper – simple, can be extended) ----
            # Add udhaar (shopkeeper only – maybe protect with a secret code)
            if msg_lower.startswith("add udhaar ") or msg_lower.startswith("add udhaar"):
                # Format: add udhaar <phone> <amount> or add udhaar <customer name> <amount>
                parts = body.split()
                if len(parts) >= 3:
                    # try to find by phone or name
                    target = parts[2]
                    amount = float(parts[3]) if len(parts) > 3 else 0
                    cust = Customer.query.filter((Customer.phone == target) | (Customer.name == target)).first()
                    if cust and amount > 0:
                        success, res = add_balance(cust.phone, amount)
                        reply = res
                    else:
                        reply = "❌ Customer not found or invalid amount"
                else:
                    reply = "Usage: add udhaar <customer name/phone> <amount>"
                twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                return

            # Pay command (customer pays)
            if msg_lower.startswith("pay "):
                parts = body.split()
                if len(parts) >= 2:
                    try:
                        amount = float(parts[1])
                        success, res = reduce_balance(customer.phone, amount)
                        reply = res
                    except:
                        reply = "❌ Invalid amount"
                else:
                    reply = "Usage: pay <amount>"
                twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                return

            # Check balance
            if msg_lower in ['balance', 'बाकी', 'kitna baki hai', 'my balance']:
                reply = f"💰 {customer.name}, आपका ₹{customer.balance} बकाया है।"
                twilio_client.messages.create(body=reply, from_=f'whatsapp:{os.getenv("TWILIO_WHATSAPP_NUMBER")}', to=from_number)
                return

            # ---- ORDER FLOW (existing) ----
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

            # New order detection (existing)
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

@app.route('/webhook', methods=['POST'])
def webhook():
    from_number = request.form.get('From')
    body = request.form.get('Body', '').strip()
    print(f"\n📩 {from_number}: {body}")
    executor.submit(process_message, from_number, body)
    return "OK", 200

@app.route('/')
def home():
    return "✅ DukaanAI Bot with Khatabook & Weekly Reminders"

@app.route('/health')
def health():
    return jsonify({"status": "alive", "time": datetime.now().isoformat()})

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
    if 'status' in data:
        order.status = data['status']
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)