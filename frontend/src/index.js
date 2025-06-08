import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; // Globální styly, pokud nějaké budou
import App from './App';
import './App.css'; // Přidání importu App.css

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
