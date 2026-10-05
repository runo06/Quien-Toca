import { Navigate } from 'react-router';
import MensajeError from '../componentes/MensajeError.jsx';
import { leerCiudadGuardada, usarCiudades } from '../contexto/ciudades.jsx';

/** "/" lleva a la última ciudad visitada o, si no hay, a la predeterminada (CDMX). */
export default function RedirigirACiudad() {
  const { datos, cargando, error, reintentar } = usarCiudades();

  if (error) return <div className="centro pagina-estado"><MensajeError error={error} alReintentar={reintentar} /></div>;
  if (cargando) return <div className="centro pagina-estado"><p role="status" className="apagado">Cargando la cartelera…</p></div>;

  const guardada = leerCiudadGuardada();
  const destino = datos.find((c) => c.slug === guardada) ?? datos.find((c) => c.es_predeterminada) ?? datos[0];
  // replace: "/" no queda en el historial, así "atrás" no regresa a una página que redirige.
  return <Navigate to={`/${destino.slug}`} replace />;
}
