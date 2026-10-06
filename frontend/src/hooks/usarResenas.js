import { useCallback, useEffect, useState } from 'react';
import { obtenerResenas } from '../api.js';

/**
 * Lista de reseñas que crece con "Ver más". filtros: { artista } o { concierto } o { ciudad }.
 * Se vuelve a pedir si cambian los filtros o quién tiene la sesión (cambian "Tu reseña" y "Me sirvió").
 */
export function usarResenas(filtros, idUsuario) {
  const clave = JSON.stringify(filtros);
  const [estado, setEstado] = useState({ lista: [], total: 0, pagina: 1, hayMas: false, cargando: true, error: null });
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    const control = new AbortController();
    setEstado({ lista: [], total: 0, pagina: 1, hayMas: false, cargando: true, error: null });
    obtenerResenas({ ...JSON.parse(clave), pagina: 1 }, control.signal)
      .then((datos) => setEstado({
        lista: datos.resultados, total: datos.total, pagina: 1, hayMas: Boolean(datos.siguiente), cargando: false, error: null,
      }))
      .catch((error) => {
        if (error.name !== 'AbortError') setEstado((e) => ({ ...e, cargando: false, error }));
      });
    return () => control.abort();
  }, [clave, idUsuario, intento]);

  const verMas = useCallback(async () => {
    setEstado((e) => ({ ...e, cargando: true }));
    try {
      const siguiente = estado.pagina + 1;
      const datos = await obtenerResenas({ ...JSON.parse(clave), pagina: siguiente });
      setEstado((e) => {
        // Sin repetidas: si alguien publicó mientras tanto, el orden pudo moverse.
        const vistas = new Set(e.lista.map((r) => r.id));
        return {
          ...e, lista: [...e.lista, ...datos.resultados.filter((r) => !vistas.has(r.id))],
          pagina: siguiente, hayMas: Boolean(datos.siguiente), cargando: false,
        };
      });
    } catch (error) {
      setEstado((e) => ({ ...e, cargando: false, error }));
    }
  }, [clave, estado.pagina]);

  // Cambios hechos aquí mismo, sin volver a pedir la lista.
  const agregar = useCallback((resena) => setEstado((e) => ({ ...e, lista: [resena, ...e.lista], total: e.total + 1 })), []);
  const reemplazar = useCallback((resena) => setEstado((e) => ({ ...e, lista: e.lista.map((r) => (r.id === resena.id ? resena : r)) })), []);
  const quitar = useCallback((id) => setEstado((e) => ({ ...e, lista: e.lista.filter((r) => r.id !== id), total: e.total - 1 })), []);
  const reintentar = useCallback(() => setIntento((n) => n + 1), []);

  return { ...estado, verMas, agregar, reemplazar, quitar, reintentar };
}
