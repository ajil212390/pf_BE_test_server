import { useState, useEffect } from 'react';
import axios from 'axios';
import { Building2, Package2, Users, Search, Image as ImageIcon } from 'lucide-react';

const API_URL = '/api';

export default function AdminDashboard() {
  const [overview, setOverview] = useState({ total_companies: 0, total_users: 0, total_products: 0 });
  const [companies, setCompanies] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('companies'); // 'companies' or 'products'
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [overviewRes, companiesRes, productsRes] = await Promise.all([
        axios.get(`${API_URL}/admin/overview`),
        axios.get(`${API_URL}/admin/companies`),
        axios.get(`${API_URL}/admin/products`)
      ]);
      setOverview(overviewRes.data);
      setCompanies(companiesRes.data);
      setProducts(productsRes.data);
    } catch (err) {
      console.error('Failed to fetch admin data', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredCompanies = companies.filter(c => 
    c.companyname?.toLowerCase().includes(search.toLowerCase())
  );

  const filteredProducts = products.filter(p => 
    p.productname?.toLowerCase().includes(search.toLowerCase()) ||
    p.company?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="admin-dashboard">
      <div className="header">
        <div>
          <h2 className="page-title">Admin Console</h2>
          <p className="page-subtitle">Platform overview and management</p>
        </div>
      </div>

      <div className="admin-stats-grid">
        <div className="stat-card">
          <div className="stat-icon companies-icon"><Building2 size={24} /></div>
          <div className="stat-info">
            <div className="stat-value">{overview.total_companies}</div>
            <div className="stat-label">Companies</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon products-icon"><Package2 size={24} /></div>
          <div className="stat-info">
            <div className="stat-value">{overview.total_products}</div>
            <div className="stat-label">Products</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon users-icon"><Users size={24} /></div>
          <div className="stat-info">
            <div className="stat-value">{overview.total_users}</div>
            <div className="stat-label">Users</div>
          </div>
        </div>
      </div>

      <div className="admin-tabs">
        <button 
          className={`tab-btn ${activeTab === 'companies' ? 'active' : ''}`}
          onClick={() => setActiveTab('companies')}
        >
          Companies
        </button>
        <button 
          className={`tab-btn ${activeTab === 'products' ? 'active' : ''}`}
          onClick={() => setActiveTab('products')}
        >
          Products
        </button>
      </div>

      <div className="admin-content glass-panel">
        <div className="admin-toolbar">
          <div className="search-box">
            <Search size={18} className="search-icon" />
            <input 
              type="text" 
              placeholder={`Search ${activeTab}...`} 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {loading ? (
          <div className="loading-state">Loading data...</div>
        ) : (
          <div className="admin-list">
            {activeTab === 'companies' && (
              <>
                {filteredCompanies.length === 0 ? <p className="empty-list">No companies found</p> : null}
                {filteredCompanies.map(c => (
                  <div key={c.companyid} className="admin-list-item">
                    <div className="item-avatar companies-icon"><Building2 size={20} /></div>
                    <div className="item-details">
                      <div className="item-title">{c.companyname}</div>
                      <div className="item-subtitle">{c.companyphonenumber || 'No phone number'}</div>
                    </div>
                    <div className="item-metrics">
                      <span className="metric-badge">{c.product_count} Products</span>
                      <span className="metric-badge">{c.user_count} Users</span>
                    </div>
                  </div>
                ))}
              </>
            )}

            {activeTab === 'products' && (
              <>
                {filteredProducts.length === 0 ? <p className="empty-list">No products found</p> : null}
                {filteredProducts.map(p => (
                  <div key={p.productid} className="admin-list-item">
                    {p.productphotourl && p.productphotourl.length > 0 ? (
                      <div className="item-avatar photo-avatar">
                        <img src={p.productphotourl[0]} alt={p.productname} />
                      </div>
                    ) : (
                      <div className="item-avatar fallback-icon"><ImageIcon size={20} /></div>
                    )}
                    <div className="item-details">
                      <div className="item-title">{p.productname}</div>
                      <div className="item-subtitle">{p.company} • By {p.uploaded_by}</div>
                    </div>
                    <div className="item-metrics">
                      <span className="metric-badge primary-badge">₹{Number(p.productprice).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                      <span className="metric-badge">{p.category}</span>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
