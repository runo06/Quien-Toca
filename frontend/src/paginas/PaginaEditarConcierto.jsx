import { useId, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { buscarRecintosEdicion, editarConcierto, obtenerConciertoEdicion } from '../api.js';
import { avisar } from '../componentes/AvisoFlotante.jsx';
import Autocompletar from '../componentes/edicion/Autocompletar.jsx';
import Icono from '../componentes/Icono.jsx';
import MensajeError from '../componentes/MensajeError.jsx';
import { usarPeticion } from '../hooks/usarPeticion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import { SoloEditores } from './PaginaEditar.jsx';
import PaginaNoEncontrada from './PaginaNoEncontrada.jsx';
import '../componentes/edicion/Edicion.css';
import './PaginaCuenta.css';

const ZONA = 'America/Mexico_City';
const ESTADOS = [
  ['en_venta', 'En venta'], ['sin_venta', 'Sin venta'], ['pospuesto', 'Pospuesto'],
  ['reprogramado', 'Reprogramado'], ['cancelado', 'Cancelado'],
];
const primero = (lista) => [].concat(lista ?? [])[0];

/** "2026-12-12T21:00:00-06:00" -> { fecha: "2026-12-12", hora: "21:00" } en hora de México. */
function partes(iso, horaPorConfirmar) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: ZONA, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return { fecha: `${p.year}-${p.month}-${p.day}`, hora: horaPorConfirmar ? '' : `${p.hour}:${p.minute}` };
}

function Formulario({ concierto }) {
  const id = useId();
  const navegar = useNavigate();
  const bloqueados = new Set(concierto.campos_bloqueados);
  const inicial = partes(concierto.fecha_hora, concierto.hora_por_confirmar);
  const [valores, setValores] = useState({
    titulo: concierto.titulo, gira: concierto.gira, estado: concierto.estado, fecha: inicial.fecha, hora: inicial.hora,
    url_boletos: concierto.url_boletos, imagen_url: concierto.imagen_url, genero: concierto.genero,
    precio_desde: concierto.precio_desde ?? '', apertura_puertas: concierto.apertura_puertas?.slice(0, 5) ?? '',
    recinto: { id: concierto.recinto, nombre: concierto.recinto_nombre },
  });
  const [errores, setErrores] = useState({});
  const [enviando, setEnviando] = useState(false);
  const poner = (campo) => (e) => setValores((v) => ({ ...v, [campo]: e.target.value }));

  async function guardar(evento) {
    evento.preventDefault();
    const todo = {
      titulo: valores.titulo.trim(), gira: valores.gira.trim(), estado: valores.estado, fecha: valores.fecha,
      hora: valores.hora || null, url_boletos: valores.url_boletos.trim(), imagen_url: valores.imagen_url.trim(),
      genero: valores.genero.trim(), precio_desde: valores.precio_desde === '' ? null : valores.precio_desde,
      apertura_puertas: valores.apertura_puertas || null, recinto: valores.recinto?.id,
    };
    // Solo se mandan los campos que se pueden cambiar.
    const datos = Object.fromEntries(Object.entries(todo).filter(([campo]) => !bloqueados.has(campo)));
    setEnviando(true);
    setErrores({});
    try {
      await editarConcierto(concierto.slug, datos);
      avisar('Cambios guardados');
      navegar(`/concierto/${concierto.slug}`);
    } catch (error) {
      setErrores({ ...error.campos, general: Object.keys(error.campos ?? {}).length ? 'Revisa los campos marcados.' : error.message });
      setEnviando(false);
    }
  }

  const campo = (nombre, etiqueta, props = {}) => (
    <div className="campo">
      <label htmlFor={`${id}-${nombre}`}>{etiqueta}</label>
      <input className="entrada" id={`${id}-${nombre}`} value={valores[nombre]} onChange={poner(nombre)} disabled={bloqueados.has(nombre)} aria-invalid={Boolean(errores[nombre])} {...props} />
      {errores[nombre] && <p className="error">{primero(errores[nombre])}</p>}
    </div>
  );

  return (
    <form className="formulario" onSubmit={guardar} noValidate aria-busy={enviando}>
      <h1 className="cartel" id="titulo-vista" tabIndex={-1}>Editar: {concierto.artista}</h1>
      {bloqueados.size > 0 && (
        <p className="aviso-info">
          Este concierto viene de Ticketmaster: la fecha, el recinto, el estado y la boletera se actualizan solos cada noche.
          Aquí puedes cambiar la gira, el precio y la apertura de puertas.
        </p>
      )}
      {errores.general && <p className="error" role="alert">{errores.general}</p>}
      <div className="rejilla-dos">
        {campo('titulo', 'Título')}
        {campo('gira', 'Gira')}
        <div className="campo">
          <label htmlFor={`${id}-estado`}>Estado</label>
          <select className="entrada" id={`${id}-estado`} value={valores.estado} onChange={poner('estado')} disabled={bloqueados.has('estado')}>
            {ESTADOS.map(([valor, nombre]) => <option key={valor} value={valor}>{nombre}</option>)}
          </select>
        </div>
        {bloqueados.has('recinto') ? (
          <div className="campo">
            <label htmlFor={`${id}-recinto`}>Recinto</label>
            <input className="entrada" id={`${id}-recinto`} value={concierto.recinto_nombre} disabled readOnly />
          </div>
        ) : (
          <Autocompletar
            etiqueta="Recinto" valor={valores.recinto} etiquetaDe={(r) => r.nombre}
            buscar={(texto, signal) => buscarRecintosEdicion(texto, undefined, signal)}
            alElegir={(recinto) => setValores((v) => ({ ...v, recinto }))} error={primero(errores.recinto)}
          />
        )}
        {campo('fecha', 'Día', { type: 'date' })}
        {campo('hora', 'Hora (vacía = por confirmar)', { type: 'time' })}
        {campo('apertura_puertas', 'Apertura de puertas', { type: 'time' })}
        {campo('precio_desde', 'Precio desde', { type: 'number', min: 0, step: 1 })}
        {campo('url_boletos', 'Boletera', { type: 'url' })}
        {campo('imagen_url', 'Imagen (URL)', { type: 'url' })}
        {campo('genero', 'Género')}
      </div>
      <div className="formulario__pie">
        <button type="submit" className="boton" disabled={enviando}>{enviando ? 'Guardando…' : 'Guardar cambios'}</button>
        <Link className="enlace" to={`/concierto/${concierto.slug}`}>Cancelar</Link>
      </div>
    </form>
  );
}

function Contenido() {
  const { slug } = useParams();
  const { datos, cargando, error, reintentar } = usarPeticion((signal) => obtenerConciertoEdicion(slug, signal), [slug]);
  usarTituloDocumento('Editar concierto · ¿Quién toca?');
  if (cargando) return <div className="centro pagina-estado"><p role="status" className="apagado">Cargando…</p></div>;
  if (error?.estado === 404) return <PaginaNoEncontrada />;
  if (error) return <div className="centro pagina-estado"><MensajeError error={error} alReintentar={reintentar} /></div>;
  return (
    <div className="centro edicion">
      <Link className="volver" to={`/concierto/${slug}`}><Icono nombre="atras" />Volver al concierto</Link>
      <Formulario concierto={datos} />
    </div>
  );
}

/** /editar/concierto/:slug */
export default function PaginaEditarConcierto() {
  return <SoloEditores><Contenido /></SoloEditores>;
}
