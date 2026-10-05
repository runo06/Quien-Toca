import { useCallback, useEffect, useState } from 'react';

/**
 * Hace una petición y lleva sus tres estados: cargando, error y datos.
 *
 * pedirDatos recibe una "señal" (AbortSignal). Si las dependencias cambian antes
 * de que llegue la respuesta, la petición anterior se cancela: así una respuesta
 * vieja nunca pisa a una nueva.
 */
export function usarPeticion(pedirDatos, dependencias) {
  const [estado, setEstado] = useState({ datos: null, cargando: true, error: null });
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    const control = new AbortController();
    setEstado({ datos: null, cargando: true, error: null });
    pedirDatos(control.signal)
      .then((datos) => setEstado({ datos, cargando: false, error: null }))
      .catch((error) => {
        if (error.name !== 'AbortError') setEstado({ datos: null, cargando: false, error });
      });
    // La función de limpieza corre antes del siguiente efecto o al desmontar.
    return () => control.abort();
    // pedirDatos cambia en cada render; las dependencias reales las da quien llama.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencias, intento]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);
  return { ...estado, reintentar };
}
