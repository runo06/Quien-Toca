import { obtenerResenas } from '../../api.js';
import { usarPeticion } from '../../hooks/usarPeticion.js';
import TarjetaResena from '../resenas/TarjetaResena.jsx';
import '../resenas/Resenas.css';

/** "Lo que dicen quienes ya fueron": las 3 reseñas que más le han servido a la gente en esta ciudad. */
export default function VocesDestacadas({ ciudad }) {
  const { datos } = usarPeticion((signal) => obtenerResenas({ ciudad: ciudad.slug }, signal), [ciudad.slug]);
  const destacadas = datos?.resultados.slice(0, 3) ?? [];
  if (!destacadas.length) return null; // sin reseñas todavía (o sin respuesta): la sección no aparece

  return (
    <section className="voces" aria-labelledby="t-voces">
      <div className="centro">
        <h2 className="cartel t-seccion" id="t-voces">Lo que dicen quienes ya fueron</h2>
        <p className="apagado" style={{ marginTop: 10, maxWidth: '36em' }}>
          Solo pueden reseñar las personas que confirman que asistieron al concierto.
        </p>
        <div className="voces__lista">
          {destacadas.map((resena) => <TarjetaResena key={resena.id} resena={resena} conArtista />)}
        </div>
      </div>
    </section>
  );
}
