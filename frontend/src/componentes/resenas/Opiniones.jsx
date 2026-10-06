import { useState } from 'react';
import { Link, useLocation } from 'react-router';
import { obtenerMisResenas } from '../../api.js';
import { usarPeticion } from '../../hooks/usarPeticion.js';
import { usarResenas } from '../../hooks/usarResenas.js';
import { usarSesion } from '../../hooks/usarSesion.js';
import { avisar } from '../AvisoFlotante.jsx';
import MensajeError from '../MensajeError.jsx';
import FormularioResena from './FormularioResena.jsx';
import ResumenCalificaciones from './ResumenCalificaciones.jsx';
import TarjetaResena from './TarjetaResena.jsx';
import './Resenas.css';

/**
 * Las fechas que se pueden reseñar desde esta página, la más reciente primero.
 * En un concierto pasado, solo esa noche (la lista muestra solo sus reseñas).
 */
function fechasResenables(concierto, yaEmpezo) {
  const candidatas = yaEmpezo ? [concierto] : concierto.otras_fechas;
  return candidatas
    .filter((f) => f.se_puede_resenar)
    .map((f) => ({ slug: f.slug, fecha_hora: f.fecha_hora, ciudad: f.recinto.ciudad.nombre, recinto: f.recinto.nombre }))
    .sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora));
}

/**
 * Concierto futuro: lo que dijeron de las fechas pasadas del artista.
 * Concierto pasado: las reseñas de esa noche.
 * alCambiarCalificaciones: para que el promedio se actualice tras publicar, editar o borrar.
 */
export default function Opiniones({ concierto, alCambiarCalificaciones }) {
  const usuario = usarSesion();
  const ubicacion = useLocation();
  const [escribiendo, setEscribiendo] = useState(false);
  const artista = concierto.artista.nombre;
  const esPasado = new Date(concierto.fecha_hora) <= new Date(); // ya empezó (aunque se haya cancelado)
  const resenas = usarResenas(esPasado ? { concierto: concierto.slug } : { artista: concierto.artista.slug }, usuario?.id);
  const mias = usarPeticion(
    (signal) => (usuario ? obtenerMisResenas(signal) : Promise.resolve([])),
    [usuario?.id],
  );

  const yaResenadas = new Set((mias.datos ?? []).map((m) => m.concierto));
  const resenables = fechasResenables(concierto, esPasado);
  const disponibles = resenables.filter((f) => !yaResenadas.has(f.slug));

  function alPublicar(resena) {
    resenas.agregar(resena);
    mias.refrescar();
    alCambiarCalificaciones();
    setEscribiendo(false);
    avisar('Reseña publicada');
  }

  let invitacion = null;
  if (resenables.length && !escribiendo) {
    if (!usuario) {
      invitacion = (
        <div className="invita">
          <p>{esPasado ? '¿Fuiste a este concierto?' : `¿Ya viste a ${artista} en vivo?`}</p>
          <Link className="boton" to="/entrar" state={{ desde: ubicacion.pathname }}>Inicia sesión para reseñar</Link>
        </div>
      );
    } else if (!mias.cargando && disponibles.length) {
      invitacion = (
        <div className="invita">
          <p>{esPasado ? '¿Fuiste a este concierto?' : `¿Ya viste a ${artista} en vivo?`}</p>
          <button type="button" className="boton" onClick={() => setEscribiendo(true)}>Escribir reseña</button>
        </div>
      );
    }
  }

  return (
    <section className="opiniones" aria-labelledby="t-opiniones">
      <div className="centro">
        <h2 className="cartel t-seccion" id="t-opiniones">
          {esPasado ? 'Así estuvo este concierto' : `Así estuvo ${artista} en otras fechas`}
        </h2>
        <p className="apagado" style={{ marginTop: 10, maxWidth: '36em' }}>
          {esPasado
            ? 'Reseñas de quienes confirmaron que asistieron.'
            : 'Como este concierto aún no pasa, te mostramos lo que dijeron quienes fueron a las fechas anteriores.'}
        </p>
        <div className="opiniones__cuerpo">
          <ResumenCalificaciones
            artista={artista}
            calificacion={concierto.calificacion_artista}
            recinto={concierto.recinto.nombre}
            calificacionRecinto={concierto.calificacion_recinto}
            hayFechasPasadas={resenables.length > 0}
          />
          <div className="opiniones__lista">
            {invitacion}
            {escribiendo && (
              <FormularioResena fechas={disponibles} alGuardar={alPublicar} alCancelar={() => setEscribiendo(false)} />
            )}
            {resenas.lista.map((resena) => (
              <TarjetaResena
                key={resena.id}
                resena={resena}
                alCambiar={(nueva) => { resenas.reemplazar(nueva); alCambiarCalificaciones(); }}
                alBorrar={(id) => { resenas.quitar(id); mias.refrescar(); alCambiarCalificaciones(); }}
              />
            ))}
            {resenas.cargando && <p role="status" className="apagado">Cargando reseñas…</p>}
            {resenas.error && <MensajeError error={resenas.error} alReintentar={resenas.reintentar} />}
            {!resenas.cargando && !resenas.error && !resenas.lista.length && !escribiendo && (
              <p className="apagado">{esPasado ? 'Todavía nadie ha reseñado este concierto.' : 'Todavía no hay reseñas de sus fechas anteriores.'}</p>
            )}
            {resenas.hayMas && !resenas.cargando && (
              <button type="button" className="boton boton--linea" style={{ alignSelf: 'flex-start' }} onClick={resenas.verMas}>
                Ver más reseñas
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
