import { useEffect } from 'react';

/** Cambia el título de la pestaña del navegador. */
export function usarTituloDocumento(titulo) {
  useEffect(() => {
    document.title = titulo;
  }, [titulo]);
}
