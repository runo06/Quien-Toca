import { useId, useState } from 'react';
import { Link } from 'react-router';
import { obtenerReportesEdicion, obtenerSugerenciasEdicion, revisarReporte, revisarSugerencia } from '../../api.js';
import { usarPeticion } from '../../hooks/usarPeticion.js';
import { fechaMedia, horaSimple } from '../../utilidades/fechas.js';
import { avisar } from '../AvisoFlotante.jsx';
import MensajeError from '../MensajeError.jsx';
import Estrellas from '../resenas/Estrellas.jsx';

function Sugerencia({ sugerencia, alResolver }) {
  const id = useId();
  const [artista, setArtista] = useState(sugerencia.artista);
  const [recinto, setRecinto] = useState(sugerencia.recinto);
  const [motivo, setMotivo] = useState('');
  const [rechazando, setRechazando] = useState(false);
  const [ocupado, setOcupado] = useState(false);

  async function resolver(accion) {
    setOcupado(true);
    try {
      const datos = accion === 'aprobar' ? { artista, recinto } : { motivo };
      const respuesta = await revisarSugerencia(sugerencia.id, accion, datos);
      avisar(accion === 'aprobar' ? `Aprobada: ${artista}` : 'Sugerencia rechazada');
      alResolver(sugerencia.id, { ...respuesta, artista }); // con el nombre ya corregido
    } catch (error) {
      avisar(error.message);
      setOcupado(false);
    }
  }

  return (
    <article className="tarjeta-revision">
      <p className="apagado">
        {sugerencia.ciudad} · {fechaMedia(`${sugerencia.fecha}T12:00:00`)}
        {sugerencia.hora ? `, ${horaSimple(sugerencia.hora)}` : ', hora por confirmar'} · sugirió {sugerencia.sugirio}
      </p>
      <div className="rejilla-dos">
        <div className="campo">
          <label htmlFor={`${id}-artista`}>Artista (corrígelo si hace falta)</label>
          <input className="entrada" id={`${id}-artista`} value={artista} onChange={(e) => setArtista(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor={`${id}-recinto`}>Recinto</label>
          <input className="entrada" id={`${id}-recinto`} value={recinto} onChange={(e) => setRecinto(e.target.value)} />
        </div>
      </div>
      <p>
        <a className="enlace" href={sugerencia.url_boletos} target="_blank" rel="noopener noreferrer">Revisar la boletera</a>
        {sugerencia.comentario && <span className="apagado"> · «{sugerencia.comentario}»</span>}
      </p>
      {rechazando ? (
        <div className="tarjeta-revision__acciones">
          <div className="campo" style={{ flex: '1 1 260px' }}>
            <label htmlFor={`${id}-motivo`}>Motivo (lo verá quien lo sugirió)</label>
            <input className="entrada" id={`${id}-motivo`} value={motivo} maxLength={300} onChange={(e) => setMotivo(e.target.value)} placeholder="Ej. No encontramos ese concierto" />
          </div>
          <button type="button" className="boton boton--chico" disabled={ocupado} onClick={() => resolver('rechazar')}>Rechazar</button>
          <button type="button" className="enlace" onClick={() => setRechazando(false)}>Cancelar</button>
        </div>
      ) : (
        <div className="tarjeta-revision__acciones">
          <button type="button" className="boton boton--chico" disabled={ocupado || !artista.trim() || !recinto.trim()} onClick={() => resolver('aprobar')}>
            Aprobar y publicar
          </button>
          <button type="button" className="boton boton--linea boton--chico" onClick={() => setRechazando(true)}>Rechazar…</button>
        </div>
      )}
    </article>
  );
}

export function RevisarSugerencias({ alCambiar }) {
  const { datos, cargando, error, reintentar } = usarPeticion(obtenerSugerenciasEdicion, []);
  const [resueltas, setResueltas] = useState({});

  if (cargando) return <p role="status" className="apagado">Cargando sugerencias…</p>;
  if (error) return <MensajeError error={error} alReintentar={reintentar} />;
  const pendientes = datos.filter((s) => !resueltas[s.id]);
  const aprobadas = datos.filter((s) => resueltas[s.id]?.concierto);

  return (
    <div className="revisiones">
      {aprobadas.map((s) => (
        <p key={s.id} className="aviso-ok" role="status">
          Publicado: <Link to={`/concierto/${resueltas[s.id].concierto}`}>{resueltas[s.id].artista}</Link>. Revisa que la imagen y los precios estén bien.
        </p>
      ))}
      {pendientes.length ? pendientes.map((s) => (
        <Sugerencia key={s.id} sugerencia={s} alResolver={(id, r) => { setResueltas((x) => ({ ...x, [id]: r })); alCambiar(); }} />
      )) : <div className="vacio"><p>No hay sugerencias pendientes.</p></div>}
    </div>
  );
}

function Reporte({ reporte, alResolver }) {
  const [ocupado, setOcupado] = useState(false);
  async function resolver(accion) {
    setOcupado(true);
    try {
      await revisarReporte(reporte.id, accion);
      avisar(accion === 'aceptar' ? 'Reseña oculta' : 'Reporte descartado');
      alResolver(reporte, accion);
    } catch (error) {
      avisar(error.message);
      setOcupado(false);
    }
  }
  const { concierto } = reporte;
  return (
    <article className="tarjeta-revision">
      <p className="apagado">
        <strong className="etiqueta-motivo">{reporte.motivo}</strong>
        {reporte.reportes_de_la_resena > 1 && ` · ${reporte.reportes_de_la_resena} reportes`} · reportó {reporte.reporto}
        {reporte.comentario && <> · «{reporte.comentario}»</>}
      </p>
      <blockquote className="cita-resena">
        <Estrellas valor={reporte.general} />
        <p>{reporte.texto}</p>
        <footer className="apagado">
          {reporte.autor} sobre <Link to={`/concierto/${concierto.slug}`}>{concierto.artista}</Link>, {concierto.ciudad}, {fechaMedia(concierto.fecha_hora)}
        </footer>
      </blockquote>
      <div className="tarjeta-revision__acciones">
        <button type="button" className="boton boton--chico" disabled={ocupado} onClick={() => resolver('aceptar')}>Ocultar la reseña</button>
        <button type="button" className="boton boton--linea boton--chico" disabled={ocupado} onClick={() => resolver('descartar')}>Está bien, descartar</button>
      </div>
    </article>
  );
}

export function RevisarReportes({ alCambiar }) {
  const { datos, cargando, error, reintentar } = usarPeticion(obtenerReportesEdicion, []);
  const [quitados, setQuitados] = useState(new Set());

  if (cargando) return <p role="status" className="apagado">Cargando reportes…</p>;
  if (error) return <MensajeError error={error} alReintentar={reintentar} />;
  const visibles = datos.filter((r) => !quitados.has(r.id));

  function alResolver(reporte, accion) {
    // Al ocultar, se van todos los reportes de esa misma reseña; al descartar, solo ese.
    const ids = accion === 'aceptar'
      ? datos.filter((r) => r.resena === reporte.resena).map((r) => r.id)
      : [reporte.id];
    setQuitados((q) => new Set([...q, ...ids]));
    alCambiar();
  }

  return (
    <div className="revisiones">
      {visibles.length ? visibles.map((r) => <Reporte key={r.id} reporte={r} alResolver={alResolver} />)
        : <div className="vacio"><p>No hay reportes pendientes.</p></div>}
    </div>
  );
}
