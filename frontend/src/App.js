// Inside App component, add state and fetch
const [business, setBusiness] = useState({ name: '', address: '', phone: '', gstin: '' });

useEffect(() => {
  fetchBusiness();
}, []);

const fetchBusiness = async () => {
  const res = await fetch(`${API_URL}/api/business`);
  const data = await res.json();
  setBusiness(data);
};

const saveBusiness = async () => {
  await fetch(`${API_URL}/api/business`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(business)
  });
  alert('Business details saved!');
};

// Add new tab in navigation
{ ['dashboard', 'products', 'orders', 'customers', 'settings', 'reports'].map(tab => ...) }

// Settings tab JSX
{
  activeTab === 'settings' && (
    <div style={{ padding: '1rem' }}>
      <h2>🏪 Business Settings</h2>
      <div className="card">
        <div className="form-group">
          <label>Business Name</label>
          <input className="form-input" value={business.name} onChange={e => setBusiness({ ...business, name: e.target.value })} />
        </div>
        <div className="form-group">
          <label>Address</label>
          <textarea className="form-textarea" value={business.address} onChange={e => setBusiness({ ...business, address: e.target.value })} rows="2" />
        </div>
        <div className="form-group">
          <label>WhatsApp Number (Twilio)</label>
          <input className="form-input" value={business.phone} onChange={e => setBusiness({ ...business, phone: e.target.value })} />
        </div>
        <div className="form-group">
          <label>GSTIN</label>
          <input className="form-input" value={business.gstin} onChange={e => setBusiness({ ...business, gstin: e.target.value })} />
        </div>
        <button className="btn btn-primary" onClick={saveBusiness}>Save Changes</button>
      </div>
    </div>
  )
}