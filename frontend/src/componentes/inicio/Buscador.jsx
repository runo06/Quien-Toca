import { useEffect, useState } from 'react';

const ESPERA_MS = 300;

/**
 * Campo de búsqueda con espera: lo escrito vive en un estado local (borrador) y
 * solo se envía cuando la persona deja de teclear 300 ms. Así no se hace una
 * petición por cada letra.
 */
export default function Buscador({ valor, alCambiar }) {
  const [borrador, setBorrador] = useState(valor);

  // Si el valor cambia desde fuera (p. ej. "Quitar filtros"), el campo se actualiza.
  useEffect(() => setBorrador(valor), [valor]);

  useEffect(() => {
    if (borrador === valor) return;
    const temporizador = setTimeout(() => alCambiar(borrador), ESPERA_MS);
    return () => clearTimeout(temporizador); // si teclea otra letra, se reinicia la espera
  }, [borrador, valor, alCambiar]);

  return (
    <div className="campo campo--buscar">
      <label htmlFor="buscar">Busca un artista, evento o recinto</label>
      <input
        className="entrada"
        id="buscar"
        type="search"
        autoComplete="off"
        placeholder="Ej. Los Cometas del Sur"
        value={borrador}
        onChange={(evento) => setBorrador(evento.target.value)}
      />
    </div>
  );
}
