import { Link } from 'react-router';
import { fechaMedia } from '../../utilidades/fechas.js';
import { plural } from '../../utilidades/texto.js';
import Icono from '../Icono.jsx';

/**
 * Las fechas que ya pasaron, cada una con sus reseñas. En la página de un artista
 * cada fecha dice la ciudad; en la de un recinto, quién tocó (mostrar="artista").
 */
export default function ConciertosPasados({ conciertos, total, mostrar = 'ciudad' }) {
  if (!conciertos.length) return null;
  return (
    <section className="perfil__seccion" aria-labelledby="t-pasados">
      <h2 className="cartel t-seccion" id="t-pasados">Ya pasaron</h2>
      <ol className="fechas__lista">
        {conciertos.map((c) => (
          <li key={c.slug}>
            <Link className="parada parada--pasada" to={`/concierto/${c.slug}`}>
              <span className="parada__dia">{fechaMedia(c.fecha_hora)}</span>
              <span>
                <strong>{mostrar === 'artista' ? c.artista.nombre : `${c.recinto.ciudad.nombre}, ${c.recinto.nombre}`}</strong>
                <span className="parada__nota">
                  {c.resenas ? (
                    <><Icono nombre="estrella" />{c.promedio.toFixed(1)} · {plural(c.resenas, 'reseña', 'reseñas')}</>
                  ) : 'Sin reseñas'}
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ol>
      {total > conciertos.length && (
        <p className="letra-chica">Se muestran los {conciertos.length} más recientes de {total}.</p>
      )}
    </section>
  );
}
