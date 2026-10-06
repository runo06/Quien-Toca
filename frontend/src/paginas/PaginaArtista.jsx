import { useParams } from 'react-router';
import { obtenerArtista } from '../api.js';
import Cartel from '../componentes/cartel/Cartel.jsx';
import Boleto from '../componentes/inicio/Boleto.jsx';
import MensajeError from '../componentes/MensajeError.jsx';
import ConciertosPasados from '../componentes/perfil/ConciertosPasados.jsx';
import TarjetaResena from '../componentes/resenas/TarjetaResena.jsx';
import { usarPeticion } from '../hooks/usarPeticion.js';
import { usarResenas } from '../hooks/usarResenas.js';
import { usarSesion } from '../hooks/usarSesion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import { plural } from '../utilidades/texto.js';
import PaginaNoEncontrada from './PaginaNoEncontrada.jsx';
import '../componentes/inicio/Boleto.css';
import '../componentes/perfil/Perfil.css';
import '../componentes/resenas/Resenas.css';
import './PaginaConcierto.css';

const REDES = [
  ['homepage', 'Sitio oficial'], ['instagram', 'Instagram'], ['spotify', 'Spotify'], ['youtube', 'YouTube'],
  ['tiktok', 'TikTok'], ['facebook', 'Facebook'], ['twitter', 'X (Twitter)'],
];

function Barra({ nombre, valor, maximo = 5, texto, clase = '' }) {
  return (
    <div className={`barra-fila ${clase}`}>
      <span>{nombre}</span>
      <i aria-hidden="true"><b style={{ width: `${maximo ? (valor / maximo) * 100 : 0}%` }} /></i>
      <strong>{texto ?? valor.toFixed(1)}</strong>
    </div>
  );
}

/** Promedio, aspectos, cuántas estrellas dio la gente y cómo le fue en cada ciudad. */
function Estadisticas({ artista }) {
  const { calificacion, distribucion, por_ciudad: porCiudad } = artista;
  const aspectos = [['Show en vivo', calificacion.show], ['Sonido', calificacion.sonido], ['Puntualidad', calificacion.puntualidad]]
    .filter(([, valor]) => valor != null);
  const masVotada = Math.max(...distribucion.map((d) => d.total));

  return (
    <section className="perfil__seccion" aria-labelledby="t-estadisticas">
      <h2 className="cartel t-seccion" id="t-estadisticas">Cómo le ha ido en vivo</h2>
      <div className="estadisticas">
        <div>
          <p className="promedio">
            <b>{calificacion.promedio.toFixed(1)}</b>
            <span className="apagado">de 5, con {plural(calificacion.total, 'reseña', 'reseñas')}</span>
          </p>
          {aspectos.length > 0 && (
            <div className="barras" style={{ marginTop: 18 }}>
              {aspectos.map(([nombre, valor]) => <Barra key={nombre} nombre={nombre} valor={valor} />)}
            </div>
          )}
        </div>
        <div>
          <h3 className="subtitulo">Calificaciones</h3>
          <div className="barras">
            {distribucion.map((d) => (
              <Barra
                key={d.estrellas} clase="barra-fila--conteo" nombre={`${d.estrellas} ${d.estrellas === 1 ? 'estrella' : 'estrellas'}`}
                valor={d.total} maximo={masVotada} texto={d.total}
              />
            ))}
          </div>
        </div>
        {porCiudad.length > 1 && (
          <div>
            <h3 className="subtitulo">Por ciudad</h3>
            <div className="barras">
              {porCiudad.map((c) => <Barra key={c.slug} nombre={c.ciudad} valor={c.promedio} />)}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function ResenasDelArtista({ slug }) {
  const usuario = usarSesion();
  const resenas = usarResenas({ artista: slug }, usuario?.id);
  if (!resenas.lista.length) return null;
  return (
    <section className="perfil__seccion" aria-labelledby="t-resenas">
      <h2 className="cartel t-seccion" id="t-resenas">Lo que dicen quienes fueron</h2>
      <div className="voces__lista">
        {resenas.lista.map((resena) => (
          <TarjetaResena key={resena.id} resena={resena} alCambiar={resenas.reemplazar} alBorrar={resenas.quitar} />
        ))}
      </div>
      {resenas.hayMas && !resenas.cargando && (
        <button type="button" className="boton boton--linea" style={{ marginTop: 18 }} onClick={resenas.verMas}>
          Ver más reseñas
        </button>
      )}
    </section>
  );
}

/** /artista/:slug */
export default function PaginaArtista() {
  const { slug } = useParams();
  const { datos: artista, cargando, error, reintentar } = usarPeticion((signal) => obtenerArtista(slug, signal), [slug]);
  usarTituloDocumento(artista ? `${artista.nombre} · ¿Quién toca?` : '¿Quién toca?');

  if (cargando) return <div className="centro pagina-estado"><p role="status" className="apagado">Cargando…</p></div>;
  if (error?.estado === 404) return <PaginaNoEncontrada mensaje="No encontramos a este artista." />;
  if (error) return <div className="centro pagina-estado"><MensajeError error={error} alReintentar={reintentar} /></div>;

  const redes = REDES.filter(([tipo]) => artista.enlaces[tipo]);

  return (
    <article className="centro perfil">
      <div className="cabeza">
        <div className="cartelote">
          <Cartel imagen={artista.imagen_url} semilla={artista.slug} tamano={760} />
        </div>
        <div>
          <p className="perfil__tipo">Artista{artista.genero ? ` · ${artista.genero}` : ''}</p>
          <h1 className="cartel" id="titulo-vista" tabIndex={-1}>{artista.nombre}</h1>
          {artista.descripcion && <p className="descripcion">{artista.descripcion}</p>}
          {artista.descripcion_fuente && (
            <p className="letra-chica">
              Fuente: <a href={artista.descripcion_fuente} target="_blank" rel="noopener noreferrer">Wikipedia</a> (CC BY-SA)
            </p>
          )}
          {redes.length > 0 && (
            <nav className="redes" aria-label={`${artista.nombre} en internet`}>
              {redes.map(([tipo, nombre]) => (
                <a key={tipo} href={artista.enlaces[tipo]} target="_blank" rel="noopener noreferrer">{nombre}</a>
              ))}
            </nav>
          )}
        </div>
      </div>

      <section className="perfil__seccion" aria-labelledby="t-proximas">
        <h2 className="cartel t-seccion" id="t-proximas">Próximas fechas</h2>
        {artista.proximos.length ? (
          <ol className="boletos">{artista.proximos.map((c) => <Boleto key={c.slug} concierto={c} />)}</ol>
        ) : (
          <p className="apagado">No tiene fechas anunciadas por ahora.</p>
        )}
      </section>

      {artista.calificacion.total > 0 && <Estadisticas artista={artista} />}
      <ConciertosPasados conciertos={artista.pasados} total={artista.pasados_total} />
      <ResenasDelArtista slug={artista.slug} />
    </article>
  );
}
