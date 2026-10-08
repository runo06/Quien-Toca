import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router';
import { salir } from '../api.js';
import { usarSesion } from '../hooks/usarSesion.js';
import { avisar } from './AvisoFlotante.jsx';
import './Encabezado.css';

/**
 * En pantallas anchas, todo en una línea. En el teléfono, la marca y un botón
 * "Menú" que despliega las opciones (se cierra al elegir, al tocar fuera o con Escape).
 */
export default function Encabezado() {
  const usuario = usarSesion();
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const [abierto, setAbierto] = useState(false);
  const barra = useRef(null);
  const boton = useRef(null);
  const enCuenta = ubicacion.pathname === '/entrar' || ubicacion.pathname === '/registro';

  // Al cambiar de página, el menú se cierra.
  useEffect(() => setAbierto(false), [ubicacion.pathname]);

  useEffect(() => {
    if (!abierto) return;
    const alTocarFuera = (evento) => {
      if (!barra.current?.contains(evento.target)) setAbierto(false);
    };
    const alTeclear = (evento) => {
      if (evento.key === 'Escape') {
        setAbierto(false);
        boton.current?.focus();
      }
    };
    document.addEventListener('pointerdown', alTocarFuera);
    document.addEventListener('keydown', alTeclear);
    return () => {
      document.removeEventListener('pointerdown', alTocarFuera);
      document.removeEventListener('keydown', alTeclear);
    };
  }, [abierto]);

  async function cerrarSesion() {
    setAbierto(false);
    await salir();
    avisar('Cerraste sesión');
    navegar(ubicacion.pathname + ubicacion.search, { replace: true }); // se queda en la misma página
  }

  // "Cartelera" se marca en la portada de cualquier ciudad, no solo en "/".
  const activo = ({ isActive }) => (isActive ? 'activo' : undefined);
  const enCartelera = !/^\/(recintos?|mis-conciertos|artista|concierto|sugerir|entrar|registro|editar)(\/|$)/.test(ubicacion.pathname);

  return (
    <header className="barra" ref={barra}>
      <div className="centro barra__fila">
        <Link className="marca" to="/">¿Quién toca?</Link>
        <button
          ref={boton} type="button" className="barra__menu" aria-expanded={abierto} aria-controls="menu-principal"
          onClick={() => setAbierto((a) => !a)}
        >
          <span className="barra__hamburguesa" aria-hidden="true"><i /><i /><i /></span>
          {abierto ? 'Cerrar' : 'Menú'}
        </button>
        <nav id="menu-principal" className={`barra__nav${abierto ? ' barra__nav--abierta' : ''}`} aria-label="Principal">
          <ul className="barra__enlaces">
            <li><NavLink to="/" className={() => (enCartelera ? 'activo' : undefined)}>Cartelera</NavLink></li>
            <li><NavLink to="/recintos" className={activo}>Recintos</NavLink></li>
            {usuario && <li><NavLink to="/mis-conciertos" className={activo}>Mis conciertos</NavLink></li>}
            {usuario?.es_editor && <li><NavLink to="/editar" className={activo}>Editar</NavLink></li>}
          </ul>
          <div className="barra__cuenta">
            {usuario ? (
              <>
                <span className="barra__usuario">Hola, {usuario.nombre}</span>
                <button type="button" className="barra__salir" onClick={cerrarSesion}>Salir</button>
              </>
            ) : (
              !enCuenta && (
                // Al terminar de entrar, se vuelve a esta misma página.
                <Link className="barra__entrar" to="/entrar" state={{ desde: ubicacion.pathname + ubicacion.search }}>
                  Entrar
                </Link>
              )
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}
