import { dinero } from '../../utilidades/texto.js';
import Icono from '../Icono.jsx';

/** "Dónde comprar": enlace a la boletera oficial y, si hay, la tabla de precios por zona. */
export default function Taquilla({ concierto }) {
  const { url_boletos, precio_desde, moneda, precios, estado, ya_paso } = concierto;
  const sePuedeComprar = !ya_paso && estado !== 'cancelado';

  let detalle;
  if (ya_paso) detalle = 'Este concierto ya pasó.';
  else if (estado === 'cancelado') detalle = 'Este concierto fue cancelado.';
  else if (precio_desde != null) detalle = `Desde ${dinero(precio_desde, moneda)} más cargos por servicio`;
  else detalle = 'Consulta precios y disponibilidad en la boletera.';

  return (
    <section className={`taquilla${precios.length ? '' : ' taquilla--sola'}`} aria-labelledby="t-comprar">
      <div className="taquilla__venta">
        <h2 className="cartel" id="t-comprar">Dónde comprar</h2>
        <div className="opcion">
          <p>
            <strong>Boletera oficial</strong>
            <span>{detalle}</span>
          </p>
          {sePuedeComprar && (
            // rel="noopener noreferrer": la página externa no puede controlar esta pestaña.
            <a className="boton" href={url_boletos} target="_blank" rel="noopener noreferrer">
              Ir a comprar
              <Icono nombre="fuera" />
              <span className="solo-lector"> (se abre en otra pestaña)</span>
            </a>
          )}
        </div>
      </div>
      {precios.length > 0 && (
        <div className="taquilla__zonas">
          <table className="zonas">
            <caption>Precios por zona</caption>
            <tbody>
              {precios.map((p) => (
                <tr key={p.zona}>
                  <th scope="row">{p.zona}</th>
                  <td>{dinero(p.precio, moneda)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="letra-chica">Precios de referencia. Confírmalos en la boletera antes de pagar.</p>
        </div>
      )}
    </section>
  );
}
