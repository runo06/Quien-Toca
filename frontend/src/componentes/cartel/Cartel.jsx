import { useEffect, useRef, useState } from 'react';
import { dibujarCartel } from './dibujarCartel.js';

/** El gráfico en canvas. useRef da acceso al elemento <canvas> real para dibujar en él. */
function CartelGenerado({ semilla, tamano }) {
  const lienzo = useRef(null);
  useEffect(() => {
    dibujarCartel(lienzo.current, semilla);
  }, [semilla]);
  return <canvas ref={lienzo} width={tamano} height={tamano} aria-hidden="true" />;
}

/**
 * La imagen del evento si existe; si no hay o no carga, el cartel generado.
 * alt="" porque es decorativa: el nombre del artista ya está escrito al lado.
 */
export default function Cartel({ imagen, semilla, tamano = 360 }) {
  const [fallo, setFallo] = useState(false);

  // Si cambia la imagen (otro concierto), se vuelve a intentar.
  useEffect(() => setFallo(false), [imagen]);

  if (imagen && !fallo) {
    return <img src={imagen} alt="" loading="lazy" decoding="async" onError={() => setFallo(true)} />;
  }
  return <CartelGenerado semilla={semilla} tamano={tamano} />;
}
