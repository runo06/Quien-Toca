import { Link, useLocation, useNavigate } from 'react-router';
import { salir } from '../api.js';
import { usarSesion } from '../hooks/usarSesion.js';
import { avisar } from './AvisoFlotante.jsx';
import './Encabezado.css';

export default function Encabezado() {
  const usuario = usarSesion();
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const enCuenta = ubicacion.pathname === '/entrar' || ubicacion.pathname === '/registro';

  async function cerrarSesion() {
    await salir();
    avisar('Cerraste sesión');
    navegar(ubicacion.pathname + ubicacion.search, { replace: true }); // se queda en la misma página
  }

  return (
    <header className="barra">
      <div className="centro">
        <Link className="marca" to="/">¿Quién toca?</Link>
        <nav aria-label="Principal">
          <Link to="/">Cartelera</Link>
          {usuario ? (
            <>
              <span className="barra__usuario">Hola, {usuario.nombre}</span>
              <button type="button" className="enlace barra__salir" onClick={cerrarSesion}>Salir</button>
            </>
          ) : (
            !enCuenta && (
              // Al terminar de entrar, se vuelve a esta misma página.
              <Link to="/entrar" state={{ desde: ubicacion.pathname + ubicacion.search }}>Entrar</Link>
            )
          )}
        </nav>
      </div>
    </header>
  );
}
