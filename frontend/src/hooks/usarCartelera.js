import { useCallback, useEffect, useRef, useState } from 'react';
import { obtenerConciertos } from '../api.js';

const INICIAL = {
  conciertos: [],
  total: 0,
  pagina: 1,
  hayMas: false,
  cargando: true,
  cargandoMas: false,
  error: null,
  errorMas: null,
};

/**
 * La lista de conciertos con "Ver más": cuando cambian los filtros empieza de
 * nuevo en la página 1; cargarMas() agrega la página siguiente al final.
 */
export function usarCartelera({ ciudad, q, desde, hasta, orden }) {
  const [estado, setEstado] = useState(INICIAL);
  const [intento, setIntento] = useState(0);
  // Cada búsqueda nueva tiene un número. Si llega tarde la respuesta de un
  // "Ver más" de una búsqueda anterior, se descarta.
  const busqueda = useRef(0);

  useEffect(() => {
    const control = new AbortController();
    const esta = ++busqueda.current;
    // Se conservan los resultados anteriores mientras llegan los nuevos (se ven atenuados).
    setEstado((anterior) => ({ ...anterior, cargando: true, error: null, errorMas: null }));
    obtenerConciertos({ ciudad, q, desde, hasta, orden }, control.signal)
      .then((datos) => {
        if (esta !== busqueda.current) return;
        setEstado({
          ...INICIAL,
          cargando: false,
          conciertos: datos.resultados,
          total: datos.total,
          hayMas: Boolean(datos.siguiente),
        });
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setEstado((anterior) => ({ ...anterior, cargando: false, error }));
      });
    return () => control.abort();
  }, [ciudad, q, desde, hasta, orden, intento]);

  const cargarMas = useCallback(async () => {
    const esta = busqueda.current;
    const siguiente = estado.pagina + 1;
    setEstado((anterior) => ({ ...anterior, cargandoMas: true, errorMas: null }));
    try {
      const datos = await obtenerConciertos({ ciudad, q, desde, hasta, orden, pagina: siguiente });
      if (esta !== busqueda.current) return;
      setEstado((anterior) => ({
        ...anterior,
        cargandoMas: false,
        pagina: siguiente,
        total: datos.total,
        conciertos: [...anterior.conciertos, ...datos.resultados],
        hayMas: Boolean(datos.siguiente),
      }));
    } catch (error) {
      if (esta !== busqueda.current) return;
      setEstado((anterior) => ({ ...anterior, cargandoMas: false, errorMas: error }));
    }
  }, [ciudad, q, desde, hasta, orden, estado.pagina]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);

  return { ...estado, cargarMas, reintentar };
}
