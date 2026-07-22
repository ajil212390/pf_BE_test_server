import { useState } from 'react';
import axios from 'axios';

const API_URL = '/api'; // Use relative path for Docker Nginx proxy

export default function Login({ onLogin }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [companyPhone, setCompanyPhone] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    try {
      if (isRegistering) {
        await axios.post(`${API_URL}/register`, {
          username,
          userEmail: email,
          userPassword: password,
          companyName: companyName,
          companyPhoneNumber: companyPhone ? parseInt(companyPhone, 10) : null
        });
        setSuccessMsg('Registration successful! You can now sign in.');
        setIsRegistering(false);
        setPassword('');
      } else {
        const response = await axios.post(`${API_URL}/login`, {
          username,
          userPassword: password
        });
        onLogin(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.error || (isRegistering ? 'Registration failed' : 'Login failed'));
    }
  };

  return (
    <div className="login-wrapper">
      <div className="glass-panel login-box" style={isRegistering ? { maxHeight: 'none', paddingBottom: '32px' } : {}}>
        <h1>Nexus POS</h1>
        
        <div style={{ display: 'flex', marginBottom: '24px', borderBottom: '1px solid #374151' }}>
          <button 
            type="button"
            onClick={() => { setIsRegistering(false); setError(''); setSuccessMsg(''); }}
            style={{ 
              flex: 1, 
              padding: '12px', 
              background: 'none', 
              border: 'none', 
              color: !isRegistering ? '#3b82f6' : '#9ca3af',
              borderBottom: !isRegistering ? '2px solid #3b82f6' : '2px solid transparent',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '16px'
            }}
          >
            Sign In
          </button>
          <button 
            type="button"
            onClick={() => { setIsRegistering(true); setError(''); setSuccessMsg(''); }}
            style={{ 
              flex: 1, 
              padding: '12px', 
              background: 'none', 
              border: 'none', 
              color: isRegistering ? '#3b82f6' : '#9ca3af',
              borderBottom: isRegistering ? '2px solid #3b82f6' : '2px solid transparent',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '16px'
            }}
          >
            Register
          </button>
        </div>
        
        {error && <div style={{ color: '#ef4444', marginBottom: '16px', fontSize: '14px' }}>{error}</div>}
        {successMsg && <div style={{ color: '#10b981', marginBottom: '16px', fontSize: '14px' }}>{successMsg}</div>}
        
        <form onSubmit={handleSubmit}>
          {isRegistering && (
            <>
              <input 
                type="email" 
                className="input-field" 
                placeholder="Email Address" 
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
              <input 
                type="text" 
                className="input-field" 
                placeholder="Company Name (Optional)" 
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
              />
              <input 
                type="tel" 
                className="input-field" 
                placeholder="Company Phone (Optional)" 
                value={companyPhone}
                onChange={e => setCompanyPhone(e.target.value)}
              />
            </>
          )}
          
          <input 
            type="text" 
            className="input-field" 
            placeholder="Username" 
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
          />
          <input 
            type="password" 
            className="input-field" 
            placeholder="Password" 
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
          <button type="submit" className="btn" style={{ width: '100%' }}>
            {isRegistering ? 'Create Account' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
