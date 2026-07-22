import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Plus, Edit2, Trash2, ChevronLeft, ChevronRight, Search, Filter, SortDesc, Image as ImageIcon, ShoppingBag } from 'lucide-react';

const API_URL = '/api';

export default function MyProductsPage({ user }) {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filter/Sort State
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [sortOption, setSortOption] = useState('newest'); // newest, oldest, price_high, price_low

  const [currentPage, setCurrentPage] = useState(1);
  const navigate = useNavigate();
  
  const ITEMS_PER_PAGE = 12;

  useEffect(() => {
    if (user?.userid) {
      fetchMyProducts();
      fetchCategories();
    }
  }, [user]);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_URL}/categories`);
      setCategories(response.data);
    } catch (err) {
      console.error('Failed to fetch categories', err);
    }
  };

  const fetchMyProducts = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/admin/user/${user.userid}/products`);
      setProducts(response.data.products || []);
    } catch (err) {
      console.error('Failed to fetch user products', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (productId) => {
    if (!window.confirm('Are you sure you want to delete this product?')) return;
    try {
      await axios.delete(`${API_URL}/products/${productId}`);
      setProducts(products.filter(p => p.productid !== productId));
    } catch (err) {
      console.error('Failed to delete product', err);
      alert('Failed to delete product.');
    }
  };

  const processedProducts = useMemo(() => {
    let result = [...products];

    // Search
    if (search) {
      result = result.filter(p => p.productname?.toLowerCase().includes(search.toLowerCase()));
    }

    // Filter
    if (selectedCategory) {
      // In Admin products endpoint, category name is returned.
      // Wait, Admin endpoint returns category name, not ID. 
      // Let's match on name instead of ID if needed, but it's tricky if categories list uses IDs.
      // Actually Admin endpoint doesn't return category ID. I will filter by category name.
      const cat = categories.find(c => c.productCategoryId?.toString() === selectedCategory);
      if (cat) {
        result = result.filter(p => p.category === cat.productCategoryName);
      }
    }

    // Sort
    switch (sortOption) {
      case 'price_high':
        result.sort((a, b) => Number(b.productprice) - Number(a.productprice));
        break;
      case 'price_low':
        result.sort((a, b) => Number(a.productprice) - Number(b.productprice));
        break;
      case 'oldest':
        result.sort((a, b) => new Date(a.createdat || 0) - new Date(b.createdat || 0));
        break;
      case 'newest':
      default:
        result.sort((a, b) => new Date(b.createdat || 0) - new Date(a.createdat || 0));
        break;
    }

    return result;
  }, [products, search, selectedCategory, sortOption, categories]);

  // Reset to page 1 if filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [search, selectedCategory, sortOption]);

  const currentProducts = processedProducts.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  return (
    <div>
      <div className="header" style={{ marginBottom: '16px' }}>
        <div>
          <h2 className="page-title">My Products</h2>
          <p className="page-subtitle">Manage products you have added</p>
        </div>
        <button className="btn-gradient px-6" onClick={() => navigate('/add')}>
          <Plus size={18} style={{ marginRight: 8 }} />
          Add Product
        </button>
      </div>

      <div className="filters-toolbar">
        <div className="search-box">
          <Search size={18} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search my products..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <div className="filter-dropdowns">
          <div className="select-with-icon">
            <Filter size={16} className="select-icon" />
            <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)}>
              <option value="">All Categories</option>
              {categories.map(c => (
                <option key={c.productCategoryId} value={c.productCategoryId}>{c.productCategoryName}</option>
              ))}
            </select>
          </div>
          
          <div className="select-with-icon">
            <SortDesc size={16} className="select-icon" />
            <select value={sortOption} onChange={(e) => setSortOption(e.target.value)}>
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="price_high">Price: High to Low</option>
              <option value="price_low">Price: Low to High</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Loading your products...</div>
      ) : (
        <>
          <div className="products-grid">
            {currentProducts.map(p => (
              <div key={p.productid} className="glass-panel product-card relative group">
                <div className="product-card-image">
                  <div className="product-category-badge">{p.category || 'No Category'}</div>
                  {p.productphotourl && p.productphotourl.length > 0 ? (
                    <img src={p.productphotourl[0]} alt={p.productname} />
                  ) : (
                    <div className="product-card-fallback"><ImageIcon size={40} /></div>
                  )}
                </div>
                <div className="product-card-content">
                  <div className="product-title">{p.productname}</div>
                  <div className="product-footer">
                    <div className="product-price-section">
                      <span className="product-price">₹{Math.round(p.productprice)}</span>
                      {p.unit && <span className="product-unit">/{p.unit}</span>}
                    </div>
                    <div className="product-action-btn">
                      <ShoppingBag size={16} />
                    </div>
                  </div>
                  <div style={{ marginTop: 'auto', display: 'flex', gap: '8px', paddingTop: '10px' }}>
                    <button className="btn-outline" style={{ padding: '6px 12px', fontSize: '13px', flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px', minHeight: '32px', height: '32px', borderRadius: '8px' }} onClick={() => navigate(`/edit/${p.productid}`)}>
                      <Edit2 size={14} /> Edit
                    </button>
                    <button className="btn-outline" style={{ padding: '6px 12px', fontSize: '13px', flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px', color: '#ef4444', borderColor: '#fee2e2', background: '#fef2f2', minHeight: '32px', height: '32px', borderRadius: '8px' }} onClick={() => handleDelete(p.productid)}>
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {processedProducts.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-icon">📦</div>
                <h3>No products found</h3>
                <p>You haven't added any products yet, or none match your filters.</p>
                <button className="btn-outline mt-4" onClick={() => { setSearch(''); setSelectedCategory(''); }}>
                  Clear Filters
                </button>
              </div>
            )}
          </div>
          
          {processedProducts.length > ITEMS_PER_PAGE && (
            <div className="pagination-minimal">
              <button 
                className="page-icon-btn" 
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              >
                <ChevronLeft size={20} />
              </button>
              <span className="page-text">
                {currentPage} / {Math.ceil(processedProducts.length / ITEMS_PER_PAGE)}
              </span>
              <button 
                className="page-icon-btn" 
                disabled={currentPage === Math.ceil(processedProducts.length / ITEMS_PER_PAGE)}
                onClick={() => setCurrentPage(p => Math.min(Math.ceil(processedProducts.length / ITEMS_PER_PAGE), p + 1))}
              >
                <ChevronRight size={20} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
