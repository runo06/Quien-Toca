import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // escucha fuera del contenedor, no solo dentro
    port: 5173,
    // En Docker sobre Windows los avisos de "archivo cambiado" no siempre cruzan al
    // contenedor: con polling, Vite revisa los archivos cada poco y la recarga funciona.
    watch: { usePolling: true },
    // /api/... se reenvía a Django. Para el navegador todo viene del mismo origen,
    // así que en desarrollo no hace falta CORS.
    proxy: {
      '/api': {
        target: process.env.API_PROXY_DESTINO ?? 'http://localhost:8000',
        // Conserva el Host original (localhost): Django rechaza hosts que no
        // están en ALLOWED_HOSTS, como "backend".
        changeOrigin: false,
      },
    },
  },
});
