import { useCallback, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import FranjaNoVendemos from '../componentes/FranjaNoVendemos.jsx';
import MensajeError from '../componentes/MensajeError.jsx';
import Buscador from '../componentes/inicio/Buscador.jsx';
import Cartelera from '../componentes/inicio/Cartelera.jsx';
import FichasFecha from '../componentes/inicio/FichasFecha.jsx';
import SelectorCiudad from '../componentes/inicio/SelectorCiudad.jsx';
import { guardarCiudad, usarCiudades } from '../contexto/ciudades.jsx';
import { usarCartelera } from '../hooks/usarCartelera.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import { RANGO_POR_DEFECTO, esRangoValido, rangoDeFechas } from '../utilidades/rangos.js';
import PaginaNoEncontrada from './PaginaNoEncontrada.jsx';
import './PaginaInicio.css';

/**
 * Inicio de una ciudad: /cdmx?q=rock&fechas=30-dias&orden=precio
 * Los filtros viven en la dirección (no en useState): así el enlace se puede
 * compartir y "atrás" o recargar conservan la búsqueda.
 */
export default function PaginaInicio() {
  const { ciudad: slugCiudad } = useParams();
  const [parametros, setParametros] = useSearchParams();
  const navegar = useNavigate();
  const ciudades = usarCiudades();

  const texto = parametros.get('q') ?? '';
  const fechas = esRangoValido(parametros.get('fechas')) ? parametros.get('fechas') : RANGO_POR_DEFECTO;
  const orden = parametros.get('orden') === 'precio' ? 'precio' : 'fecha';
  const { desde, hasta } = rangoDeFechas(fechas);

  const ciudad = ciudades.datos?.find((c) => c.slug === slugCiudad);
  const cartelera = usarCartelera({ ciudad: slugCiudad, q: texto.trim(), desde, hasta, orden });

  usarTituloDocumento(ciudad ? `¿Quién toca en ${ciudad.nombre}?` : '¿Quién toca?');
  useEffect(() => {
    if (ciudad) guardarCiudad(ciudad.slug); // la próxima visita a "/" abre esta ciudad
  }, [ciudad]);

  // Cambia un parámetro de la dirección. Si queda en su valor por defecto, se quita
  // para que el enlace quede limpio. Al teclear se reemplaza la entrada del historial
  // en vez de agregar una por cada búsqueda.
  const cambiarParametro = useCallback((nombre, valor, porDefecto = '') => {
    setParametros((actuales) => {
      const nuevos = new URLSearchParams(actuales);
      if (!valor || valor === porDefecto) nuevos.delete(nombre);
      else nuevos.set(nombre, valor);
      return nuevos;
    }, { replace: nombre === 'q' });
  }, [setParametros]);

  const cambiarTexto = useCallback((valor) => cambiarParametro('q', valor), [cambiarParametro]);

  // Los returns tempranos van después de todos los hooks: React exige el mismo orden en cada render.
  if (ciudades.error) {
    return <div className="centro pagina-estado"><MensajeError error={ciudades.error} alReintentar={ciudades.reintentar} /></div>;
  }
  if (ciudades.cargando) {
    return <div className="centro pagina-estado"><p role="status" className="apagado">Cargando la cartelera…</p></div>;
  }
  if (!ciudad) return <PaginaNoEncontrada />;

  function elegirCiudad(slug) {
    const busqueda = parametros.toString();
    // conservarFoco: el selector devuelve el foco a su botón; App no debe moverlo.
    navegar({ pathname: `/${slug}`, search: busqueda ? `?${busqueda}` : '' }, { state: { conservarFoco: true } });
  }

  function quitarFiltros() {
    setParametros((actuales) => {
      const nuevos = new URLSearchParams(actuales);
      nuevos.delete('q');
      nuevos.delete('fechas');
      return nuevos;
    });
    document.getElementById('buscar')?.focus();
  }

  return (
    <>
      <section className="portada">
        <div className="centro">
          <SelectorCiudad ciudades={ciudades.datos} actual={ciudad} alElegir={elegirCiudad} />
          <p className="bajada">
            Todos los conciertos de tu ciudad en un solo lugar, con el enlace a la boletera oficial y reseñas de
            quienes ya fueron.
          </p>
          <div className="filtros">
            <Buscador valor={texto} alCambiar={cambiarTexto} />
            <FichasFecha valor={fechas} alCambiar={(valor) => cambiarParametro('fechas', valor, RANGO_POR_DEFECTO)} />
          </div>
        </div>
      </section>
      <Cartelera
        ciudad={ciudad}
        cartelera={cartelera}
        orden={orden}
        alCambiarOrden={(valor) => cambiarParametro('orden', valor, 'fecha')}
        hayFiltros={Boolean(texto.trim()) || fechas !== RANGO_POR_DEFECTO}
        alQuitarFiltros={quitarFiltros}
      />
      <FranjaNoVendemos />
    </>
  );
}
