import React, { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import './App.css';

function App() {
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [dashboard, setDashboard] = useState({});
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Invoice state
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [selectedOrderForInvoice, setSelectedOrderForInvoice] = useState(null);
  const [invoiceType, setInvoiceType] = useState('simple'); // 'simple' or 'tax'
  const [businessInfo, setBusinessInfo] = useState({
    name: 'DukaanAI Demo Shop',
    address: '123 Market Street, New Delhi, India',
    phone: '+91 98765 43210',
    email: 'contact@dukaanai.com',
    gstin: '07AAAAA0000A1Z5'
  });

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

  // Order filter state
  const [orderFilter, setOrderFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

  // Fetch all data
  const fetchAllData = async () => {
    try {
      const [productsRes, ordersRes, customersRes, dashboardRes, analyticsRes] = await Promise.all([
        fetch(`${API_URL}/api/products`),
        fetch(`${API_URL}/api/orders`),
        fetch(`${API_URL}/api/customers`),
        fetch(`${API_URL}/api/dashboard`),
        fetch(`${API_URL}/api/analytics`)
      ]);

      setProducts(await productsRes.json());
      setOrders(await ordersRes.json());
      setCustomers(await customersRes.json());
      setDashboard(await dashboardRes.json());
      setAnalytics(await analyticsRes.json());
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  // CSV Export helpers
  const exportToCSV = (data, filename, headers) => {
    const csvRows = [headers.join(',')];
    data.forEach(row => {
      csvRows.push(headers.map(h => {
        const key = h.toLowerCase().replace(/ /g, '_');
        const val = row[key] !== undefined ? row[key] : '';
        return `"${String(val).replace(/"/g, '""')}"`;
      }).join(','));
    });
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportOrders = () => {
    const data = orders.map(o => ({
      id: o.id, customer: o.customer, customer_phone: o.customer_phone,
      total: o.total, status: o.status, source: o.source,
      date: o.date, time: o.time
    }));
    exportToCSV(data, 'orders.csv', ['ID', 'Customer', 'Customer_Phone', 'Total', 'Status', 'Source', 'Date', 'Time']);
  };

  const exportProducts = () => {
    const data = products.map(p => ({
      id: p.id, name: p.name, price: p.price,
      stock: p.stock, unit: p.unit, total_sold: p.total_sold
    }));
    exportToCSV(data, 'products.csv', ['ID', 'Name', 'Price', 'Stock', 'Unit', 'Total_Sold']);
  };

  const exportCustomers = () => {
    const data = customers.map(c => ({
      id: c.id, name: c.name, phone: c.phone,
      balance: c.balance, total_orders: c.total_orders, total_spent: c.total_spent
    }));
    exportToCSV(data, 'customers.csv', ['ID', 'Name', 'Phone', 'Balance', 'Total_Orders', 'Total_Spent']);
  };

  // Product functions
  const handleAddProduct = async () => {
    try {
      const response = await fetch(`${API_URL}/api/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProduct)
      });

      if (response.ok) {
        fetchAllData();
        setShowProductForm(false);
        setNewProduct({ name: '', price: '', unit: 'kg', stock: '' });
        alert('✅ Product added!');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('❌ Failed to add product');
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
      console.error('Error:', error);
      alert('❌ Failed to update product');
    }
  };

  const handleDeleteProduct = async (id) => {
    if (window.confirm('Delete this product?')) {
      try {
        const response = await fetch(`${API_URL}/api/products/${id}`, {
          method: 'DELETE'
        });
        if (response.ok) {
          fetchAllData();
          alert('✅ Product deleted!');
        }
      } catch (error) {
        console.error('Error:', error);
        alert('❌ Failed to delete product');
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
      console.error('Error:', error);
      alert('❌ Failed to add customer');
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
      console.error('Error:', error);
      alert('❌ Failed to update customer');
    }
  };

  const handleDeleteCustomer = async (id) => {
    if (window.confirm('Delete this customer?')) {
      try {
        const response = await fetch(`${API_URL}/api/customers/${id}`, {
          method: 'DELETE'
        });
        if (response.ok) {
          fetchAllData();
          alert('✅ Customer deleted!');
        }
      } catch (error) {
        console.error('Error:', error);
        alert('❌ Failed to delete customer');
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
      console.error('Error:', error);
      alert('❌ Failed to update order status');
    }
  };

  const handeOpenInvoice = (order) => {
    setSelectedOrderForInvoice(order);
    setShowInvoiceModal(true);
  };

  const handlePrint = () => {
    window.print();
  };

  const renderInvoiceModal = () => {
    if (!showInvoiceModal || !selectedOrderForInvoice) return null;

    const o = selectedOrderForInvoice;
    const isTax = invoiceType === 'tax';
    
    // Calculations (Assuming 18% inclusive for Tax Invoice)
    let subtotal = o.total;
    let cgst = 0;
    let sgst = 0;
    let taxRate = 18;

    if (isTax) {
      subtotal = o.total / (1 + taxRate / 100);
      cgst = (o.total - subtotal) / 2;
      sgst = (o.total - subtotal) / 2;
    }

    return (
      <div className="no-print" style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000,
        padding: '1rem',
        overflowY: 'auto'
      }}>
        <div style={{
          background: 'white',
          width: '100%',
          maxWidth: '800px',
          borderRadius: '12px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Modal Header */}
          <div style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <h3 style={{ margin: 0 }}>Generate Invoice</h3>
            <button 
              onClick={() => setShowInvoiceModal(false)}
              style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
            >
              ×
            </button>
          </div>

          {/* Modal Options */}
          <div style={{ padding: '1rem 1.5rem', background: '#f9fafb', display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ fontWeight: '600' }}>Type:</span>
            <button 
              onClick={() => setInvoiceType('simple')}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: 'none',
                background: invoiceType === 'simple' ? '#075E54' : '#e5e7eb',
                color: invoiceType === 'simple' ? 'white' : '#4b5563',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              Simple Bill
            </button>
            <button 
              onClick={() => setInvoiceType('tax')}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                border: 'none',
                background: invoiceType === 'tax' ? '#075E54' : '#e5e7eb',
                color: invoiceType === 'tax' ? 'white' : '#4b5563',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              Tax Invoice (GST)
            </button>
          </div>

          {/* Invoice Body (The Printable Part) */}
          <div id="invoice-print-area" style={{
            padding: '2rem',
            overflowY: 'auto',
            flex: 1,
            fontFamily: 'Arial, sans-serif'
          }}>
            {/* Business Details */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
              <div>
                <h2 style={{ margin: '0 0 0.5rem 0', color: '#075E54' }}>{businessInfo.name}</h2>
                <p style={{ margin: '0', fontSize: '0.9rem', color: '#6b7280' }}>{businessInfo.address}</p>
                <p style={{ margin: '0', fontSize: '0.9rem', color: '#6b7280' }}>Phone: {businessInfo.phone}</p>
                {isTax && businessInfo.gstin && (
                  <p style={{ margin: '0.5rem 0 0 0', fontWeight: 'bold' }}>GSTIN: {businessInfo.gstin}</p>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <h1 style={{ margin: '0', fontSize: '1.5rem', opacity: 0.5 }}>{isTax ? 'TAX INVOICE' : 'BILL'}</h1>
                <p style={{ margin: '0.5rem 0 0 0' }}>Invoice #: INV-{o.id}</p>
                <p style={{ margin: '0' }}>Date: {o.date}</p>
              </div>
            </div>

            {/* Customer Details */}
            <div style={{ marginBottom: '2rem', padding: '1rem', background: '#f9fafb', borderRadius: '8px' }}>
              <h4 style={{ margin: '0 0 0.5rem 0', textTransform: 'uppercase', fontSize: '0.8rem', color: '#6b7280' }}>Bill To:</h4>
              <p style={{ margin: '0', fontWeight: 'bold' }}>{o.customer}</p>
              <p style={{ margin: '0' }}>Phone: {o.customer_phone}</p>
              {isTax && (
                <div style={{ marginTop: '0.5rem' }}>
                  <label style={{ fontSize: '0.8rem', display: 'block' }}>Customer GSTIN (Optional):</label>
                  <input 
                    type="text"
                    placeholder="Enter GSTIN"
                    className="no-print"
                    value={o.customer_gstin || ''}
                    onChange={(e) => {
                      // Update local state if needed, but for now just show
                    }}
                    style={{
                      border: '1px solid #e5e7eb',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      marginTop: '4px',
                      width: '200px'
                    }}
                  />
                  <span className="print-only" style={{ display: 'none' }}>{o.customer_gstin}</span>
                </div>
              )}
            </div>

            {/* Table */}
            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '2rem' }}>
              <thead>
                <tr style={{ background: '#075E54', color: 'white' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Item Description</th>
                  <th style={{ padding: '0.75rem', textAlign: 'center' }}>Qty</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Rate</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Amount</th>
                </tr>
              </thead>
              <tbody>
                {/* For now, using the total since detail items might not be available */}
                <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '1rem' }}>Order from {o.source}</td>
                  <td style={{ padding: '1rem', textAlign: 'center' }}>1</td>
                  <td style={{ padding: '1rem', textAlign: 'right' }}>₹{subtotal.toFixed(2)}</td>
                  <td style={{ padding: '1rem', textAlign: 'right' }}>₹{subtotal.toFixed(2)}</td>
                </tr>
              </tbody>
            </table>

            {/* Totals */}
            <div style={{ marginLeft: 'auto', width: '300px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span>Subtotal:</span>
                <span>₹{subtotal.toFixed(2)}</span>
              </div>
              
              {isTax && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', color: '#6b7280' }}>
                    <span>CGST (9%):</span>
                    <span>₹{cgst.toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', color: '#6b7280' }}>
                    <span>SGST (9%):</span>
                    <span>₹{sgst.toFixed(2)}</span>
                  </div>
                </>
              )}
              
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem', padding: '1rem 0', borderTop: '2px solid #075E54', fontWeight: 'bold', fontSize: '1.2rem' }}>
                <span>Total:</span>
                <span style={{ color: '#075E54' }}>₹{o.total.toFixed(2)}</span>
              </div>
            </div>

            <div style={{ marginTop: '4rem', textAlign: 'center', fontSize: '0.9rem', color: '#9ca3af' }}>
              <p>Thank you for your business! 🙏</p>
              <p style={{ margin: '0' }}>Generated via DukaanAI Dashboard</p>
            </div>
          </div>

          {/* Modal Footer */}
          <div className="no-print" style={{
            padding: '1.5rem',
            borderTop: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '1rem'
          }}>
            <button
              onClick={() => setShowInvoiceModal(false)}
              style={{
                padding: '0.75rem 1.5rem',
                borderRadius: '8px',
                border: '1px solid #e5e7eb',
                background: 'white',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              onClick={handlePrint}
              style={{
                padding: '0.75rem 1.5rem',
                borderRadius: '8px',
                border: 'none',
                background: '#25D366',
                color: 'white',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              Print / Save PDF 🖨️
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Filter orders
  const filteredOrders = orders.filter(order => {
    // Status filter
    if (orderFilter !== 'all' && order.status !== orderFilter) return false;

    // Search filter
    if (searchTerm && !order.customer?.toLowerCase().includes(searchTerm.toLowerCase())) return false;

    return true;
  });

  const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    marginBottom: '1rem',
    border: '2px solid #e5e7eb',
    borderRadius: '8px',
    fontSize: '1rem',
    outline: 'none',
    transition: 'border-color 0.3s'
  };

  if (loading) return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      background: '#ECE5DD'
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📱</div>
        <h2 style={{ color: '#075E54' }}>Loading DukaanDash...</h2>
      </div>
    </div>
  );

  return (
    <div className="App">
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #075E54 0%, #128C7E 100%)',
        color: 'white',
        padding: '2rem 1rem',
        textAlign: 'center'
      }}>
        <h1 style={{ fontSize: '2.5rem', margin: '0 0 0.5rem 0' }}>📱 DukaanDash</h1>
        <p style={{ fontSize: '1.1rem', opacity: 0.9 }}>
          Orders: {dashboard.today?.orders || 0} today | Revenue: ₹{dashboard.today?.revenue || 0}
        </p>
      </div>

      {/* Low Stock Alert Banner */}
      {dashboard.lowStock > 0 && (
        <div style={{
          background: 'linear-gradient(90deg, #dc2626, #ef4444)',
          color: 'white',
          padding: '0.75rem 1.5rem',
          textAlign: 'center',
          fontWeight: '600',
          fontSize: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.75rem',
          animation: 'pulse 2s infinite'
        }}>
          <span style={{ fontSize: '1.3rem' }}>⚠️</span>
          <span>LOW STOCK ALERT: {dashboard.lowStock} product{dashboard.lowStock > 1 ? 's' : ''} running low!</span>
          <button
            onClick={() => setActiveTab('products')}
            style={{
              background: 'white',
              color: '#dc2626',
              border: 'none',
              padding: '0.3rem 1rem',
              borderRadius: '20px',
              fontWeight: '700',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            View Products →
          </button>
        </div>
      )}

      {/* Navigation */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: '1rem',
        margin: '2rem 0',
        borderBottom: '2px solid #e5e7eb',
        paddingBottom: '1rem',
        flexWrap: 'wrap'
      }}>
        {['dashboard', 'products', 'orders', 'customers', 'reports'].map(tab => (
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
              transition: 'all 0.3s',
              textTransform: 'capitalize'
            }}
          >
            {tab === 'dashboard' ? '🏠 Dashboard' :
              tab === 'products' ? '📦 Products' :
                tab === 'orders' ? '📋 Orders' :
                  tab === 'customers' ? '👥 Customers' : '📊 Analytics'}
          </button>
        ))}
      </div>

      {/* Dashboard Tab */}
      {activeTab === 'dashboard' && (
        <div style={{ padding: '0 1rem' }}>
          <h2 style={{ color: '#075E54', marginBottom: '1.5rem' }}>Dashboard Overview</h2>

          {/* Stats Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1.5rem',
            marginBottom: '2rem'
          }}>
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
              <h3 style={{ color: '#6b7280', fontSize: '0.9rem' }}>Customers</h3>
              <p style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#10b981' }}>{dashboard.customers?.total || 0}</p>
              <p style={{ color: '#6b7280' }}>New: {dashboard.customers?.new || 0}</p>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <button
              onClick={() => setActiveTab('products')}
              style={{
                background: '#25D366',
                color: 'white',
                border: 'none',
                padding: '1rem',
                borderRadius: '12px',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'transform 0.2s'
              }}
              onMouseEnter={(e) => e.target.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
            >
              📦 Manage Products
            </button>
            <button
              onClick={() => setActiveTab('orders')}
              style={{
                background: '#075E54',
                color: 'white',
                border: 'none',
                padding: '1rem',
                borderRadius: '12px',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'transform 0.2s'
              }}
              onMouseEnter={(e) => e.target.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
            >
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
            <button
              onClick={() => setShowProductForm(true)}
              style={{
                background: '#25D366',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '30px',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              + Add Product
            </button>
          </div>
          
          {/* Product Form Modal */}
          {(showProductForm || editingProduct) && (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }}>
              <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '12px',
                width: '90%',
                maxWidth: '500px'
              }}>
                <h3 style={{ color: '#075E54', marginBottom: '1.5rem' }}>
                  {editingProduct ? 'Edit Product' : 'Add New Product'}
                </h3>
                
                <input
                  type="text"
                  placeholder="Product Name"
                  value={editingProduct ? editingProduct.name : newProduct.name}
                  onChange={(e) => editingProduct ? 
                    setEditingProduct({...editingProduct, name: e.target.value}) :
                    setNewProduct({...newProduct, name: e.target.value})}
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '1rem', border: '2px solid #e5e7eb', borderRadius: '8px' }}
                />
                
                <input
                  type="number"
                  placeholder="Price (₹)"
                  value={editingProduct ? editingProduct.price : newProduct.price}
                  onChange={(e) => editingProduct ? 
                    setEditingProduct({...editingProduct, price: e.target.value}) :
                    setNewProduct({...newProduct, price: e.target.value})}
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '1rem', border: '2px solid #e5e7eb', borderRadius: '8px' }}
                />
                
                <select
                  value={editingProduct ? editingProduct.unit : newProduct.unit}
                  onChange={(e) => editingProduct ? 
                    setEditingProduct({...editingProduct, unit: e.target.value}) :
                    setNewProduct({...newProduct, unit: e.target.value})}
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '1rem', border: '2px solid #e5e7eb', borderRadius: '8px', fontSize: '1rem' }}
                >
                  <option value="kg">kg (किलो)</option>
                  <option value="piece">piece (पीस)</option>
                  <option value="dozen">dozen (दर्जन)</option>
                  <option value="litre">litre (लीटर)</option>
                </select>
                
                <input
                  type="number"
                  placeholder="Stock Quantity"
                  value={editingProduct ? editingProduct.stock : newProduct.stock}
                  onChange={(e) => editingProduct ? 
                    setEditingProduct({...editingProduct, stock: e.target.value}) :
                    setNewProduct({...newProduct, stock: e.target.value})}
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '1rem', border: '2px solid #e5e7eb', borderRadius: '8px' }}
                />
                
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                  <button
                    onClick={editingProduct ? handleUpdateProduct : handleAddProduct}
                    style={{
                      flex: 1,
                      background: '#25D366',
                      color: 'white',
                      border: 'none',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      fontSize: '1rem',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    {editingProduct ? 'Update' : 'Add'} Product
                  </button>
                  <button
                    onClick={() => {
                      setShowProductForm(false);
                      setEditingProduct(null);
                    }}
                    style={{
                      flex: 1,
                      background: '#f3f4f6',
                      color: '#4b5563',
                      border: 'none',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      fontSize: '1rem',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Products Table */}
          <div style={{
            background: 'white',
            borderRadius: '12px',
            overflow: 'hidden',
            boxShadow: '0 4px 6px rgba(0,0,0,0.05)'
          }}>
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
                    <td style={{
                      padding: '1rem',
                      color: p.stock < 10 ? '#ef4444' : '#10b981',
                      fontWeight: '600'
                    }}>
                      {p.stock}
                    </td>
                    <td style={{ padding: '1rem' }}>{p.unit}</td>
                    <td style={{ padding: '1rem' }}>{p.total_sold || 0}</td>
                    <td style={{ padding: '1rem' }}>
                      <button
                        onClick={() => setEditingProduct(p)}
                        style={{
                          background: '#3b82f6',
                          color: 'white',
                          border: 'none',
                          padding: '4px 12px',
                          borderRadius: '4px',
                          marginRight: '8px',
                          cursor: 'pointer'
                        }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteProduct(p.id)}
                        style={{
                          background: '#ef4444',
                          color: 'white',
                          border: 'none',
                          padding: '4px 12px',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
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

          {/* Filters */}
          <div style={{
            display: 'flex',
            gap: '1rem',
            marginBottom: '1.5rem',
            flexWrap: 'wrap'
          }}>
            <input
              type="text"
              placeholder="Search customer..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                flex: 1,
                padding: '0.5rem',
                border: '2px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '1rem'
              }}
            />
            <select
              value={orderFilter}
              onChange={(e) => setOrderFilter(e.target.value)}
              style={{
                padding: '0.5rem',
                border: '2px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '1rem'
              }}
            >
              <option value="all">All Orders</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          {/* Orders Table */}
          <div style={{
            background: 'white',
            borderRadius: '12px',
            overflow: 'auto',
            boxShadow: '0 4px 6px rgba(0,0,0,0.05)'
          }}>
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
                      <select
                        value={o.status}
                        onChange={(e) => handleUpdateOrderStatus(o.id, e.target.value)}
                        style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          border: '1px solid #25D366',
                          background: o.status === 'pending' ? '#fef3c7' :
                            o.status === 'completed' ? '#DCF8C6' : '#fee2e2'
                        }}
                      >
                        <option value="pending">Pending</option>
                        <option value="processing">Processing</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </td>
                    <td style={{ padding: '1rem', textTransform: 'capitalize' }}>{o.source}</td>
                    <td style={{ padding: '1rem' }}>{o.date} {o.time}</td>
                    <td style={{ padding: '1rem' }}>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          onClick={() => window.open(`https://wa.me/${o.customer_phone}`, '_blank')}
                          style={{
                            background: '#25D366',
                            color: 'white',
                            border: 'none',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.8rem'
                          }}
                        >
                          WhatsApp
                        </button>
                        <button
                          onClick={() => handeOpenInvoice(o)}
                          style={{
                            background: '#075E54',
                            color: 'white',
                            border: 'none',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.8rem'
                          }}
                        >
                          Bill 📄
                        </button>
                      </div>
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
            <button 
              onClick={() => setShowCustomerForm(true)}
              style={{
                background: '#25D366',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '30px',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              + Add Customer
            </button>
          </div>
          
          {/* Customer Form Modal */}
          {(showCustomerForm || editingCustomer) && (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }}>
              <div style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '12px',
                width: '90%',
                maxWidth: '500px'
              }}>
                <h3 style={{ color: '#075E54', marginBottom: '1.5rem' }}>
                  {editingCustomer ? 'Edit Customer' : 'Add Customer'}
                </h3>
                
                <input
                  type="text"
                  placeholder="Customer Name"
                  value={editingCustomer ? editingCustomer.name : newCustomer.name}
                  onChange={(e) => editingCustomer ? 
                    setEditingCustomer({...editingCustomer, name: e.target.value}) :
                    setNewCustomer({...newCustomer, name: e.target.value})}
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '1rem', border: '2px solid #e5e7eb', borderRadius: '8px' }}
                />
                
                <input
                  type="text"
                  placeholder="Phone Number"
                  value={editingCustomer ? editingCustomer.phone : newCustomer.phone}
                  onChange={(e) => editingCustomer ? 
                    setEditingCustomer({...editingCustomer, phone: e.target.value}) :
                    setNewCustomer({...newCustomer, phone: e.target.value})}
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '1rem', border: '2px solid #e5e7eb', borderRadius: '8px' }}
                />
                
                <input
                  type="number"
                  placeholder="Balance (₹)"
                  value={editingCustomer ? editingCustomer.balance : newCustomer.balance}
                  onChange={(e) => editingCustomer ? 
                    setEditingCustomer({...editingCustomer, balance: e.target.value}) :
                    setNewCustomer({...newCustomer, balance: e.target.value})}
                  style={{ width: '100%', padding: '0.75rem', marginBottom: '1rem', border: '2px solid #e5e7eb', borderRadius: '8px' }}
                />
                
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                  <button
                    onClick={editingCustomer ? handleUpdateCustomer : handleAddCustomer}
                    style={{
                      flex: 1,
                      background: '#25D366',
                      color: 'white',
                      border: 'none',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      fontSize: '1rem',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    {editingCustomer ? 'Update' : 'Add'} Customer
                  </button>
                  <button
                    onClick={() => {
                      setShowCustomerForm(false);
                      setEditingCustomer(null);
                    }}
                    style={{
                      flex: 1,
                      background: '#f3f4f6',
                      color: '#4b5563',
                      border: 'none',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      fontSize: '1rem',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Customers Table */}
          <div style={{ 
            background: 'white', 
            borderRadius: '12px', 
            overflow: 'auto',
            boxShadow: '0 4px 6px rgba(0,0,0,0.05)'
          }}>
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
                    <td style={{ 
                      padding: '1rem', 
                      fontWeight: '600',
                      color: c.balance > 0 ? '#ef4444' : '#10b981'
                    }}>
                      ₹{c.balance}
                    </td>
                    <td style={{ padding: '1rem' }}>{c.total_orders || 0}</td>
                    <td style={{ padding: '1rem' }}>₹{c.total_spent || 0}</td>
                    <td style={{ padding: '1rem' }}>{c.last_order_date || 'N/A'}</td>
                    <td style={{ padding: '1rem' }}>
                      <button
                        onClick={() => setEditingCustomer(c)}
                        style={{
                          background: '#3b82f6',
                          color: 'white',
                          border: 'none',
                          padding: '4px 12px',
                          borderRadius: '4px',
                          marginRight: '8px',
                          cursor: 'pointer'
                        }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteCustomer(c.id)}
                        style={{
                          background: '#ef4444',
                          color: 'white',
                          border: 'none',
                          padding: '4px 12px',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'reports' && analytics && (
        <div style={{ padding: '0 1rem' }}>
          <h2 style={{ color: '#075E54', marginBottom: '1.5rem' }}>📊 Advanced Analytics</h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem', marginBottom: '2rem' }}>
            
            {/* Revenue Trends */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <h3 style={{ color: '#4b5563', marginBottom: '1rem' }}>Revenue Trends (Last 7 Days)</h3>
              <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                  <LineChart data={analytics.revenueTrends}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value) => `₹${value}`} />
                    <Line type="monotone" dataKey="revenue" stroke="#25D366" strokeWidth={3} activeDot={{ r: 8 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Customer Growth */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <h3 style={{ color: '#4b5563', marginBottom: '1rem' }}>Cumulative Customer Growth</h3>
              <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                  <AreaChart data={analytics.customerGrowth}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Area type="monotone" dataKey="customers" stroke="#3b82f6" fill="#bfdbfe" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Top Selling Products */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <h3 style={{ color: '#4b5563', marginBottom: '1rem' }}>Top Products by Volume</h3>
              <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                  <BarChart data={analytics.topProducts} layout="vertical" margin={{ left: 40, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" />
                    <YAxis dataKey="name" type="category" width={100} />
                    <Tooltip />
                    <Bar dataKey="sold" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Order Completion Rate */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
              <h3 style={{ color: '#4b5563', marginBottom: '1rem' }}>Order Status Breakdown</h3>
              <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={analytics.orderCompletion.filter(d => d.value > 0)}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {analytics.orderCompletion.map((entry, index) => {
                        const colors = {
                          'Completed': '#10b981',
                          'Pending': '#f59e0b',
                          'Cancelled': '#ef4444'
                        };
                        return <Cell key={`cell-${index}`} fill={colors[entry.name] || '#8884d8'} />;
                      })}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>

          {/* CSV Export Section */}
          <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '12px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
            marginTop: '1rem'
          }}>
            <h3 style={{ color: '#4b5563', marginBottom: '1rem' }}>📥 Export Data as CSV</h3>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <button
                onClick={exportOrders}
                style={{
                  background: '#075E54',
                  color: 'white',
                  border: 'none',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                📋 Export Orders
              </button>
              <button
                onClick={exportProducts}
                style={{
                  background: '#1d4ed8',
                  color: 'white',
                  border: 'none',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                📦 Export Products
              </button>
              <button
                onClick={exportCustomers}
                style={{
                  background: '#7c3aed',
                  color: 'white',
                  border: 'none',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                👥 Export Customers
              </button>
            </div>
          </div>
        </div>
      )}
      {renderInvoiceModal()}
    </div>
  );
}

export default App;