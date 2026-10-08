import { useId, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { crearArtistaEdicion, editarArtista, obtenerArtistaEdicion } from '../api.js';
import { avisar } from '../componentes/AvisoFlotante.jsx';
import Cartel from '../componentes/cartel/Cartel.jsx';
import Icono from '../componentes/Icono.jsx';
import MensajeError from '../componentes/MensajeError.jsx';
import { usarPeticion } from '../hooks/usarPeticion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import { SoloEditores } from './PaginaEditar.jsx';
import PaginaNoEncontrada from './PaginaNoEncontrada.jsx';
import '../componentes/edicion/Edicion.css';
import './PaginaConcierto.css';
import './PaginaCuenta.css';

const REDES = [
  ['homepage', 'Sitio oficial'], ['instagram', 'Instagram'], ['spotify', 'Spotify'], ['youtube', 'YouTube'],
  ['tiktok', 'TikTok'], ['facebook', 'Facebook'], ['twitter', 'X (Twitter)'],
];
const VACIO = { nombre: '', genero: '', imagen_url: '', descripcion: '', wikipedia: '', enlaces: {} };
const primero = (lista) => [].concat(lista ?? [])[0];

function Formulario({ artista }) {
  const id = useId();
  const navegar = useNavigate();
  const nuevo = !artista;
  const [valores, setValores] = useState(() => ({ ...VACIO, ...artista, enlaces: { ...artista?.enlaces } }));
  const [errores, setErrores] = useState({});
  const [enviando, setEnviando] = useState(false);

  const poner = (campo) => (e) => {
    setValores((v) => ({ ...v, [campo]: e.target.value }));
    setErrores((x) => ({ ...x, [campo]: undefined }));
  };
  const ponerEnlace = (tipo) => (e) => {
    setValores((v) => ({ ...v, enlaces: { ...v.enlaces, [tipo]: e.target.value } }));
    setErrores((x) => ({ ...x, enlaces: undefined }));
  };

  async function guardar(evento) {
    evento.preventDefault();
    if (!valores.nombre.trim()) {
      setErrores({ nombre: ['Escribe el nombre.'] });
      return;
    }
    const datos = {
      nombre: valores.nombre.trim(), genero: valores.genero.trim(), imagen_url: valores.imagen_url.trim(),
      wikipedia: valores.wikipedia.trim(),
      enlaces: Object.fromEntries(REDES.map(([tipo]) => [tipo, (valores.enlaces[tipo] ?? '').trim()]).filter(([, url]) => url)),
    };
    // La descripción solo se manda si cambió: así una que vino de Wikipedia no queda "fija" sin querer.
    if (nuevo || valores.descripcion !== artista.descripcion) datos.descripcion = valores.descripcion.trim();
    setEnviando(true);
    try {
      const guardado = nuevo ? await crearArtistaEdicion(datos) : await editarArtista(artista.slug, datos);
      avisar(nuevo ? `Agregaste a ${guardado.nombre}` : 'Perfil actualizado');
      navegar(`/artista/${guardado.slug}`);
    } catch (error) {
      setErrores({ ...error.campos, general: Object.keys(error.campos ?? {}).length ? 'Revisa los campos marcados.' : error.message });
      setEnviando(false);
    }
  }

  const campo = (nombre, etiqueta, props = {}, ayuda = null) => (
    <div className="campo">
      <label htmlFor={`${id}-${nombre}`}>{etiqueta}</label>
      <input className="entrada" id={`${id}-${nombre}`} value={valores[nombre]} onChange={poner(nombre)} aria-invalid={Boolean(errores[nombre])} {...props} />
      {ayuda && <p className="letra-chica" style={{ margin: 0 }}>{ayuda}</p>}
      {errores[nombre] && <p className="error">{primero(errores[nombre])}</p>}
    </div>
  );

  return (
    <form className="formulario" onSubmit={guardar} noValidate aria-busy={enviando}>
      <h1 className="cartel" id="titulo-vista" tabIndex={-1}>{nuevo ? 'Agregar artista' : `Editar: ${artista.nombre}`}</h1>
      {nuevo && <p className="apagado">Para artistas que aún no están en la cartelera. Tendrán su perfil aunque no tengan fechas.</p>}
      {errores.general && <p className="error" role="alert">{errores.general}</p>}

      <div className="perfil-edicion">
        <div className="perfil-edicion__foto" aria-hidden="true">
          <Cartel imagen={valores.imagen_url.trim()} semilla={valores.nombre || 'nuevo'} tamano={300} />
        </div>
        <div className="rejilla-dos">
          {campo('nombre', 'Nombre', { maxLength: 200 })}
          {campo('genero', 'Género', { maxLength: 60, placeholder: 'Ej. Rock' })}
          {campo('imagen_url', 'Imagen (URL)', { type: 'url', placeholder: 'https://…' }, 'Sin imagen se dibuja un cartel con sus colores.')}
        </div>
      </div>

      <div className="campo">
        <label htmlFor={`${id}-descripcion`}>Descripción</label>
        <textarea
          className="entrada" id={`${id}-descripcion`} value={valores.descripcion} onChange={poner('descripcion')} maxLength={3000}
          placeholder="Quién es, de dónde viene, qué toca…"
        />
        <p className="letra-chica" style={{ margin: 0 }}>
          {artista?.descripcion_fuente
            ? 'Esta salió de Wikipedia. Si la cambias, quedará la tuya y ya no se actualizará sola.'
            : 'Si la dejas vacía, la buscamos en Wikipedia (esta noche, o al momento si pegas el artículo abajo).'}
        </p>
      </div>
      {campo('wikipedia', 'Artículo de Wikipedia (opcional)', { type: 'url', placeholder: 'https://es.wikipedia.org/wiki/…' }, 'Úsalo si la descripción automática es de otra persona o no aparece.')}

      <fieldset className="grupo">
        <legend>Redes y sitio oficial</legend>
        <div className="rejilla-dos">
          {REDES.map(([tipo, nombre]) => (
            <div className="campo" key={tipo}>
              <label htmlFor={`${id}-${tipo}`}>{nombre}</label>
              <input className="entrada" id={`${id}-${tipo}`} type="url" placeholder="https://…" value={valores.enlaces[tipo] ?? ''} onChange={ponerEnlace(tipo)} />
            </div>
          ))}
        </div>
        {errores.enlaces && <p className="error">{primero(errores.enlaces)}</p>}
      </fieldset>

      <div className="formulario__pie">
        <button type="submit" className="boton" disabled={enviando}>{enviando ? 'Guardando…' : nuevo ? 'Agregar artista' : 'Guardar cambios'}</button>
        <Link className="enlace" to={nuevo ? '/editar/artistas' : `/artista/${artista.slug}`}>Cancelar</Link>
      </div>
    </form>
  );
}

function Editar({ slug }) {
  const { datos, cargando, error, reintentar } = usarPeticion((signal) => obtenerArtistaEdicion(slug, signal), [slug]);
  if (cargando) return <p role="status" className="apagado">Cargando…</p>;
  if (error?.estado === 404) return <PaginaNoEncontrada mensaje="No encontramos a este artista." />;
  if (error) return <MensajeError error={error} alReintentar={reintentar} />;
  return <Formulario artista={datos} />;
}

/** /editar/artista/nuevo y /editar/artista/:slug */
export default function PaginaEditarArtista() {
  const { slug } = useParams();
  const nuevo = slug === 'nuevo';
  usarTituloDocumento(nuevo ? 'Agregar artista · ¿Quién toca?' : 'Editar artista · ¿Quién toca?');
  return (
    <SoloEditores>
      <div className="centro edicion">
        <Link className="volver" to={nuevo ? '/editar/artistas' : `/artista/${slug}`}><Icono nombre="atras" />Volver</Link>
        {nuevo ? <Formulario /> : <Editar slug={slug} />}
      </div>
    </SoloEditores>
  );
}
