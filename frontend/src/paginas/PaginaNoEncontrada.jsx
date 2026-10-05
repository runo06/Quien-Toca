import { Link } from 'react-router';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';

export default function PaginaNoEncontrada({ mensaje = 'La dirección no existe o el concierto ya no está en la cartelera.' }) {
  usarTituloDocumento('No encontramos esta página · ¿Quién toca?');
  return (
    <section className="centro pagina-estado">
      <h1 className="cartel t-seccion" id="titulo-vista" tabIndex={-1}>No encontramos esta página</h1>
      <p className="apagado" style={{ margin: '14px 0 24px', maxWidth: '34em' }}>{mensaje}</p>
      <Link className="boton" to="/">Ir a la cartelera</Link>
    </section>
  );
}
