import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate, useParams } from 'react-router-dom';
import { Calendar, Tag, Package2, DollarSign, UploadCloud, CheckCircle2, Image as ImageIcon, X } from 'lucide-react';

const API_URL = '/api';

export default function EditProductPage({ user }) {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [productName, setProductName] = useState('');
  const [price, setPrice] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [unitId, setUnitId] = useState('');
  const [date, setDate] = useState('');
  
  const [categories, setCategories] = useState([]);
  const [units, setUnits] = useState([]);
  
  const [existingPhotos, setExistingPhotos] = useState([]);
  const [newPhotos, setNewPhotos] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetchCategories();
    fetchUnits();
    fetchProduct();
  }, [id]);

  const fetchCategories = async () => {
    try {
      const res = await axios.get(`${API_URL}/categories`);
      setCategories(res.data);
    } catch (err) {
      console.error('Failed to fetch categories');
    }
  };

  const fetchUnits = async () => {
    try {
      const res = await axios.get(`${API_URL}/units`);
      setUnits(res.data);
    } catch (err) {
      console.error('Failed to fetch units');
    }
  };

  const fetchProduct = async () => {
    try {
      const res = await axios.get(`${API_URL}/products/${id}`);
      const p = res.data;
      setProductName(p.productName || '');
      setPrice(p.productPrice || '');
      setCategoryId(p.productCategoryId || '');
      setUnitId(p.productUnitId || '');
      setDate(p.dateAdded ? p.dateAdded.split('T')[0] : '');
      
      // Setup existing photos
      if (p.productphotourl && p.productphotourl.length > 0) {
        // extract raw paths from urls to send as retained_images
        const rawPaths = p.productPhotoPath ? p.productPhotoPath.split(',').map(s => s.trim()).filter(Boolean) : [];
        const photoObjs = p.productphotourl.map((url, i) => ({
          url,
          rawPath: rawPaths[i]
        }));
        setExistingPhotos(photoObjs);
      }
    } catch (err) {
      setError('Failed to load product details.');
    } finally {
      setLoading(false);
    }
  };

  const handlePhotoSelect = (e) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files).map(file => ({
        file,
        previewUrl: URL.createObjectURL(file)
      }));
      setNewPhotos(prev => [...prev, ...filesArray]);
    }
  };

  const removeExistingPhoto = (index) => {
    setExistingPhotos(prev => prev.filter((_, i) => i !== index));
  };

  const removeNewPhoto = (index) => {
    setNewPhotos(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!productName || !price || !categoryId) {
      setError('Please fill in Product Name, Category, and Price.');
      window.scrollTo(0, 0);
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('productname', productName);
      formData.append('productprice', price);
      formData.append('productcategoryid', categoryId);
      if (unitId) {
        formData.append('productunitid', unitId);
      }
      formData.append('dateadded', date);
      
      const retainedPaths = existingPhotos.map(p => p.rawPath).filter(Boolean);
      formData.append('retained_images', retainedPaths.join(','));

      newPhotos.forEach(p => {
        formData.append('files', p.file);
      });

      await axios.put(`${API_URL}/products/${id}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setSuccess(true);
      setTimeout(() => {
        navigate(-1); // go back to wherever they came from
      }, 1500);
    } catch (err) {
      setError("Couldn't update product. Try again.");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container max-w-3xl">
        <div className="loading-state">Loading product details...</div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="success-state">
        <CheckCircle2 size={64} color="#10b981" />
        <h2>Product Updated Successfully!</h2>
        <p>Saving changes...</p>
      </div>
    );
  }

  return (
    <div className="page-container max-w-3xl">
      <div className="header">
        <div>
          <h2 className="page-title">Edit Product</h2>
          <p className="page-subtitle">Update details and photos for this product</p>
        </div>
      </div>
      
      <div className="glass-panel form-panel">
        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="web-form">
          <div className="form-row">
            <div className="form-group full-width">
              <label>Product Name</label>
              <div className="input-with-icon">
                <Tag className="prefix-icon icon-svg" size={18} />
                <input 
                  type="text" 
                  className="web-input with-prefix" 
                  placeholder="e.g., Apple iPhone 15" 
                  value={productName}
                  onChange={e => setProductName(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="form-row split-row">
            <div className="form-group half-width">
              <label>Category</label>
              <div className="input-with-icon">
                <select 
                  className="web-input select-input"
                  value={categoryId}
                  onChange={e => setCategoryId(e.target.value)}
                >
                  <option value="">Select Category</option>
                  {categories.map(c => (
                    <option key={c.productCategoryId} value={c.productCategoryId}>
                      {c.productCategoryName}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group half-width">
              <label>Selling Unit</label>
              <div className="input-with-icon">
                <Package2 className="prefix-icon icon-svg" size={18} />
                <select 
                  className="web-input select-input with-prefix"
                  value={unitId}
                  onChange={e => setUnitId(e.target.value)}
                >
                  <option value="">Select Unit</option>
                  {units.map(u => (
                    <option key={u.productUnitId} value={u.productUnitId}>
                      {u.productUnitName === 'None' ? 'None (No Unit)' : u.productUnitName}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="form-row split-row">
            <div className="form-group half-width">
              <label>Price</label>
              <div className="input-with-icon">
                <span className="prefix-icon currency-symbol">₹</span>
                <input 
                  type="number" 
                  step="0.01"
                  className="web-input with-prefix" 
                  placeholder="0.00" 
                  value={price}
                  onChange={e => setPrice(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group half-width">
              <label>Date Added</label>
              <div className="input-with-icon">
                <Calendar className="prefix-icon icon-svg" size={18} />
                <input 
                  type="date" 
                  className="web-input with-prefix" 
                  value={date}
                  onChange={e => setDate(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="form-divider"></div>
          
          <h3 className="form-section-title">Product Photos</h3>
          
          <div className="photo-upload-section">
            <div className="photo-grid">
              {existingPhotos.map((photo, index) => (
                <div key={`exist-${index}`} className="photo-preview-card">
                  <img src={photo.url} alt={`Existing ${index}`} />
                  <button type="button" className="remove-photo-btn" onClick={() => removeExistingPhoto(index)}>
                    <X size={14} />
                  </button>
                </div>
              ))}
              {newPhotos.map((photo, index) => (
                <div key={`new-${index}`} className="photo-preview-card">
                  <img src={photo.previewUrl} alt={`New ${index}`} />
                  <div className="new-badge">New</div>
                  <button type="button" className="remove-photo-btn" onClick={() => removeNewPhoto(index)}>
                    <X size={14} />
                  </button>
                </div>
              ))}
              
              <label className="photo-upload-card">
                <input type="file" multiple accept="image/*" onChange={handlePhotoSelect} style={{ display: 'none' }} />
                <UploadCloud size={28} className="upload-icon" />
                <span>Upload Photos</span>
              </label>
            </div>
          </div>

          <div className="form-divider"></div>

          <div className="form-actions">
            <button 
              type="button" 
              className="btn-text"
              onClick={() => navigate(-1)}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-gradient px-8"
              disabled={submitting}
            >
              {submitting ? 'Updating...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
