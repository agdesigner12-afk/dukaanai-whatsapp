import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const API_URL = process.env.REACT_APP_API_URL || '';

function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('today');

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const res = await fetch(`${API_URL}/api/dashboard`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (!data) return <div>No data</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>Dashboard</h2>
      
      <div className="filter-bar">
        <button className={`filter-btn ${filter === 'today' ? 'active' : ''}`} onClick={() => setFilter('today')}>Today</button>
        <button className={`filter-btn ${filter === 'week' ? 'active' : ''}`} onClick={() => setFilter('week')}>This Week</button>
        <button className={`filter-btn ${filter === 'month' ? 'active' : ''}`} onClick={() => setFilter('month')}>This Month</button>
      </div>

      <div className="dashboard-grid">
        <div className="stat-card">
          <h3>Today's Orders</h3>
          <div className="value">{data.today?.total_orders || 0}</div>
        </div>
        
        <div className="stat-card">
          <h3>Today's Revenue</h3>
          <div className="value">₹{data.today?.revenue?.toLocaleString() || 0}</div>
        </div>
        
        <div className="stat-card">
          <h3>Pending Orders</h3>
          <div className="value">{data.today?.pending || 0}</div>
        </div>
        
        <div className="stat-card">
          <h3>Week Revenue</h3>
          <div className="value">₹{data.week?.revenue?.toLocaleString() || 0}</div>
        </div>
        
        <div className="stat-card">
          <h3>Low Stock Items</h3>
          <div className="value" style={{ color: data.low_stock_count > 0 ? '#dc3545' : '#075e54' }}>
            {data.low_stock_count || 0}
          </div>
        </div>
        
        <div className="stat-card">
          <h3>Total Udhaar</h3>
          <div className="value">₹{data.total_udhaar?.toLocaleString() || 0}</div>
        </div>
        
        <div className="stat-card">
          <h3>Total Customers</h3>
          <div className="value">{data.total_customers || 0}</div>
        </div>
      </div>

      <div className="table-container">
        <h3 style={{ marginBottom: 15 }}>Recent Orders</h3>
        <table>
          <thead>
            <tr>
              <th>Order ID</th>
              <th>Customer</th>
              <th>Items</th>
              <th>Total</th>
              <th>Payment</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.recent_orders?.map(order => (
              <tr key={order.id}>
                <td>#{order.id}</td>
                <td>{order.customer_name}</td>
                <td>{order.items?.length || 0} items</td>
                <td>₹{order.total}</td>
                <td>{order.payment_mode || 'Pending'}</td>
                <td>
                  <span className={`status-badge status-${order.status}`}>
                    {order.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: 15 }}>
          <Link to="/orders" style={{ color: '#075e54', textDecoration: 'none' }}>
            View All Orders →
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;