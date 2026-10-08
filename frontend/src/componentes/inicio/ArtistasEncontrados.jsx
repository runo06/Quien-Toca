import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { abrirArtistaExterno, buscarArtistas, buscarArtistasExternos } from '../../api.js';
import { usarPeticion } from '../../hooks/usarPeticion.js';
import { plural } from '../../utilidades/texto.js';
import { avisar } from '../AvisoFlotante.jsx';
import Cartel from '../cartel/Cartel.jsx';

const fechasDe = (n) => (n ? plural(n, 'fecha próxima', 'fechas próximas') : 'Sin fechas anunciadas');

/** detalle: las fechas en nuestras ciudades (los que tenemos) o el género (los de Ticketmaster,
 * cuyas fechas pueden ser en otros países). */
function Contenido({ artista, detalle }) {
  return (
    <>
      <span className="encontrado__foto"><Cartel imagen={artista.imagen_url} semilla={artista.slug ?? artista.id_ticketmaster} tamano={120} /></span>
      <span>
        <strong>{artista.nombre}</strong>
        <span className="apagado">{detalle}</span>
      </span>
    </>
  );
}

/** Uno que aún no tenemos: al tocarlo se crea su perfil (con su descripción) y se abre. */
function Externo({ artista }) {
  const navegar = useNavigate();
  const [abriendo, setAbriendo] = useState(false);
  async function abrir() {
    setAbriendo(true);
    try {
      const { slug } = await abrirArtistaExterno(artista.id_ticketmaster);
      navegar(`/artista/${slug}`);
    } catch (error) {
      avisar(error.message);
      setAbriendo(false);
    }
  }
  return (
    <button type="button" className="encontrado" onClick={abrir} disabled={abriendo} aria-busy={abriendo}>
      <Contenido artista={artista} detalle={artista.genero || 'Ver perfil'} />
      {abriendo && <span className="encontrado__abriendo">Abriendo…</span>}
    </button>
  );
}

/**
 * Al buscar, los perfiles de artista van primero (también los que no tienen fechas).
 * Si tenemos pocos, se completan con "Más artistas" de Ticketmaster.
 */
export default function ArtistasEncontrados({ texto }) {
  const q = texto.trim();
  const locales = usarPeticion((signal) => (q.length >= 2 ? buscarArtistas(q, signal) : Promise.resolve([])), [q]);
  const pocos = !locales.cargando && (locales.datos?.length ?? 0) < 3;
  const externos = usarPeticion(
    (signal) => (pocos && q.length >= 3 ? buscarArtistasExternos(q, signal) : Promise.resolve([])),
    [q, pocos],
  );
  const tenemos = locales.datos ?? [];
  const mas = externos.datos ?? [];
  if (!tenemos.length && !mas.length) return null;

  return (
    <section className="encontrados" aria-labelledby="t-encontrados">
      <div className="centro">
        {tenemos.length > 0 && (
          <>
            <h2 className="etiqueta" id="t-encontrados">Artistas</h2>
            <ul className="encontrados__lista">
              {tenemos.map((a) => (
                <li key={a.slug}><Link className="encontrado" to={`/artista/${a.slug}`}><Contenido artista={a} detalle={fechasDe(a.proximos)} /></Link></li>
              ))}
            </ul>
          </>
        )}
        {mas.length > 0 && (
          <>
            <h2 className="etiqueta" id={tenemos.length ? undefined : 't-encontrados'} style={{ marginTop: tenemos.length ? 18 : 0 }}>
              {tenemos.length ? 'Más artistas' : 'Artistas'}
            </h2>
            <ul className="encontrados__lista">
              {mas.map((a) => <li key={a.id_ticketmaster}><Externo artista={a} /></li>)}
            </ul>
          </>
        )}
      </div>
    </section>
  );
}
