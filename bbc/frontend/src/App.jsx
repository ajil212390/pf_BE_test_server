import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Package, LogOut, Settings, Plus, ShieldAlert, ShoppingBag } from 'lucide-react';
import Login from './Login';
import ProductsList from './ProductsList';
import MyProductsPage from './MyProductsPage';
import AddProductPage from './AddProductPage';
import EditProductPage from './EditProductPage';
import AdminDashboard from './AdminDashboard';
import SettingsPage from './SettingsPage';
import './index.css';

function RequireAuth({ children, user }) {
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function DashboardLayout({ user, setUser, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="dashboard-layout">
      <div className="sidebar">
        <div className="sidebar-brand">Micro POS</div>
        
        <div className="sidebar-menu">
          <div 
            className={`sidebar-item ${location.pathname === '/' ? 'active' : ''}`}
            onClick={() => navigate('/')}
          >
            <Package size={20} /> All Products
          </div>
          <div 
            className={`sidebar-item ${location.pathname === '/my-products' ? 'active' : ''}`}
            onClick={() => navigate('/my-products')}
          >
            <ShoppingBag size={20} /> My Products
          </div>
          <div 
            className={`sidebar-item ${location.pathname === '/add' ? 'active' : ''}`}
            onClick={() => navigate('/add')}
          >
            <Plus size={20} /> Add Product
          </div>
          {user?.username?.toLowerCase() === 'admin' && (
            <div 
              className={`sidebar-item ${location.pathname === '/admin' ? 'active' : ''}`}
              onClick={() => navigate('/admin')}
            >
              <ShieldAlert size={20} /> Admin Console
            </div>
          )}
          <div 
            className={`sidebar-item ${location.pathname === '/settings' ? 'active' : ''}`}
            onClick={() => navigate('/settings')}
          >
            <Settings size={20} /> Settings
          </div>
        </div>

        <div style={{ flex: 1 }}></div>
        
        <div className="user-profile-sidebar">
          <div className="user-avatar">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="user-info">
            <div className="user-name">{user?.username}</div>
            <div className="user-company">{user?.companyname || 'No Company'}</div>
          </div>
        </div>

        <div className="sidebar-item logout-btn" onClick={onLogout}>
          <LogOut size={20} /> Logout
        </div>
      </div>
      
      <div className="main-content">
        <Routes>
          <Route path="/" element={<ProductsList user={user} />} />
          <Route path="/my-products" element={<MyProductsPage user={user} />} />
          <Route path="/add" element={<AddProductPage user={user} />} />
          <Route path="/edit/:id" element={<EditProductPage user={user} />} />
          {user?.username?.toLowerCase() === 'admin' && (
            <Route path="/admin" element={<AdminDashboard user={user} />} />
          )}
          <Route path="/settings" element={<SettingsPage user={user} setUser={setUser} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('nexus_user');
    return saved ? JSON.parse(saved) : null;
  });

  const handleLogin = (userData) => {
    localStorage.setItem('nexus_user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('nexus_user');
    setUser(null);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route 
          path="/login" 
          element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/*" 
          element={
            <RequireAuth user={user}>
              <DashboardLayout user={user} setUser={setUser} onLogout={handleLogout} />
            </RequireAuth>
          } 
        />
      </Routes>
    </BrowserRouter>
  );
}
