import { useEffect, useRef } from 'react';
import { refrescarUsuario } from './api.js';
import { BrowserRouter, Route, Routes, useLocation } from 'react-router';
import AvisoDespertando from './componentes/AvisoDespertando.jsx';
import AvisoFlotante from './componentes/AvisoFlotante.jsx';
import Encabezado from './componentes/Encabezado.jsx';
import PiePagina from './componentes/PiePagina.jsx';
import { ProveedorCiudades } from './contexto/ciudades.jsx';
import PaginaConcierto from './paginas/PaginaConcierto.jsx';
import PaginaArtista from './paginas/PaginaArtista.jsx';
import PaginaCuenta from './paginas/PaginaCuenta.jsx';
import PaginaEditar from './paginas/PaginaEditar.jsx';
import PaginaEditarArtista from './paginas/PaginaEditarArtista.jsx';
import PaginaEditarConcierto from './paginas/PaginaEditarConcierto.jsx';
import PaginaMisConciertos from './paginas/PaginaMisConciertos.jsx';
import PaginaInicio from './paginas/PaginaInicio.jsx';
import PaginaNoEncontrada from './paginas/PaginaNoEncontrada.jsx';
import PaginaRecinto from './paginas/PaginaRecinto.jsx';
import PaginaRecintos from './paginas/PaginaRecintos.jsx';
import PaginaSugerir from './paginas/PaginaSugerir.jsx';
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
  // Al abrir la página se actualizan los datos de la cuenta (p. ej. si ganó o perdió el rol de editor).
  useEffect(() => { refrescarUsuario(); }, []);

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
            <Route path="/artista/:slug" element={<PaginaArtista />} />
            <Route path="/recinto/:slug" element={<PaginaRecinto />} />
            <Route path="/recintos" element={<PaginaRecintos />} />
            <Route path="/recintos/:ciudad" element={<PaginaRecintos />} />
            <Route path="/mis-conciertos" element={<PaginaMisConciertos />} />
            <Route path="/sugerir" element={<PaginaSugerir />} />
            <Route path="/editar" element={<PaginaEditar />} />
            <Route path="/editar/concierto/:slug" element={<PaginaEditarConcierto />} />
            <Route path="/editar/artista/:slug" element={<PaginaEditarArtista />} />
            <Route path="/editar/:seccion" element={<PaginaEditar />} />
            <Route path="/entrar" element={<PaginaCuenta modo="entrar" key="entrar" />} />
            <Route path="/registro" element={<PaginaCuenta modo="registro" key="registro" />} />
            <Route path="/:ciudad" element={<PaginaInicio />} />
            <Route path="*" element={<PaginaNoEncontrada />} />
          </Routes>
        </main>
        <PiePagina />
        <AvisoDespertando />
        <AvisoFlotante />
      </ProveedorCiudades>
    </BrowserRouter>
  );
}
