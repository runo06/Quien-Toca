import { Link, NavLink, useLocation, useParams } from 'react-router';
import { obtenerResumenEdicion } from '../api.js';
import FormularioGira from '../componentes/edicion/FormularioGira.jsx';
import { RevisarReportes, RevisarSugerencias } from '../componentes/edicion/Revisiones.jsx';
import { usarPeticion } from '../hooks/usarPeticion.js';
import { usarSesion } from '../hooks/usarSesion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import PaginaNoEncontrada from './PaginaNoEncontrada.jsx';
import '../componentes/edicion/Edicion.css';
import './PaginaCuenta.css';

const SECCIONES = {
  gira: { titulo: 'Capturar gira', Componente: FormularioGira },
  sugerencias: { titulo: 'Sugerencias', Componente: RevisarSugerencias },
  reportes: { titulo: 'Reportes de reseñas', Componente: RevisarReportes },
};

/** Solo para quien tiene el rol Editor (el servidor lo vuelve a revisar en cada petición). */
export function SoloEditores({ children }) {
  const usuario = usarSesion();
  const ubicacion = useLocation();
  if (!usuario) {
    return (
      <div className="centro pagina-estado">
        <div className="vacio">
          <p>Inicia sesión con tu cuenta de editor.</p>
          <Link className="boton" to="/entrar" state={{ desde: ubicacion.pathname }}>Iniciar sesión</Link>
        </div>
      </div>
    );
  }
  if (!usuario.es_editor) {
    return (
      <div className="centro pagina-estado">
        <div className="vacio"><p>Esta sección es solo para editores. Si necesitas acceso, pídelo a quien administra el sitio.</p></div>
      </div>
    );
  }
  return children;
}

function Contenido() {
  const { seccion } = useParams();
  const resumen = usarPeticion(obtenerResumenEdicion, []);
  const actual = SECCIONES[seccion ?? 'gira']; // /editar a secas abre la captura de giras
  usarTituloDocumento(actual ? `${actual.titulo} · Editar · ¿Quién toca?` : '¿Quién toca?');
  if (!actual) return <PaginaNoEncontrada />;

  const pendientes = (n) => (n ? <span className="contador-pendientes">{n}</span> : null);
  const { Componente } = actual;

  return (
    <div className="centro edicion">
      <h1 className="cartel t-seccion" id="titulo-vista" tabIndex={-1}>Editar</h1>
      <nav className="pestanas" aria-label="Secciones de edición">
        <NavLink to="/editar" end>Capturar gira</NavLink>
        <NavLink to="/editar/sugerencias">Sugerencias {pendientes(resumen.datos?.sugerencias_pendientes)}</NavLink>
        <NavLink to="/editar/reportes">Reportes {pendientes(resumen.datos?.reportes_pendientes)}</NavLink>
      </nav>
      <p className="letra-chica">
        Para editar o cancelar un concierto, ábrelo en la cartelera y pulsa <strong>Editar</strong>.
      </p>
      <Componente alCambiar={resumen.refrescar} />
    </div>
  );
}

/** /editar, /editar/sugerencias y /editar/reportes */
export default function PaginaEditar() {
  return <SoloEditores><Contenido /></SoloEditores>;
}
