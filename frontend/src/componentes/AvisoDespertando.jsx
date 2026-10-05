import { useSyncExternalStore } from 'react';
import { hayPeticionesLentas, suscribirseALentitud } from '../api.js';

/**
 * Aviso fijo abajo de la pantalla mientras alguna petición tarda de más:
 * casi siempre es el servidor gratuito despertando.
 *
 * El contenedor con role="status" existe siempre y solo cambia su contenido:
 * así el lector de pantalla anuncia el aviso cuando aparece.
 */
export default function AvisoDespertando() {
  const lento = useSyncExternalStore(suscribirseALentitud, hayPeticionesLentas);

  return (
    <div className="despertando" role="status">
      {lento && (
        <div className="despertando__caja">
          <span className="despertando__punto" aria-hidden="true" />
          <p>
            <strong>Despertando el servidor…</strong> Cuando nadie lo usa se duerme y tarda
            hasta un minuto en volver. La página carga sola, no hace falta recargar.
          </p>
        </div>
      )}
    </div>
  );
}
