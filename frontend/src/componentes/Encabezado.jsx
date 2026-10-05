import { Link } from 'react-router';
import './Encabezado.css';

export default function Encabezado() {
  return (
    <header className="barra">
      <div className="centro">
        <Link className="marca" to="/">¿Quién toca?</Link>
        <nav aria-label="Principal">
          <Link to="/">Cartelera</Link>
        </nav>
      </div>
    </header>
  );
}
