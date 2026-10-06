import { Link, useParams } from 'react-router';
import { obtenerRecinto } from '../api.js';
import Icono from '../componentes/Icono.jsx';
import Boleto from '../componentes/inicio/Boleto.jsx';
import MensajeError from '../componentes/MensajeError.jsx';
import ConciertosPasados from '../componentes/perfil/ConciertosPasados.jsx';
import { usarPeticion } from '../hooks/usarPeticion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import { plural } from '../utilidades/texto.js';
import PaginaNoEncontrada from './PaginaNoEncontrada.jsx';
import '../componentes/inicio/Boleto.css';
import '../componentes/perfil/Perfil.css';
import '../componentes/resenas/Resenas.css';
import './PaginaConcierto.css';

/** Enlace a Google Maps: por coordenadas si las hay (más exacto), si no por nombre y dirección. */
function enlaceMapa(recinto) {
  const destino = recinto.latitud != null
    ? `${recinto.latitud},${recinto.longitud}`
    : `${recinto.nombre}, ${recinto.direccion}, ${recinto.ciudad.nombre}`;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(destino)}`;
}

/** /recinto/:slug */
export default function PaginaRecinto() {
  const { slug } = useParams();
  const { datos: recinto, cargando, error, reintentar } = usarPeticion((signal) => obtenerRecinto(slug, signal), [slug]);
  usarTituloDocumento(recinto ? `${recinto.nombre} · ¿Quién toca?` : '¿Quién toca?');

  if (cargando) return <div className="centro pagina-estado"><p role="status" className="apagado">Cargando…</p></div>;
  if (error?.estado === 404) return <PaginaNoEncontrada mensaje="No encontramos este recinto." />;
  if (error) return <div className="centro pagina-estado"><MensajeError error={error} alReintentar={reintentar} /></div>;

  const { calificacion } = recinto;

  return (
    <article className="centro perfil">
      <Link className="volver" to={`/recintos/${recinto.ciudad.slug}`}>
        <Icono nombre="atras" />
        Recintos de {recinto.ciudad.nombre}
      </Link>
      <div className="cabeza cabeza--sin-cartel">
        <div>
          <p className="perfil__tipo">Recinto · {recinto.ciudad.nombre}</p>
          <h1 className="cartel" id="titulo-vista" tabIndex={-1}>{recinto.nombre}</h1>
          <dl className="datos">
            {recinto.direccion && (
              <div><dt>Dirección</dt><dd>{recinto.direccion}</dd></div>
            )}
            <div>
              <dt>Calificación del lugar</dt>
              <dd>
                {calificacion.total
                  ? `${calificacion.promedio.toFixed(1)} de 5, según ${plural(calificacion.total, 'reseña', 'reseñas')}`
                  : 'Todavía nadie lo ha calificado'}
              </dd>
            </div>
          </dl>
          <div className="redes">
            <a href={enlaceMapa(recinto)} target="_blank" rel="noopener noreferrer">
              Cómo llegar<span className="solo-lector"> (abre Google Maps)</span>
            </a>
          </div>
        </div>
      </div>

      <section className="perfil__seccion" aria-labelledby="t-proximas">
        <h2 className="cartel t-seccion" id="t-proximas">Próximos conciertos</h2>
        {recinto.proximos.length ? (
          <ol className="boletos">{recinto.proximos.map((c) => <Boleto key={c.slug} concierto={c} />)}</ol>
        ) : (
          <p className="apagado">No hay conciertos anunciados aquí por ahora.</p>
        )}
      </section>

      <ConciertosPasados conciertos={recinto.pasados} total={recinto.pasados_total} mostrar="artista" />
    </article>
  );
}
