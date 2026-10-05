import { RANGOS } from '../../utilidades/rangos.js';

/** Fichas de rango de fechas. aria-pressed le dice al lector de pantalla cuál está activa. */
export default function FichasFecha({ valor, alCambiar }) {
  return (
    <div className="campo">
      <span className="etiqueta" id="et-fechas">Fechas</span>
      <div className="fichas" role="group" aria-labelledby="et-fechas">
        {RANGOS.map((rango) => (
          <button
            key={rango.valor}
            type="button"
            className="ficha"
            aria-pressed={rango.valor === valor}
            onClick={() => alCambiar(rango.valor)}
          >
            {rango.etiqueta}
          </button>
        ))}
      </div>
    </div>
  );
}
