import React, { useState, useEffect } from 'react';

const API_URL = process.env.REACT_APP_API_URL || '';

function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [days, setDays] = useState(null);

  useEffect(() => {
    fetchOrders();
  }, [days]);

  const fetchOrders = async () => {
    try {
      let url = `${API_URL}/api/orders`;
      if (days) url += `?days=${days}`;
      
      const res = await fetch(url);
      const json = await res.json();
      setOrders(json);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (orderId, newStatus) => {
    try {
      await fetch(`${API_URL}/api/orders/${orderId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      fetchOrders();
    } catch (err) {
      console.error('Error:', err);
    }
  };

  const filteredOrders = filter === 'all' 
    ? orders 
    : orders.filter(o => o.status === filter);

  const getStatusColor = (status) => {
    const colors = {
      pending: '#fff3cd',
      confirmed: '#cce5ff',
      payment_received: '#d4edda',
      delivered: '#d1e7dd',
      cancelled: '#f8d7da'
    };
    return colors[status] || '#f0f0f0';
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>Orders</h2>
      
      <div className="filter-bar">
        <button className={`filter-btn ${days === null ? 'active' : ''}`} onClick={() => setDays(null)}>All Time</button>
        <button className={`filter-btn ${days === 1 ? 'active' : ''}`} onClick={() => setDays(1)}>Today</button>
        <button className={`filter-btn ${days === 7 ? 'active' : ''}`} onClick={() => setDays(7)}>Week</button>
        <button className={`filter-btn ${days === 30 ? 'active' : ''}`} onClick={() => setDays(30)}>Month</button>
      </div>

      <div className="filter-bar">
        <button className={`filter-btn ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
        <button className={`filter-btn ${filter === 'pending' ? 'active' : ''}`} onClick={() => setFilter('pending')}>Pending</button>
        <button className={`filter-btn ${filter === 'confirmed' ? 'active' : ''}`} onClick={() => setFilter('confirmed')}>Confirmed</button>
        <button className={`filter-btn ${filter === 'payment_received' ? 'active' : ''}`} onClick={() => setFilter('payment_received')}>Paid</button>
        <button className={`filter-btn ${filter === 'delivered' ? 'active' : ''}`} onClick={() => setFilter('delivered')}>Delivered</button>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Customer</th>
              <th>Items</th>
              <th>Total</th>
              <th>Payment</th>
              <th>Status</th>
              <th>Time</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map(order => (
              <tr key={order.id}>
                <td>#{order.id}</td>
                <td>
                  {order.customer_name}
                  <br />
                  <small>{order.customer_phone}</small>
                </td>
                <td>
                  {order.items?.map((item, i) => (
                    <div key={i}>{item.quantity} x {item.product_name}</div>
                  ))}
                </td>
                <td>₹{order.total}</td>
                <td>{order.payment_mode || '-'}</td>
                <td>
                  <span className={`status-badge status-${order.status}`}>
                    {order.status}
                  </span>
                </td>
                <td>{new Date(order.created_at).toLocaleTimeString()}</td>
                <td>
                  {order.status === 'pending' && (
                    <button className="btn btn-success" style={{ marginRight: 5 }} onClick={() => updateStatus(order.id, 'confirmed')}>
                      Accept
                    </button>
                  )}
                  {(order.status === 'confirmed' || order.status === 'payment_received') && (
                    <button className="btn btn-primary" style={{ marginRight: 5 }} onClick={() => updateStatus(order.id, 'delivered')}>
                      Deliver
                    </button>
                  )}
                  {order.status !== 'delivered' && order.status !== 'cancelled' && (
                    <button className="btn btn-danger" onClick={() => updateStatus(order.id, 'cancelled')}>
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Orders;