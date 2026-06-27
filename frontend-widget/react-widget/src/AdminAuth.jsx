import React, { useState } from 'react';
import AdminPanel from './AdminPanel';

export default function AdminAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState(false);

  const handleLogin = (e) => {
    e.preventDefault();
    if (password === 'admin123') {
      setIsAuthenticated(true);
      setError(false);
    } else {
      setError(true);
    }
  };

  if (isAuthenticated) {
    return <AdminPanel />;
  }

  return (
    <div className="admin-login-container">
      <div className="admin-login-card">
        <h2>Admin Dashboard</h2>
        <p>Please enter the admin password to continue.</p>
        <form onSubmit={handleLogin}>
          <input 
            type="password" 
            placeholder="Password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)} 
            autoFocus
          />
          {error && <div className="error-text">Incorrect password.</div>}
          <button type="submit">Login</button>
        </form>
        <a href="/" className="back-link">Return to Website</a>
      </div>
    </div>
  );
}
