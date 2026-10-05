import { Link, useLocation } from 'react-router';
import { fechaCorta } from '../../utilidades/fechas.js';
import { dinero } from '../../utilidades/texto.js';

/** Las fechas del mismo artista; las pasadas en gris y la actual marcada. */
export default function OtrasFechas({ concierto }) {
  const ubicacion = useLocation();
  if (!concierto.otras_fechas.length) return null;

  // Se mezcla el concierto actual con los demás y se ordena por fecha.
  const fechas = [...concierto.otras_fechas, { ...concierto, actual: true }].sort(
    (a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora),
  );

  return (
    <section className="fechas" aria-labelledby="t-fechas">
      <h2 className="cartel" id="t-fechas">Más fechas de {concierto.artista.nombre}</h2>
      <ol className="fechas__lista">
        {fechas.map((fecha) => {
          const dia = <span className="parada__dia">{fechaCorta(fecha.fecha_hora)}</span>;
          const ciudad = <strong>{fecha.recinto.ciudad.nombre}</strong>;

          if (fecha.actual) {
            return (
              <li key={fecha.slug}>
                <span className="parada" aria-current="true">
                  {dia}<span>{ciudad}<span>Estás viendo esta fecha</span></span>
                </span>
              </li>
            );
          }
          if (fecha.ya_paso) {
            return (
              <li key={fecha.slug}>
                <span className="parada parada--pasada">
                  {dia}<span>{ciudad}<span>Ya pasó</span></span>
                </span>
              </li>
            );
          }
          return (
            <li key={fecha.slug}>
              {/* Se pasa el "desde" original para que volver siga llevando a la cartelera. */}
              <Link className="parada" to={`/concierto/${fecha.slug}`} state={ubicacion.state}>
                {dia}
                <span>
                  {ciudad}
                  <span>{fecha.precio_desde != null ? `Desde ${dinero(fecha.precio_desde, fecha.moneda)}` : fecha.recinto.nombre}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
