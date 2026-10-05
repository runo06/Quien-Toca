// Punto de entrada: monta la aplicación de React dentro de <div id="raiz"> (index.html).
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './estilos/base.css';

createRoot(document.getElementById('raiz')).render(
  // StrictMode solo actúa en desarrollo: ejecuta dos veces algunos efectos para
  // detectar errores, como peticiones que no se cancelan al desmontar.
  <StrictMode>
    <App />
  </StrictMode>,
);
