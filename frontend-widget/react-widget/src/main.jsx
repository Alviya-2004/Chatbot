import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import LandingPage from './LandingPage.jsx'
import AdminAuth from './AdminAuth.jsx'

const path = window.location.pathname;

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {path === '/admin' ? (
      <AdminAuth />
    ) : (
      <>
        <LandingPage />
        <App />
      </>
    )}
  </StrictMode>,
)
