import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// This release ships the dark interface only (the light theme had visual
// inconsistencies). <html class="dark"> is set in index.html so there is no
// light flash before React loads; drop the old persisted toggle preference.
document.documentElement.classList.add('dark');
try {
  localStorage.removeItem('dq-theme-storage');
} catch {
  // storage unavailable (private mode etc.) - nothing to clean up
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
