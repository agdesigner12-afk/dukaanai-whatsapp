import React, { useState, useEffect } from 'react';

const API_URL = process.env.REACT_APP_API_URL || '';

function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState({
    category: '',
    brand: '',
    name: '',
    description: '',
    is_loose: false,
    variants: [{ weight: '', unit: 'kg', price: '', stock: '' }]
  });

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/products`);
      const json = await res.json();
      setProducts(json);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const data = {
      ...formData,
      variants: formData.variants.map(v => ({
        ...v,
        weight: parseFloat(v.weight),
        price: parseFloat(v.price),
        stock: parseInt(v.stock)
      }))
    };

    try {
      const url = editingProduct 
        ? `${API_URL}/api/products/${editingProduct.id}`
        : `${API_URL}/api/products`;
      
      const method = editingProduct ? 'PUT' : 'POST';
      
      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      
      fetchProducts();
      resetForm();
    } catch (err) {
      console.error('Error:', err);
    }
  };

  const deleteProduct = async (id) => {
    if (!window.confirm('Delete this product?')) return;
    
    try {
      await fetch(`${API_URL}/api/products/${id}`, { method: 'DELETE' });
      fetchProducts();
    } catch (err) {
      console.error('Error:', err);
    }
  };

  const updateStock = async (variantId, newStock) => {
    try {
      await fetch(`${API_URL}/api/variants/${variantId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stock: newStock })
      });
      fetchProducts();
    } catch (err) {
      console.error('Error:', err);
    }
  };

  const resetForm = () => {
    setFormData({
      category: '',
      brand: '',
      name: '',
      description: '',
      is_loose: false,
      variants: [{ weight: '', unit: 'kg', price: '', stock: '' }]
    });
    setEditingProduct(null);
    setShowForm(false);
  };

  const addVariant = () => {
    setFormData({
      ...formData,
      variants: [...formData.variants, { weight: '', unit: 'kg', price: '', stock: '' }]
    });
  };

  const removeVariant = (index) => {
    setFormData({
      ...formData,
      variants: formData.variants.filter((_, i) => i !== index)
    });
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>Products</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ Add Product'}
        </button>
      </div>

      {showForm && (
        <div className="table-container" style={{ marginBottom: 20 }}>
          <h3 style={{ marginBottom: 20 }}>{editingProduct ? 'Edit' : 'Add'} Product</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Category</label>
              <select className="form-control" value={formData.category} onChange={(e) => setFormData({...formData, category: e.target.value})} required>
                <option value="">Select Category</option>
                <option value="tea">Tea (Chai)</option>
                <option value="rice">Rice (Chawal)</option>
                <option value="sugar">Sugar (Chini)</option>
                <option value="oil">Oil (Tel)</option>
                <option value="dal">Dal</option>
                <option value="milk">Milk (Doodh)</option>
                <option value="wheat">Wheat (Gehu/Aata)</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Brand</label>
              <input type="text" className="form-control" value={formData.brand} onChange={(e) => setFormData({...formData, brand: e.target.value})} placeholder="e.g., Tata Tea" />
            </div>
            
            <div className="form-group">
              <label>Product Name</label>
              <input type="text" className="form-control" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} placeholder="e.g., Gold" required />
            </div>

            <div className="form-group">
              <label>
                <input type="checkbox" checked={formData.is_loose} onChange={(e) => setFormData({...formData, is_loose: e.target.checked})} />
                {' '}Loose Item (खुला सामान)
              </label>
            </div>

            <h4 style={{ marginBottom: 15 }}>Variants</h4>
            {formData.variants.map((variant, index) => (
              <div key={index} style={{ display: 'flex', gap: 10, marginBottom: 15, alignItems: 'center' }}>
                <input type="number" step="0.01" className="form-control" style={{ width: 100 }} placeholder="Weight" value={variant.weight} onChange={(e) => {
                  const newVariants = [...formData.variants];
                  newVariants[index].weight = e.target.value;
                  setFormData({...formData, variants: newVariants});
                }} required />
                
                <select className="form-control" style={{ width: 80 }} value={variant.unit} onChange={(e) => {
                  const newVariants = [...formData.variants];
                  newVariants[index].unit = e.target.value;
                  setFormData({...formData, variants: newVariants});
                }}>
                  <option value="kg">kg</option>
                  <option value="g">g</option>
                  <option value="packet">packet</option>
                </select>
                
                <input type="number" step="0.01" className="form-control" style={{ width: 100 }} placeholder="Price (₹)" value={variant.price} onChange={(e) => {
                  const newVariants = [...formData.variants];
                  newVariants[index].price = e.target.value;
                  setFormData({...formData, variants: newVariants});
                }} required />
                
                <input type="number" className="form-control" style={{ width: 100 }} placeholder="Stock" value={variant.stock} onChange={(e) => {
                  const newVariants = [...formData.variants];
                  newVariants[index].stock = e.target.value;
                  setFormData({...formData, variants: newVariants});
                }} required />
                
                {formData.variants.length > 1 && (
                  <button type="button" className="btn btn-danger" onClick={() => removeVariant(index)}>✕</button>
                )}
              </div>
            ))}
            
            <button type="button" className="btn" style={{ background: '#f0f0f0', marginBottom: 20 }} onClick={addVariant}>+ Add Variant</button>
            
            <div>
              <button type="submit" className="btn btn-primary">{editingProduct ? 'Update' : 'Save'} Product</button>
              <button type="button" className="btn" style={{ marginLeft: 10 }} onClick={resetForm}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Category</th>
              <th>Brand</th>
              <th>Variants</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map(product => (
              <tr key={product.id}>
                <td>
                  <strong>{product.full_name}</strong>
                  {product.is_loose && <span style={{ marginLeft: 5, color: '#666', fontSize: 12 }}>(Loose)</span>}
                </td>
                <td>{product.category || '-'}</td>
                <td>{product.brand || '-'}</td>
                <td>
                  {product.variants?.map((v, i) => (
                    <div key={i} style={{ marginBottom: 5 }}>
                      {v.display} | Stock: 
                      <input 
                        type="number" 
                        value={v.stock} 
                        style={{ width: 60, marginLeft: 5, padding: 3 }}
                        onChange={(e) => updateStock(v.id, parseInt(e.target.value))}
                      />
                      {v.stock < 5 && <span style={{ color: 'red', marginLeft: 5 }}>⚠️ Low</span>}
                    </div>
                  ))}
                </td>
                <td>
                  <button className="btn" style={{ marginRight: 5 }} onClick={() => {
                    setEditingProduct(product);
                    setFormData({
                      category: product.category || '',
                      brand: product.brand || '',
                      name: product.name,
                      description: product.description || '',
                      is_loose: product.is_loose,
                      variants: product.variants.map(v => ({
                        weight: v.weight,
                        unit: v.unit,
                        price: v.price,
                        stock: v.stock
                      }))
                    });
                    setShowForm(true);
                  }}>Edit</button>
                  <button className="btn btn-danger" onClick={() => deleteProduct(product.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Products;