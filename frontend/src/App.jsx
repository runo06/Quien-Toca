import { useEffect, useRef } from 'react';
import { BrowserRouter, Route, Routes, useLocation } from 'react-router';
import Encabezado from './componentes/Encabezado.jsx';
import PiePagina from './componentes/PiePagina.jsx';
import { ProveedorCiudades } from './contexto/ciudades.jsx';
import PaginaConcierto from './paginas/PaginaConcierto.jsx';
import PaginaInicio from './paginas/PaginaInicio.jsx';
import PaginaNoEncontrada from './paginas/PaginaNoEncontrada.jsx';
import RedirigirACiudad from './paginas/RedirigirACiudad.jsx';

/**
 * Al cambiar de pantalla: sube al inicio y lleva el foco al título, para que
 * quien navega con teclado o lector de pantalla sepa que la página cambió.
 */
function GestorDeEnfoque() {
  const ubicacion = useLocation();
  const primeraVez = useRef(true);

  useEffect(() => {
    if (primeraVez.current) {
      primeraVez.current = false; // al abrir la página no se mueve el foco
      return;
    }
    if (ubicacion.state?.conservarFoco) return; // p. ej. al cambiar de ciudad
    window.scrollTo(0, 0);
    const destino = document.getElementById('titulo-vista') ?? document.getElementById('contenido');
    destino?.focus({ preventScroll: true });
    // Solo al cambiar de ruta: cambiar filtros (?q=...) no debe mover el foco.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ubicacion.pathname]);

  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <ProveedorCiudades>
        <GestorDeEnfoque />
        <a className="saltar" href="#contenido">Saltar al contenido</a>
        <Encabezado />
        <main id="contenido" tabIndex={-1}>
          <Routes>
            <Route path="/" element={<RedirigirACiudad />} />
            <Route path="/concierto/:slug" element={<PaginaConcierto />} />
            <Route path="/:ciudad" element={<PaginaInicio />} />
            <Route path="*" element={<PaginaNoEncontrada />} />
          </Routes>
        </main>
        <PiePagina />
      </ProveedorCiudades>
    </BrowserRouter>
  );
}
