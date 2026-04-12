import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [dashboard, setDashboard] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');

  // Product form state
  const [showProductForm, setShowProductForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [newProduct, setNewProduct] = useState({
    name: '',
    price: '',
    unit: 'kg',
    stock: ''
  });

  // Customer form state
  const [showCustomerForm, setShowCustomerForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [newCustomer, setNewCustomer] = useState({
    name: '',
    phone: '',
    balance: ''
  });

  // Order filter
  const [orderFilter, setOrderFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Udhaar state
  const [udhaarCustomers, setUdhaarCustomers] = useState([]);
  const [totalOutstanding, setTotalOutstanding] = useState(0);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [showTransactionModal, setShowTransactionModal] = useState(false);
  const [showUdhaarModal, setShowUdhaarModal] = useState(false);
  const [udhaarAmount, setUdhaarAmount] = useState('');
  const [udhaarReason, setUdhaarReason] = useState('');
  const [udhaarAction, setUdhaarAction] = useState('add'); // 'add' or 'adjust'

  // Business settings
  const [business, setBusiness] = useState({ name: '', address: '', phone: '', gstin: '', upi_id: '' });

  const API_URL = process.env.REACT_APP_API_URL || 'https://dukaanai-whatsapp-1.onrender.com';

  // Fetch all data
  const fetchAllData = async () => {
    try {
      const [productsRes, ordersRes, customersRes, dashboardRes] = await Promise.all([
        fetch(`${API_URL}/api/products`),
        fetch(`${API_URL}/api/orders`),
        fetch(`${API_URL}/api/customers`),
        fetch(`${API_URL}/api/dashboard`)
      ]);
      setProducts(await productsRes.json());
      setOrders(await ordersRes.json());
      setCustomers(await customersRes.json());
      setDashboard(await dashboardRes.json());
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  const fetchUdhaarCustomers = async () => {
    try {
      const res = await fetch(`${API_URL}/api/udhaar/customers`);
      const data = await res.json();
      setUdhaarCustomers(data.customers);
      setTotalOutstanding(data.totalOutstanding);
    } catch (error) {
      console.error('Error fetching udhaar customers:', error);
    }
  };

  const fetchBusiness = async () => {
    try {
      const res = await fetch(`${API_URL}/api/business`);
      const data = await res.json();
      setBusiness(data);
    } catch (error) {
      console.error('Error fetching business:', error);
    }
  };

  const fetchTransactions = async (customerId) => {
    try {
      const res = await fetch(`${API_URL}/api/udhaar/transactions/${customerId}`);
      const data = await res.json();
      setTransactions(data);
      setShowTransactionModal(true);
    } catch (error) {
      console.error('Error fetching transactions:', error);
    }
  };

  useEffect(() => {
    fetchAllData();
    fetchUdhaarCustomers();
    fetchBusiness();
  }, []);

  // Product functions
  const handleAddProduct = async () => {
    try {
      const response = await fetch(`${API_URL}/api/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProduct.name,
          price: parseFloat(newProduct.price),
          unit: newProduct.unit,
          stock: parseInt(newProduct.stock)
        })
      });
      if (response.ok) {
        fetchAllData();
        setShowProductForm(false);
        setNewProduct({ name: '', price: '', unit: 'kg', stock: '' });
        alert('✅ Product added!');
      }
    } catch (error) {
      console.error('Error adding product:', error);
    }
  };

  const handleUpdateProduct = async () => {
    try {
      const response = await fetch(`${API_URL}/api/products/${editingProduct.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingProduct)
      });
      if (response.ok) {
        fetchAllData();
        setEditingProduct(null);
        alert('✅ Product updated!');
      }
    } catch (error) {
      console.error('Error updating product:', error);
    }
  };

  const handleDeleteProduct = async (id) => {
    if (window.confirm('Delete this product?')) {
      try {
        const response = await fetch(`${API_URL}/api/products/${id}`, { method: 'DELETE' });
        if (response.ok) {
          fetchAllData();
          alert('✅ Product deleted!');
        }
      } catch (error) {
        console.error('Error deleting product:', error);
      }
    }
  };

  // Customer functions
  const handleAddCustomer = async () => {
    try {
      const response = await fetch(`${API_URL}/api/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCustomer)
      });
      if (response.ok) {
        fetchAllData();
        setShowCustomerForm(false);
        setNewCustomer({ name: '', phone: '', balance: '' });
        alert('✅ Customer added!');
      }
    } catch (error) {
      console.error('Error adding customer:', error);
    }
  };

  const handleUpdateCustomer = async () => {
    try {
      const response = await fetch(`${API_URL}/api/customers/${editingCustomer.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingCustomer)
      });
      if (response.ok) {
        fetchAllData();
        setEditingCustomer(null);
        alert('✅ Customer updated!');
      }
    } catch (error) {
      console.error('Error updating customer:', error);
    }
  };

  const handleDeleteCustomer = async (id) => {
    if (window.confirm('Delete this customer?')) {
      try {
        const response = await fetch(`${API_URL}/api/customers/${id}`, { method: 'DELETE' });
        if (response.ok) {
          fetchAllData();
          alert('✅ Customer deleted!');
        }
      } catch (error) {
        console.error('Error deleting customer:', error);
      }
    }
  };

  // Order functions
  const handleUpdateOrderStatus = async (orderId, newStatus) => {
    try {
      const response = await fetch(`${API_URL}/api/orders/${orderId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (response.ok) {
        fetchAllData();
      }
    } catch (error) {
      console.error('Error updating order:', error);
    }
  };

  // Udhaar functions
  const handleUdhaarSubmit = async () => {
    if (!selectedCustomer) return;
    const amount = parseFloat(udhaarAmount);
    if (isNaN(amount) || amount === 0) {
      alert('Please enter a valid amount');
      return;
    }
    const url = udhaarAction === 'add' ? `${API_URL}/api/udhaar/add` : `${API_URL}/api/udhaar/adjust`;
    const body = udhaarAction === 'add'
      ? { customer_id: selectedCustomer.id, amount: amount, reason: udhaarReason }
      : { customer_id: selectedCustomer.id, amount: amount, reason: udhaarReason };
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (res.ok) {
        alert('Udhaar updated successfully');
        fetchUdhaarCustomers();
        fetchAllData();
        setShowUdhaarModal(false);
        setUdhaarAmount('');
        setUdhaarReason('');
      } else {
        const err = await res.json();
        alert(err.error || 'Failed to update udhaar');
      }
    } catch (error) {
      console.error('Error updating udhaar:', error);
    }
  };

  const sendReminder = async (customerId) => {
    try {
      const res = await fetch(`${API_URL}/api/udhaar/send_reminder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: customerId })
      });
      if (res.ok) {
        alert('Reminder sent successfully');
      } else {
        const err = await res.json();
        alert(err.error || 'Failed to send reminder');
      }
    } catch (error) {
      console.error('Error sending reminder:', error);
    }
  };

  // Business settings
  const saveBusiness = async () => {
    try {
      await fetch(`${API_URL}/api/business`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(business)
      });
      alert('Business details saved!');
    } catch (error) {
      console.error('Error saving business:', error);
      alert('Failed to save business details');
    }
  };

  // Filter orders
  const filteredOrders = orders.filter(order => {
    if (orderFilter !== 'all' && order.status !== orderFilter) return false;
    if (searchTerm && !order.customer.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    marginBottom: '1rem',
    border: '2px solid #e5e7eb',
    borderRadius: '8px',
    fontSize: '1rem',
    outline: 'none'
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#ECE5DD' }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ color: '#075E54' }}>Loading DukaanDash...</h2>
      </div>
    </div>
  );

  return (
    <div className="App">
      {/* Header */}
      <div style={{ background: 'linear-gradient(135deg, #075E54 0%, #128C7E 100%)', color: 'white', padding: '2rem 1rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2.5rem', margin: '0 0 0.5rem 0' }}>📱 DukaanDash</h1>
        <p style={{ fontSize: '1.1rem', opacity: 0.9 }}>
          Orders: {dashboard.today?.orders || 0} today | Revenue: ₹{dashboard.today?.revenue || 0}
        </p>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', margin: '2rem 0', borderBottom: '2px solid #e5e7eb', paddingBottom: '1rem', flexWrap: 'wrap' }}>
        {['dashboard', 'products', 'orders', 'customers', 'udhaar', 'settings'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '0.75rem 2rem',
              background: activeTab === tab ? '#25D366' : 'transparent',
              color: activeTab === tab ? 'white' : '#4b5563',
              border: activeTab === tab ? 'none' : '2px solid #e5e7eb',
              borderRadius: '30px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: 'pointer',
              textTransform: 'capitalize'
            }}
          >
            {tab === 'dashboard' ? '🏠 Dashboard' :
              tab === 'products' ? '📦 Products' :
                tab === 'orders' ? '📋 Orders' :
                  tab === 'customers' ? '👥 Customers' :
                    tab === 'udhaar' ? '💰 Udhaar' : '⚙️ Settings'}
          </button>
        ))}
      </div>

      <div className="main-content">
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div style={{ padding: '0 1rem' }}>
            <h2 style={{ color: '#075E54', marginBottom: '1.5rem' }}>Dashboard Overview</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
              <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <h3 style={{ color: '#6b7280', fontSize: '0.9rem' }}>Today's Orders</h3>
                <p style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#25D366' }}>{dashboard.today?.orders || 0}</p>
                <p style={{ color: '#10b981' }}>Revenue: ₹{dashboard.today?.revenue || 0}</p>
              </div>
              <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <h3 style={{ color: '#6b7280', fontSize: '0.9rem' }}>Pending Orders</h3>
                <p style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#f59e0b' }}>{dashboard.pending || 0}</p>
              </div>
              <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <h3 style={{ color: '#6b7280', fontSize: '0.9rem' }}>Low Stock</h3>
                <p style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#ef4444' }}>{dashboard.lowStock || 0}</p>
              </div>
              <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <h3 style={{ color: '#6b7280', fontSize: '0.9rem' }}>Total Outstanding</h3>
                <p style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#dc2626' }}>₹{dashboard.totalBalance || 0}</p>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <button onClick={() => setActiveTab('products')} style={{ background: '#25D366', color: 'white', border: 'none', padding: '1rem', borderRadius: '12px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>
                📦 Manage Products
              </button>
              <button onClick={() => setActiveTab('orders')} style={{ background: '#075E54', color: 'white', border: 'none', padding: '1rem', borderRadius: '12px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>
                📋 View Orders
              </button>
            </div>
          </div>
        )}

        {/* Products Tab */}
        {activeTab === 'products' && (
          <div style={{ padding: '0 1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ color: '#075E54' }}>📦 Products Catalog</h2>
              <button onClick={() => setShowProductForm(true)} style={{ background: '#25D366', color: 'white', border: 'none', padding: '0.75rem 1.5rem', borderRadius: '30px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>
                + Add Product
              </button>
            </div>

            {(showProductForm || editingProduct) && (
              <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                <div style={{ background: 'white', padding: '2rem', borderRadius: '12px', width: '90%', maxWidth: '500px' }}>
                  <h3 style={{ color: '#075E54', marginBottom: '1.5rem' }}>{editingProduct ? 'Edit Product' : 'Add New Product'}</h3>
                  <div className="form-group">
                    <label htmlFor="productName" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Product Name</label>
                    <input id="productName" name="productName" type="text" placeholder="Product Name" value={editingProduct ? editingProduct.name : newProduct.name} onChange={(e) => editingProduct ? setEditingProduct({ ...editingProduct, name: e.target.value }) : setNewProduct({ ...newProduct, name: e.target.value })} style={inputStyle} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="productPrice" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Price (₹)</label>
                    <input id="productPrice" name="productPrice" type="number" placeholder="Price (₹)" value={editingProduct ? editingProduct.price : newProduct.price} onChange={(e) => editingProduct ? setEditingProduct({ ...editingProduct, price: e.target.value }) : setNewProduct({ ...newProduct, price: e.target.value })} style={inputStyle} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="productUnit" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Unit</label>
                    <select id="productUnit" name="productUnit" value={editingProduct ? editingProduct.unit : newProduct.unit} onChange={(e) => editingProduct ? setEditingProduct({ ...editingProduct, unit: e.target.value }) : setNewProduct({ ...newProduct, unit: e.target.value })} style={inputStyle}>
                      <option value="kg">kg (किलो)</option>
                      <option value="piece">piece (पीस)</option>
                      <option value="dozen">dozen (दर्जन)</option>
                      <option value="litre">litre (लीटर)</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="productStock" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Stock Quantity</label>
                    <input id="productStock" name="productStock" type="number" placeholder="Stock Quantity" value={editingProduct ? editingProduct.stock : newProduct.stock} onChange={(e) => editingProduct ? setEditingProduct({ ...editingProduct, stock: e.target.value }) : setNewProduct({ ...newProduct, stock: e.target.value })} style={inputStyle} />
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                    <button onClick={editingProduct ? handleUpdateProduct : handleAddProduct} style={{ flex: 1, background: '#25D366', color: 'white', border: 'none', padding: '0.75rem', borderRadius: '8px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>{editingProduct ? 'Update' : 'Add'} Product</button>
                    <button onClick={() => { setShowProductForm(false); setEditingProduct(null); }} style={{ flex: 1, background: '#f3f4f6', color: '#4b5563', border: 'none', padding: '0.75rem', borderRadius: '8px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>Cancel</button>
                  </div>
                </div>
              </div>
            )}

            <div style={{ background: 'white', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#DCF8C6' }}>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Product</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Price</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Stock</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Unit</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Sold</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map(p => (
                    <tr key={p.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '1rem' }}>{p.name}</td>
                      <td style={{ padding: '1rem' }}>₹{p.price}</td>
                      <td style={{ padding: '1rem', color: p.stock < 10 ? '#ef4444' : '#10b981', fontWeight: '600' }}>{p.stock}</td>
                      <td style={{ padding: '1rem' }}>{p.unit}</td>
                      <td style={{ padding: '1rem' }}>{p.total_sold || 0}</td>
                      <td style={{ padding: '1rem' }}>
                        <button onClick={() => setEditingProduct(p)} style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', marginRight: '8px', cursor: 'pointer' }}>Edit</button>
                        <button onClick={() => handleDeleteProduct(p.id)} style={{ background: '#ef4444', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer' }}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div style={{ padding: '0 1rem' }}>
            <h2 style={{ color: '#075E54', marginBottom: '1.5rem' }}>📋 Orders</h2>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
              <input id="orderSearch" name="orderSearch" type="text" placeholder="Search customer..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} style={{ flex: 1, padding: '0.5rem', border: '2px solid #e5e7eb', borderRadius: '8px', fontSize: '1rem' }} />
              <select id="orderFilter" name="orderFilter" value={orderFilter} onChange={(e) => setOrderFilter(e.target.value)} style={{ padding: '0.5rem', border: '2px solid #e5e7eb', borderRadius: '8px', fontSize: '1rem' }}>
                <option value="all">All Orders</option>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div style={{ background: 'white', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#DCF8C6' }}>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Order ID</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Customer</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Total</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Status</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Source</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Date</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map(o => (
                    <tr key={o.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '1rem', fontWeight: '500' }}>#{o.id}</td>
                      <td style={{ padding: '1rem' }}>{o.customer}</td>
                      <td style={{ padding: '1rem', fontWeight: '600', color: '#25D366' }}>₹{o.total}</td>
                      <td style={{ padding: '1rem' }}>
                        <select id={`orderStatus_${o.id}`} name={`orderStatus_${o.id}`} value={o.status} onChange={(e) => handleUpdateOrderStatus(o.id, e.target.value)} style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #25D366', background: o.status === 'pending' ? '#fef3c7' : o.status === 'completed' ? '#DCF8C6' : '#fee2e2' }}>
                          <option value="pending">Pending</option>
                          <option value="processing">Processing</option>
                          <option value="completed">Completed</option>
                          <option value="cancelled">Cancelled</option>
                        </select>
                      </td>
                      <td style={{ padding: '1rem', textTransform: 'capitalize' }}>{o.source}</td>
                      <td style={{ padding: '1rem' }}>{o.date} {o.time}</td>
                      <td style={{ padding: '1rem' }}>
                        <button onClick={() => window.open(`https://wa.me/${o.customer_phone}`, '_blank')} style={{ background: '#25D366', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer' }}>WhatsApp</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Customers Tab */}
        {activeTab === 'customers' && (
          <div style={{ padding: '0 1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ color: '#075E54' }}>👥 Customers</h2>
              <button onClick={() => setShowCustomerForm(true)} style={{ background: '#25D366', color: 'white', border: 'none', padding: '0.75rem 1.5rem', borderRadius: '30px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>+ Add Customer</button>
            </div>

            {(showCustomerForm || editingCustomer) && (
              <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                <div style={{ background: 'white', padding: '2rem', borderRadius: '12px', width: '90%', maxWidth: '500px' }}>
                  <h3 style={{ color: '#075E54', marginBottom: '1.5rem' }}>{editingCustomer ? 'Edit Customer' : 'Add Customer'}</h3>
                  <div className="form-group">
                    <label htmlFor="customerName" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Customer Name</label>
                    <input id="customerName" name="customerName" type="text" placeholder="Customer Name" value={editingCustomer ? editingCustomer.name : newCustomer.name} onChange={(e) => editingCustomer ? setEditingCustomer({ ...editingCustomer, name: e.target.value }) : setNewCustomer({ ...newCustomer, name: e.target.value })} style={inputStyle} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="customerPhone" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Phone Number</label>
                    <input id="customerPhone" name="customerPhone" type="tel" placeholder="Phone Number" value={editingCustomer ? editingCustomer.phone : newCustomer.phone} onChange={(e) => editingCustomer ? setEditingCustomer({ ...editingCustomer, phone: e.target.value }) : setNewCustomer({ ...newCustomer, phone: e.target.value })} style={inputStyle} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="customerBalance" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Balance (₹)</label>
                    <input id="customerBalance" name="customerBalance" type="number" placeholder="Balance (₹)" value={editingCustomer ? editingCustomer.balance : newCustomer.balance} onChange={(e) => editingCustomer ? setEditingCustomer({ ...editingCustomer, balance: e.target.value }) : setNewCustomer({ ...newCustomer, balance: e.target.value })} style={inputStyle} />
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                    <button onClick={editingCustomer ? handleUpdateCustomer : handleAddCustomer} style={{ flex: 1, background: '#25D366', color: 'white', border: 'none', padding: '0.75rem', borderRadius: '8px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>{editingCustomer ? 'Update' : 'Add'} Customer</button>
                    <button onClick={() => { setShowCustomerForm(false); setEditingCustomer(null); }} style={{ flex: 1, background: '#f3f4f6', color: '#4b5563', border: 'none', padding: '0.75rem', borderRadius: '8px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>Cancel</button>
                  </div>
                </div>
              </div>
            )}

            <div style={{ background: 'white', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#DCF8C6' }}>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Name</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Phone</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Balance</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Orders</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Total Spent</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Last Order</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map(c => (
                    <tr key={c.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '1rem', fontWeight: '500' }}>{c.name}</td>
                      <td style={{ padding: '1rem' }}>{c.phone}</td>
                      <td style={{ padding: '1rem', fontWeight: '600', color: c.balance > 0 ? '#ef4444' : '#10b981' }}>₹{c.balance}</td>
                      <td style={{ padding: '1rem' }}>{c.total_orders || 0}</td>
                      <td style={{ padding: '1rem' }}>₹{c.total_spent || 0}</td>
                      <td style={{ padding: '1rem' }}>{c.last_order_date}</td>
                      <td style={{ padding: '1rem' }}>
                        <button onClick={() => setEditingCustomer(c)} style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', marginRight: '8px', cursor: 'pointer' }}>Edit</button>
                        <button onClick={() => handleDeleteCustomer(c.id)} style={{ background: '#ef4444', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer' }}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Udhaar Tab */}
        {activeTab === 'udhaar' && (
          <div style={{ padding: '0 1rem' }}>
            <h2 style={{ color: '#075E54', marginBottom: '1.5rem' }}>💰 Udhaar Management</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
              <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <h3 style={{ color: '#6b7280', fontSize: '0.9rem' }}>Total Outstanding</h3>
                <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#dc2626' }}>₹{totalOutstanding}</p>
              </div>
              <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <h3 style={{ color: '#6b7280', fontSize: '0.9rem' }}>Customers with Balance</h3>
                <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#075E54' }}>{udhaarCustomers.length}</p>
              </div>
            </div>

            <div style={{ background: 'white', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#DCF8C6' }}>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Name</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Phone</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Balance (₹)</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Last Order</th>
                    <th style={{ padding: '1rem', textAlign: 'left' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {udhaarCustomers.map(c => (
                    <tr key={c.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '1rem', fontWeight: '500' }}>{c.name}</td>
                      <td style={{ padding: '1rem' }}>{c.phone}</td>
                      <td style={{ padding: '1rem', fontWeight: '600', color: '#dc2626' }}>₹{c.balance}</td>
                      <td style={{ padding: '1rem' }}>{c.last_order_date || '-'}</td>
                      <td style={{ padding: '1rem' }}>
                        <button onClick={() => { setSelectedCustomer(c); setUdhaarAction('add'); setUdhaarAmount(''); setUdhaarReason(''); setShowUdhaarModal(true); }} style={{ background: '#25D366', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', marginRight: '8px', cursor: 'pointer' }}>➕ Add</button>
                        <button onClick={() => { setSelectedCustomer(c); setUdhaarAction('adjust'); setUdhaarAmount(''); setUdhaarReason(''); setShowUdhaarModal(true); }} style={{ background: '#f59e0b', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', marginRight: '8px', cursor: 'pointer' }}>🔄 Adjust</button>
                        <button onClick={() => fetchTransactions(c.id)} style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', marginRight: '8px', cursor: 'pointer' }}>📜 History</button>
                        <button onClick={() => sendReminder(c.id)} disabled={c.balance <= 0} style={{ background: c.balance > 0 ? '#8b5cf6' : '#cbd5e1', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer' }}>🔔 Reminder</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div style={{ padding: '0 1rem' }}>
            <h2 style={{ color: '#075E54', marginBottom: '1.5rem' }}>🏪 Business Settings</h2>
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <div className="form-group">
                <label htmlFor="businessName" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Business Name</label>
                <input id="businessName" name="businessName" className="form-input" value={business.name} onChange={e => setBusiness({ ...business, name: e.target.value })} style={inputStyle} />
              </div>
              <div className="form-group">
                <label htmlFor="businessAddress" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Address</label>
                <textarea id="businessAddress" name="businessAddress" className="form-textarea" value={business.address} onChange={e => setBusiness({ ...business, address: e.target.value })} rows="2" style={inputStyle} />
              </div>
              <div className="form-group">
                <label htmlFor="businessPhone" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>WhatsApp Number (Twilio)</label>
                <input id="businessPhone" name="businessPhone" className="form-input" value={business.phone} onChange={e => setBusiness({ ...business, phone: e.target.value })} style={inputStyle} />
              </div>
              <div className="form-group">
                <label htmlFor="businessGstin" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>GSTIN</label>
                <input id="businessGstin" name="businessGstin" className="form-input" value={business.gstin} onChange={e => setBusiness({ ...business, gstin: e.target.value })} style={inputStyle} />
              </div>
              <div className="form-group">
                <label htmlFor="businessUpiId" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>UPI ID (for payment links)</label>
                <input id="businessUpiId" name="businessUpiId" className="form-input" value={business.upi_id} onChange={e => setBusiness({ ...business, upi_id: e.target.value })} style={inputStyle} />
              </div>
              <button className="btn btn-primary" onClick={saveBusiness} style={{ background: '#25D366', color: 'white', border: 'none', padding: '0.75rem 1.5rem', borderRadius: '8px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>Save Changes</button>
            </div>
          </div>
        )}
      </div>

      {/* Udhaar Modal */}
      {showUdhaarModal && selectedCustomer && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', padding: '2rem', borderRadius: '12px', width: '90%', maxWidth: '500px' }}>
            <h3 style={{ color: '#075E54', marginBottom: '1.5rem' }}>{udhaarAction === 'add' ? 'Add Udhaar' : 'Adjust Balance'} for {selectedCustomer.name}</h3>
            <div className="form-group">
              <label htmlFor="udhaarAmount" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Amount (₹)</label>
              <input id="udhaarAmount" name="udhaarAmount" type="number" placeholder="Amount" value={udhaarAmount} onChange={e => setUdhaarAmount(e.target.value)} style={inputStyle} />
              {udhaarAction === 'adjust' && <small style={{ color: '#666' }}>Positive = add to balance, Negative = reduce balance</small>}
            </div>
            <div className="form-group">
              <label htmlFor="udhaarReason" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Reason (optional)</label>
              <input id="udhaarReason" name="udhaarReason" type="text" placeholder="Reason" value={udhaarReason} onChange={e => setUdhaarReason(e.target.value)} style={inputStyle} />
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
              <button onClick={handleUdhaarSubmit} style={{ flex: 1, background: '#25D366', color: 'white', border: 'none', padding: '0.75rem', borderRadius: '8px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>Submit</button>
              <button onClick={() => setShowUdhaarModal(false)} style={{ flex: 1, background: '#f3f4f6', color: '#4b5563', border: 'none', padding: '0.75rem', borderRadius: '8px', fontSize: '1rem', fontWeight: '600', cursor: 'pointer' }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Transaction History Modal */}
      {showTransactionModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', padding: '2rem', borderRadius: '12px', width: '90%', maxWidth: '700px', maxHeight: '80vh', overflow: 'auto' }}>
            <h3 style={{ color: '#075E54', marginBottom: '1.5rem' }}>Transaction History</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#DCF8C6' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Date</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Amount</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>New Balance</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Reason</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Source</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map(t => (
                  <tr key={t.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                    <td style={{ padding: '0.75rem' }}>{t.created_at}</td>
                    <td style={{ padding: '0.75rem', color: t.amount > 0 ? '#dc2626' : '#10b981' }}>₹{t.amount}</td>
                    <td style={{ padding: '0.75rem' }}>₹{t.new_balance}</td>
                    <td style={{ padding: '0.75rem' }}>{t.reason}</td>
                    <td style={{ padding: '0.75rem' }}>{t.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={() => setShowTransactionModal(false)} style={{ marginTop: '1rem', background: '#075E54', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer' }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;