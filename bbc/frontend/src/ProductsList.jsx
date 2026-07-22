import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Plus, ChevronLeft, ChevronRight, Search, Filter, SortDesc, Image as ImageIcon, ShoppingBag } from 'lucide-react';

const API_URL = '/api';

export default function ProductsList() {
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
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [prodRes, catRes] = await Promise.all([
        axios.get(`${API_URL}/products`),
        axios.get(`${API_URL}/categories`)
      ]);
      setProducts(prodRes.data);
      setCategories(catRes.data);
    } catch (err) {
      console.error('Failed to fetch data', err);
    } finally {
      setLoading(false);
    }
  };

  const processedProducts = useMemo(() => {
    let result = [...products];

    // Search
    if (search) {
      result = result.filter(p => p.productName?.toLowerCase().includes(search.toLowerCase()));
    }

    // Filter
    if (selectedCategory) {
      result = result.filter(p => p.productCategoryId?.toString() === selectedCategory);
    }

    // Sort
    switch (sortOption) {
      case 'price_high':
        result.sort((a, b) => b.productPrice - a.productPrice);
        break;
      case 'price_low':
        result.sort((a, b) => a.productPrice - b.productPrice);
        break;
      case 'oldest':
        result.sort((a, b) => new Date(a.createdAt || 0) - new Date(b.createdAt || 0));
        break;
      case 'newest':
      default:
        result.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
        break;
    }

    return result;
  }, [products, search, selectedCategory, sortOption]);

  // Reset to page 1 if filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [search, selectedCategory, sortOption]);

  const currentProducts = processedProducts.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  return (
    <div>
      <div className="header" style={{ marginBottom: '16px' }}>
        <div>
          <h2 className="page-title">Product Catalog</h2>
          <p className="page-subtitle">Manage your inventory and pricing</p>
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
            placeholder="Search products..." 
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
        <div className="loading-state">Loading products...</div>
      ) : (
        <>
          <div className="products-grid">
            {currentProducts.map(p => (
              <div key={p.productId} className="glass-panel product-card">
                <div className="product-card-image">
                  <div className="product-category-badge">{p.categoryname || 'No Category'}</div>
                  {p.productphotourl && p.productphotourl.length > 0 ? (
                    <img src={p.productphotourl[0]} alt={p.productName} />
                  ) : (
                    <div className="product-card-fallback"><ImageIcon size={40} /></div>
                  )}
                </div>
                <div className="product-card-content">
                  <div className="product-title">{p.productName}</div>
                  <div className="product-footer">
                    <div className="product-price-section">
                      <span className="product-price">₹{Math.round(p.productPrice)}</span>
                      {p.unitname && <span className="product-unit">/{p.unitname}</span>}
                    </div>
                    <div className="product-action-btn">
                      <ShoppingBag size={16} />
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {processedProducts.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-icon">📦</div>
                <h3>No products found</h3>
                <p>Try adjusting your search or filters.</p>
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
