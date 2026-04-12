import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Orders from './pages/Orders';
import Products from './pages/Products';
import Customers from './pages/Customers';
import Udhaar from './pages/Udhaar';
import Settings from './pages/Settings';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || '';

function App() {
  const [business, setBusiness] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/business`)
      .then(res => res.json())
      .then(data => setBusiness(data))
      .catch(err => console.error('Error:', err));
  }, []);

  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)}>☰</button>
          <h1>{business?.name || 'DukaanAI'}</h1>
          <div className="header-right">
            <span className="shop-status">🟢 Open</span>
          </div>
        </header>

        <div className={`sidebar ${menuOpen ? 'open' : ''}`}>
          <nav>
            <Link to="/" onClick={() => setMenuOpen(false)}>📊 Dashboard</Link>
            <Link to="/orders" onClick={() => setMenuOpen(false)}>📦 Orders</Link>
            <Link to="/products" onClick={() => setMenuOpen(false)}>🛍️ Products</Link>
            <Link to="/customers" onClick={() => setMenuOpen(false)}>👥 Customers</Link>
            <Link to="/udhaar" onClick={() => setMenuOpen(false)}>💰 Udhaar</Link>
            <Link to="/settings" onClick={() => setMenuOpen(false)}>⚙️ Settings</Link>
          </nav>
        </div>

        <main className={`main-content ${menuOpen ? 'shifted' : ''}`}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/products" element={<Products />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/udhaar" element={<Udhaar />} />
            <Route path="/settings" element={<Settings business={business} setBusiness={setBusiness} />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;