import { Link, useLocation, useParams } from 'react-router';
import { obtenerConcierto } from '../api.js';
import CabezaConcierto from '../componentes/concierto/CabezaConcierto.jsx';
import OtrasFechas from '../componentes/concierto/OtrasFechas.jsx';
import Taquilla from '../componentes/concierto/Taquilla.jsx';
import Icono from '../componentes/Icono.jsx';
import MensajeError from '../componentes/MensajeError.jsx';
import { usarPeticion } from '../hooks/usarPeticion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import PaginaNoEncontrada from './PaginaNoEncontrada.jsx';
import './PaginaConcierto.css';

function ConciertoCargando() {
  return (
    <div className="centro concierto" aria-busy="true">
      <p role="status" className="solo-lector">Cargando el concierto…</p>
      <div className="cabeza" aria-hidden="true">
        <div className="cartelote esqueleto" />
        <div>
          <span className="esqueleto" style={{ width: '45%', height: 22 }} />
          <span className="esqueleto" style={{ width: '80%', height: 80, marginTop: 14 }} />
          <span className="esqueleto" style={{ width: '60%', height: 22, marginTop: 30 }} />
        </div>
      </div>
    </div>
  );
}

/** /concierto/:slug */
export default function PaginaConcierto() {
  const { slug } = useParams();
  const ubicacion = useLocation();
  const { datos: concierto, cargando, error, reintentar } = usarPeticion(
    (signal) => obtenerConcierto(slug, signal),
    [slug],
  );

  usarTituloDocumento(
    concierto ? `${concierto.artista.nombre} en ${concierto.recinto.ciudad.nombre} · ¿Quién toca?` : '¿Quién toca?',
  );

  if (cargando) return <ConciertoCargando />;
  if (error?.estado === 404) return <PaginaNoEncontrada mensaje="Este concierto no existe o cambió de dirección." />;
  if (error) return <div className="centro pagina-estado"><MensajeError error={error} alReintentar={reintentar} /></div>;

  const ciudad = concierto.recinto.ciudad;
  // Si venimos de la cartelera, "volver" regresa con los mismos filtros.
  const volverA = ubicacion.state?.desde ?? `/${ciudad.slug}`;

  return (
    <article className="concierto">
      <div className="centro">
        <Link className="volver" to={volverA}>
          <Icono nombre="atras" />
          Cartelera de {ciudad.nombre}
        </Link>
        {concierto.estado === 'cancelado' && (
          <p className="aviso-estado" role="status">Este concierto fue cancelado.</p>
        )}
        {(concierto.estado === 'pospuesto' || concierto.estado === 'reprogramado') && (
          <p className="aviso-estado" role="status">
            Este concierto fue {concierto.estado}. Confirma la nueva fecha en la boletera.
          </p>
        )}
        <CabezaConcierto concierto={concierto} />
        <Taquilla concierto={concierto} />
        <OtrasFechas concierto={concierto} />
      </div>
    </article>
  );
}
