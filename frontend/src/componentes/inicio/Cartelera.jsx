import { plural } from '../../utilidades/texto.js';
import MensajeError from '../MensajeError.jsx';
import Boleto, { BoletosCargando } from './Boleto.jsx';

function titulo(cartelera, ciudad) {
  if (cartelera.cargando && !cartelera.conciertos.length) return 'Buscando conciertos…';
  if (cartelera.error) return 'No pudimos cargar la cartelera';
  if (!cartelera.total) return `Sin conciertos en ${ciudad.nombre}`;
  return `${plural(cartelera.total, 'concierto', 'conciertos')} en ${ciudad.nombre}`;
}

/** La lista de boletos con su encabezado, el orden y todos sus estados. */
export default function Cartelera({ ciudad, cartelera, orden, alCambiarOrden, hayFiltros, alQuitarFiltros }) {
  const { conciertos, cargando, error, hayMas, cargandoMas, errorMas, cargarMas, reintentar } = cartelera;

  let contenido;
  if (error) {
    contenido = <MensajeError error={error} alReintentar={reintentar} />;
  } else if (cargando && !conciertos.length) {
    contenido = <BoletosCargando />;
  } else if (!conciertos.length) {
    // Dos casos distintos: la ciudad no tiene nada, o los filtros no dejan ver nada.
    const hayOtros = ciudad.conciertos_proximos > 0;
    contenido = (
      <div className="vacio">
        <p>
          {hayOtros && hayFiltros
            ? `Ningún concierto de ${ciudad.nombre} coincide con tu búsqueda y esas fechas.`
            : `Todavía no hay conciertos anunciados en ${ciudad.nombre}. Prueba con otra ciudad.`}
        </p>
        {hayOtros && hayFiltros && (
          <button type="button" className="boton boton--linea" onClick={alQuitarFiltros}>Quitar filtros</button>
        )}
      </div>
    );
  } else {
    contenido = (
      <>
        {/* aria-busy: mientras se actualiza, los resultados viejos se ven atenuados */}
        <ol className={`boletos${cargando ? ' boletos--actualizando' : ''}`} aria-busy={cargando}>
          {conciertos.map((concierto) => <Boleto key={concierto.slug} concierto={concierto} />)}
        </ol>
        {errorMas && <div className="mas"><MensajeError error={errorMas} /></div>}
        {hayMas && (
          <div className="mas">
            <button type="button" className="boton boton--linea" onClick={cargarMas} disabled={cargandoMas}>
              {cargandoMas ? 'Cargando…' : 'Ver más conciertos'}
            </button>
          </div>
        )}
      </>
    );
  }

  return (
    <section className="cartelera" aria-labelledby="cuenta">
      <div className="centro">
        <div className="encabezado">
          {/* aria-live: el lector de pantalla anuncia el nuevo total al filtrar */}
          <h2 className="cartel t-seccion" id="cuenta" aria-live="polite">{titulo(cartelera, ciudad)}</h2>
          <div className="orden">
            <label htmlFor="orden">Ordenar por</label>
            <select id="orden" value={orden} onChange={(evento) => alCambiarOrden(evento.target.value)}>
              <option value="fecha">Fecha más cercana</option>
              <option value="nota">Mejor reseñados</option>
              <option value="precio">Precio más bajo</option>
            </select>
          </div>
        </div>
        {contenido}
      </div>
    </section>
  );
}
