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
export default function ResumenCalificaciones({ artista, calificacion, recinto, calificacionRecinto }) {
  return (
    <div>
      {calificacion.total > 0 && (
        <>
          <p className="promedio">
            <b>{calificacion.promedio.toFixed(1)}</b>
            <span className="apagado">de 5, con {plural(calificacion.total, 'reseña', 'reseñas')}</span>
          </p>
          <h3 className="subtitulo">{artista} en vivo</h3>
          <Barras filas={[['Show en vivo', calificacion.show], ['Sonido', calificacion.sonido], ['Puntualidad', calificacion.puntualidad]]} />
        </>
      )}
      {calificacionRecinto.total > 0 && (
        <>
          <h3 className="subtitulo">El recinto: {recinto}</h3>
          <Barras filas={[['Calificación', calificacionRecinto.promedio]]} />
          <p className="letra-chica">Según {plural(calificacionRecinto.total, 'reseña', 'reseñas')} de conciertos en este lugar.</p>
        </>
      )}
    </div>
  );
}
