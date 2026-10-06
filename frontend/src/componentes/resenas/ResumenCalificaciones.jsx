import { plural } from '../../utilidades/texto.js';

function Barras({ filas }) {
  const conDato = filas.filter(([, valor]) => valor != null);
  if (!conDato.length) return null;
  return (
    <div className="barras">
      {conDato.map(([nombre, valor]) => (
        <div className="barra-fila" key={nombre}>
          <span>{nombre}</span>
          <i aria-hidden="true"><b style={{ width: `${(valor / 5) * 100}%` }} /></i>
          <strong>{valor.toFixed(1)}<span className="solo-lector"> de 5</span></strong>
        </div>
      ))}
    </div>
  );
}

/** El promedio grande del artista, sus barras por aspecto y la nota del recinto. */
export default function ResumenCalificaciones({ artista, calificacion, recinto, calificacionRecinto, hayFechasPasadas }) {
  return (
    <div>
      {calificacion.total ? (
        <>
          <p className="promedio">
            <b>{calificacion.promedio.toFixed(1)}</b>
            <span className="apagado">de 5, con {plural(calificacion.total, 'reseña', 'reseñas')}</span>
          </p>
          <h3 className="subtitulo">{artista} en vivo</h3>
          <Barras filas={[['Show en vivo', calificacion.show], ['Sonido', calificacion.sonido], ['Puntualidad', calificacion.puntualidad]]} />
        </>
      ) : (
        <>
          <p className="subtitulo" style={{ marginTop: 0 }}>{artista} todavía no tiene reseñas</p>
          <p className="apagado">
            {hayFechasPasadas ? 'Sé la primera persona en contar cómo estuvo.' : 'Las reseñas se abren cuando pase su primera fecha.'}
          </p>
        </>
      )}
      <h3 className="subtitulo">El recinto: {recinto}</h3>
      {calificacionRecinto.total ? (
        <>
          <Barras filas={[['Calificación', calificacionRecinto.promedio]]} />
          <p className="letra-chica">Según {plural(calificacionRecinto.total, 'reseña', 'reseñas')} de conciertos en este lugar.</p>
        </>
      ) : (
        <p className="apagado">Todavía nadie ha calificado este recinto.</p>
      )}
    </div>
  );
}
