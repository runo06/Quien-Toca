import { Link, useNavigate } from 'react-router';
import { buscarArtistasEdicion } from '../../api.js';
import Autocompletar from './Autocompletar.jsx';

/** Agregar un artista nuevo o buscar uno para editar su perfil. */
export default function GestionArtistas() {
  const navegar = useNavigate();
  return (
    <div className="formulario">
      <h2 className="cartel">Artistas</h2>
      <p className="apagado">
        Agrega artistas que aún no están en la cartelera (tendrán su perfil aunque no tengan fechas) o corrige
        la descripción, la imagen y las redes de los que ya están.
      </p>
      <div><Link className="boton" to="/editar/artista/nuevo">+ Agregar artista</Link></div>
      <div style={{ maxWidth: 520 }}>
        <Autocompletar
          etiqueta="Editar el perfil de…" valor={null} placeholder="Busca por nombre"
          etiquetaDe={(a) => a.nombre} buscar={buscarArtistasEdicion}
          alElegir={(artista) => artista && navegar(`/editar/artista/${artista.slug}`)}
        />
      </div>
    </div>
  );
}
