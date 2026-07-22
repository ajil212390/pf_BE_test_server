import { useState, useEffect } from 'react';
import axios from 'axios';
import { User, Building2, Lock, Phone } from 'lucide-react';

const API_URL = '/api';

export default function SettingsPage({ user, setUser }) {
  const [activeTab, setActiveTab] = useState('profile');

  // Company State
  const [companyName, setCompanyName] = useState(user?.companyname || '');
  const [companyPhone, setCompanyPhone] = useState(user?.companyphonenumber || '');
  const [companySaving, setCompanySaving] = useState(false);
  const [companyMessage, setCompanyMessage] = useState({ type: '', text: '' });

  // Password State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState({ type: '', text: '' });

  const handleUpdateCompany = async (e) => {
    e.preventDefault();
    setCompanyMessage({ type: '', text: '' });
    setCompanySaving(true);
    try {
      const res = await axios.post(`${API_URL}/auth/update-company`, {
        userId: user.userid,
        companyName: companyName,
        companyPhoneNumber: companyPhone ? parseInt(companyPhone) : null
      });

      // Update local storage and app state
      const updatedUser = { ...user, companyname: companyName, companyphonenumber: companyPhone };
      localStorage.setItem('nexus_user', JSON.stringify(updatedUser));
      setUser(updatedUser);

      setCompanyMessage({ type: 'success', text: 'Company profile updated successfully!' });
    } catch (err) {
      setCompanyMessage({ type: 'error', text: err.response?.data?.error || 'Failed to update company' });
    } finally {
      setCompanySaving(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordMessage({ type: '', text: '' });

    if (newPassword !== confirmPassword) {
      setPasswordMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }

    if (newPassword.length < 5) {
      setPasswordMessage({ type: 'error', text: 'Password must be at least 5 characters' });
      return;
    }

    setPasswordSaving(true);
    try {
      const res = await axios.post(`${API_URL}/auth/change-password`, {
        userId: user.userid,
        currentPassword: currentPassword,
        newPassword: newPassword
      });
      setPasswordMessage({ type: 'success', text: 'Password changed successfully!' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPasswordMessage({ type: 'error', text: err.response?.data?.error || 'Failed to change password' });
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <div className="page-container max-w-3xl">
      <div className="header">
        <div>
          <h2 className="page-title">Settings</h2>
          <p className="page-subtitle">Manage your account and security</p>
        </div>
      </div>

      <div className="admin-tabs" style={{ marginBottom: '32px' }}>
        <button 
          className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          <User size={16} style={{ display: 'inline', marginRight: 6, verticalAlign: 'text-bottom' }} /> 
          Company Profile
        </button>
        <button 
          className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          <Lock size={16} style={{ display: 'inline', marginRight: 6, verticalAlign: 'text-bottom' }} /> 
          Security
        </button>
      </div>

      <div className="glass-panel form-panel">
        {activeTab === 'profile' && (
          <form onSubmit={handleUpdateCompany} className="web-form">
            <h3 className="product-title" style={{ marginBottom: 24 }}>Business Information</h3>
            
            {companyMessage.text && (
              <div className={companyMessage.type === 'error' ? 'error-message' : 'success-message'} style={{ padding: 12, borderRadius: 8, marginBottom: 20, background: companyMessage.type === 'error' ? '#fef2f2' : '#ecfdf5', color: companyMessage.type === 'error' ? '#ef4444' : '#10b981', border: `1px solid ${companyMessage.type === 'error' ? '#fee2e2' : '#d1fae5'}` }}>
                {companyMessage.text}
              </div>
            )}

            <div className="form-group full-width" style={{ marginBottom: 24 }}>
              <label>Company Name</label>
              <div className="input-with-icon">
                <Building2 className="prefix-icon icon-svg" size={18} />
                <input 
                  type="text" 
                  className="web-input with-prefix" 
                  placeholder="Your Company Name" 
                  value={companyName}
                  onChange={e => setCompanyName(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group full-width" style={{ marginBottom: 24 }}>
              <label>Business Phone</label>
              <div className="input-with-icon">
                <Phone className="prefix-icon icon-svg" size={18} />
                <input 
                  type="number" 
                  className="web-input with-prefix" 
                  placeholder="Phone Number" 
                  value={companyPhone}
                  onChange={e => setCompanyPhone(e.target.value)}
                />
              </div>
            </div>

            <div className="form-actions" style={{ marginTop: 32 }}>
              <button 
                type="submit" 
                className="btn-gradient px-8"
                disabled={companySaving}
              >
                {companySaving ? 'Saving...' : 'Update Profile'}
              </button>
            </div>
          </form>
        )}

        {activeTab === 'security' && (
          <form onSubmit={handleChangePassword} className="web-form">
            <h3 className="product-title" style={{ marginBottom: 24 }}>Change Password</h3>
            
            {passwordMessage.text && (
              <div className={passwordMessage.type === 'error' ? 'error-message' : 'success-message'} style={{ padding: 12, borderRadius: 8, marginBottom: 20, background: passwordMessage.type === 'error' ? '#fef2f2' : '#ecfdf5', color: passwordMessage.type === 'error' ? '#ef4444' : '#10b981', border: `1px solid ${passwordMessage.type === 'error' ? '#fee2e2' : '#d1fae5'}` }}>
                {passwordMessage.text}
              </div>
            )}

            <div className="form-group full-width" style={{ marginBottom: 24 }}>
              <label>Current Password</label>
              <div className="input-with-icon">
                <Lock className="prefix-icon icon-svg" size={18} />
                <input 
                  type="password" 
                  className="web-input with-prefix" 
                  placeholder="Enter current password" 
                  value={currentPassword}
                  onChange={e => setCurrentPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-divider"></div>

            <div className="form-group full-width" style={{ marginBottom: 24 }}>
              <label>New Password</label>
              <div className="input-with-icon">
                <Lock className="prefix-icon icon-svg" size={18} />
                <input 
                  type="password" 
                  className="web-input with-prefix" 
                  placeholder="Enter new password" 
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group full-width" style={{ marginBottom: 24 }}>
              <label>Confirm New Password</label>
              <div className="input-with-icon">
                <Lock className="prefix-icon icon-svg" size={18} />
                <input 
                  type="password" 
                  className="web-input with-prefix" 
                  placeholder="Confirm new password" 
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-actions" style={{ marginTop: 32 }}>
              <button 
                type="submit" 
                className="btn-gradient px-8"
                disabled={passwordSaving}
              >
                {passwordSaving ? 'Updating...' : 'Change Password'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
