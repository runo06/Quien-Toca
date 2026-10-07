import { useState } from 'react';
import { Link, useLocation } from 'react-router';
import { obtenerMisConciertos, obtenerMisSugerencias } from '../api.js';
import Boleto from '../componentes/inicio/Boleto.jsx';
import MensajeError from '../componentes/MensajeError.jsx';
import { guardarCiudad, leerCiudadGuardada, usarCiudades } from '../contexto/ciudades.jsx';
import { usarPeticion } from '../hooks/usarPeticion.js';
import { usarSesion } from '../hooks/usarSesion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import { fechaMedia } from '../utilidades/fechas.js';
import { plural } from '../utilidades/texto.js';
import '../componentes/inicio/Boleto.css';
import '../componentes/perfil/Perfil.css';
import './PaginaConcierto.css';

const ESTADOS_SUGERENCIA = { pendiente: 'En revisión', aprobada: 'Aprobada', rechazada: 'No se agregó' };

function Seccion({ id, titulo, children }) {
  return (
    <section className="perfil__seccion" aria-labelledby={id}>
      <h2 className="cartel t-seccion" id={id}>{titulo}</h2>
      {children}
    </section>
  );
}

function Vacio({ children }) {
  return <div className="vacio"><p>{children}</p></div>;
}

/** Las próximas fechas de quienes sigo: primero las de mi ciudad, luego las demás. */
function DeArtistas({ conciertos, ciudad }) {
  const aqui = conciertos.filter((c) => c.recinto.ciudad.slug === ciudad.slug);
  const fuera = conciertos.filter((c) => c.recinto.ciudad.slug !== ciudad.slug);
  return (
    <>
      {aqui.length > 0 && (
        <>
          <h3 className="subtitulo">En {ciudad.nombre}</h3>
          <ol className="boletos">{aqui.map((c) => <Boleto key={c.slug} concierto={c} />)}</ol>
        </>
      )}
      {!aqui.length && <p className="apagado">No tienen fechas en {ciudad.nombre} por ahora.</p>}
      {fuera.length > 0 && (
        <>
          <h3 className="subtitulo">En otras ciudades</h3>
          <ol className="boletos">{fuera.map((c) => <Boleto key={c.slug} concierto={c} />)}</ol>
        </>
      )}
    </>
  );
}

function Contenido({ usuario }) {
  const ciudades = usarCiudades();
  const [slugCiudad, setSlugCiudad] = useState(() => leerCiudadGuardada());
  const ciudad = ciudades.datos?.find((c) => c.slug === slugCiudad) ?? ciudades.datos?.find((c) => c.es_predeterminada);
  const mios = usarPeticion((signal) => obtenerMisConciertos(ciudad?.slug, signal), [ciudad?.slug, usuario.id]);
  const sugerencias = usarPeticion((signal) => obtenerMisSugerencias(signal), [usuario.id]);

  if (mios.error) return <MensajeError error={mios.error} alReintentar={mios.reintentar} />;
  if (mios.cargando || !ciudad) return <p role="status" className="apagado" style={{ marginTop: 24 }}>Cargando…</p>;
  const { de_artistas: deArtistas, guardados, guardados_pasados: pasados, artistas } = mios.datos;

  function elegirCiudad(slug) {
    setSlugCiudad(slug);
    guardarCiudad(slug);
  }

  return (
    <>
      <div className="fichas" role="group" aria-label="Mi ciudad" style={{ marginTop: 22 }}>
        {ciudades.datos.map((c) => (
          <button key={c.slug} type="button" className="ficha" aria-pressed={c.slug === ciudad.slug} onClick={() => elegirCiudad(c.slug)}>
            {c.nombre}
          </button>
        ))}
      </div>

      <Seccion id="t-de-artistas" titulo="De los artistas que sigues">
        {artistas.length ? (
          deArtistas.length ? <DeArtistas conciertos={deArtistas} ciudad={ciudad} /> : (
            <Vacio>Los artistas que sigues no tienen fechas anunciadas por ahora. Te las mostramos aquí en cuanto aparezcan.</Vacio>
          )
        ) : (
          <Vacio>Aún no sigues a nadie. En la página de un artista pulsa <strong>Seguir</strong> y aquí verás sus próximas fechas.</Vacio>
        )}
      </Seccion>

      <Seccion id="t-guardados" titulo="Guardados">
        {guardados.length ? (
          <ol className="boletos">{guardados.map((c) => <Boleto key={c.slug} concierto={c} />)}</ol>
        ) : (
          <Vacio>No tienes conciertos guardados. En la página de un concierto pulsa <strong>Guardar</strong> para tenerlo a mano.</Vacio>
        )}
      </Seccion>

      {pasados.length > 0 && (
        <Seccion id="t-fuiste" titulo="¿Fuiste?">
          <ol className="fechas__lista">
            {pasados.map((c) => (
              <li key={c.slug}>
                <Link className="parada parada--pasada" to={`/concierto/${c.slug}`}>
                  <span className="parada__dia">{fechaMedia(c.fecha_hora)}</span>
                  <span>
                    <strong>{c.artista.nombre}</strong>
                    <span>{c.resenaste ? 'Ya lo reseñaste' : 'Cuenta cómo estuvo →'}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </Seccion>
      )}

      {artistas.length > 0 && (
        <Seccion id="t-sigues" titulo="Artistas que sigues">
          <ul className="redes">
            {artistas.map((a) => (
              <li key={a.slug}>
                <Link to={`/artista/${a.slug}`}>
                  {a.nombre}<span className="apagado">&nbsp;· {a.proximos ? plural(a.proximos, 'fecha', 'fechas') : 'sin fechas'}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Seccion>
      )}

      <Seccion id="t-sugerencias" titulo="Tus sugerencias">
        {sugerencias.datos?.length > 0 && (
          <ul className="sugerencias">
            {sugerencias.datos.map((s) => (
              <li key={s.id}>
                <strong>{s.artista}</strong>
                <span className="apagado">{s.recinto}, {fechaMedia(`${s.fecha}T12:00:00`)}</span>
                <span className={`estado-sugerencia estado-sugerencia--${s.estado}`}>{ESTADOS_SUGERENCIA[s.estado]}</span>
                {s.estado === 'aprobada' && s.concierto && <Link className="enlace" to={`/concierto/${s.concierto}`}>Ver concierto</Link>}
                {s.estado === 'rechazada' && s.motivo_rechazo && <span className="letra-chica" style={{ margin: 0 }}>{s.motivo_rechazo}</span>}
              </li>
            ))}
          </ul>
        )}
        <p style={{ marginTop: 14 }}>
          ¿Falta un concierto en la cartelera? <Link className="enlace" to="/sugerir">Sugiérelo</Link>
        </p>
      </Seccion>
    </>
  );
}

/** /mis-conciertos */
export default function PaginaMisConciertos() {
  const usuario = usarSesion();
  const ubicacion = useLocation();
  usarTituloDocumento('Mis conciertos · ¿Quién toca?');

  return (
    <div className="centro perfil">
      <h1 className="cartel t-seccion" id="titulo-vista" tabIndex={-1} style={{ marginTop: 24 }}>Mis conciertos</h1>
      {usuario ? (
        <Contenido usuario={usuario} />
      ) : (
        <div className="vacio" style={{ marginTop: 24 }}>
          <p>Inicia sesión para seguir a tus artistas, guardar conciertos y verlos todos aquí.</p>
          <Link className="boton" to="/entrar" state={{ desde: ubicacion.pathname }}>Iniciar sesión</Link>
        </div>
      )}
    </div>
  );
}
