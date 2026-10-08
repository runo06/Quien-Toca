import { Link } from 'react-router';
import { buscarArtistas } from '../../api.js';
import { usarPeticion } from '../../hooks/usarPeticion.js';
import { plural } from '../../utilidades/texto.js';
import Cartel from '../cartel/Cartel.jsx';

/** Al buscar, los perfiles de artista que coinciden van primero (también los que no tienen fechas). */
export default function ArtistasEncontrados({ texto }) {
  const q = texto.trim();
  const { datos } = usarPeticion(
    (signal) => (q.length >= 2 ? buscarArtistas(q, signal) : Promise.resolve([])),
    [q],
  );
  if (!datos?.length) return null;

  return (
    <section className="encontrados" aria-labelledby="t-encontrados">
      <div className="centro">
        <h2 className="etiqueta" id="t-encontrados">Artistas</h2>
        <ul className="encontrados__lista">
          {datos.map((a) => (
            <li key={a.slug}>
              <Link className="encontrado" to={`/artista/${a.slug}`}>
                <span className="encontrado__foto"><Cartel imagen={a.imagen_url} semilla={a.slug} tamano={120} /></span>
                <span>
                  <strong>{a.nombre}</strong>
                  <span className="apagado">
                    {a.proximos ? plural(a.proximos, 'fecha próxima', 'fechas próximas') : 'Sin fechas anunciadas'}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
