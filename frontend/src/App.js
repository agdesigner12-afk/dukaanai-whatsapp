import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [dashboard, setDashboard] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');

  // Business settings state
  const [business, setBusiness] = useState({ name: '', address: '', phone: '', gstin: '' });

  const API_URL = process.env.REACT_APP_API_URL || 'https://dukaanai-whatsapp-1.onrender.com';

  useEffect(() => {
    fetchAllData();
    fetchBusiness();
  }, []);

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

  const fetchBusiness = async () => {
    try {
      const res = await fetch(`${API_URL}/api/business`);
      const data = await res.json();
      setBusiness(data);
    } catch (error) {
      console.error('Error fetching business:', error);
    }
  };

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

  // Helper for product actions (add/edit/delete) – keep your existing code
  // ... (I assume you already have product/customer/order handlers)
  // For brevity, I'll only show the Settings tab addition.
  // But in a real file, you would keep all your existing CRUD logic.

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="App">
      <div className="header">
        <h1>📱 DukaanDash</h1>
        <p>Orders: {dashboard.today?.orders || 0} today | Revenue: ₹{dashboard.today?.revenue || 0}</p>
      </div>

      <div className="nav-tabs">
        {['dashboard', 'products', 'orders', 'customers', 'settings'].map(tab => (
          <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
            {tab === 'dashboard' ? '🏠 Dashboard' :
              tab === 'products' ? '📦 Products' :
                tab === 'orders' ? '📋 Orders' :
                  tab === 'customers' ? '👥 Customers' : '⚙️ Settings'}
          </button>
        ))}
      </div>

      <div className="main-content">
        {activeTab === 'dashboard' && (
          <div>
            {/* Your existing dashboard UI */}
            <div className="stats-grid">
              <div className="stat-card">Today's Orders: {dashboard.today?.orders || 0}</div>
              <div className="stat-card">Pending Orders: {dashboard.pending || 0}</div>
              <div className="stat-card">Low Stock: {dashboard.lowStock || 0}</div>
              <div className="stat-card">Total Balance: ₹{dashboard.totalBalance || 0}</div>
            </div>
          </div>
        )}

        {activeTab === 'products' && (
          <div>
            {/* Your existing products table */}
            <h2>Products</h2>
            <table>...</table>
          </div>
        )}

        {activeTab === 'orders' && (
          <div>
            {/* Your existing orders table */}
            <h2>Orders</h2>
            <table>...</table>
          </div>
        )}

        {activeTab === 'customers' && (
          <div>
            {/* Your existing customers table */}
            <h2>Customers</h2>
            <table>...</table>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="settings-panel">
            <h2>🏪 Business Settings</h2>
            <div className="form-group">
              <label>Business Name</label>
              <input value={business.name} onChange={e => setBusiness({ ...business, name: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Address</label>
              <textarea value={business.address} onChange={e => setBusiness({ ...business, address: e.target.value })} rows="2" />
            </div>
            <div className="form-group">
              <label>WhatsApp Number (Twilio)</label>
              <input value={business.phone} onChange={e => setBusiness({ ...business, phone: e.target.value })} />
            </div>
            <div className="form-group">
              <label>GSTIN</label>
              <input value={business.gstin} onChange={e => setBusiness({ ...business, gstin: e.target.value })} />
            </div>
            <button className="btn-save" onClick={saveBusiness}>Save Changes</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;