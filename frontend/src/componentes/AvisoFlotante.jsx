import { useSyncExternalStore } from 'react';

// Un solo aviso a la vez, llamable desde cualquier parte: avisar('Reseña publicada').
let aviso = null;
let temporizador;
const oyentes = new Set();

export function avisar(texto) {
  aviso = { texto, id: Date.now() };
  oyentes.forEach((oyente) => oyente());
  clearTimeout(temporizador);
  temporizador = setTimeout(() => {
    aviso = null;
    oyentes.forEach((oyente) => oyente());
  }, 3500);
}

function suscribirse(oyente) {
  oyentes.add(oyente);
  return () => oyentes.delete(oyente);
}

/** Va una vez en App. role="status": el lector de pantalla lo anuncia sin mover el foco. */
export default function AvisoFlotante() {
  const actual = useSyncExternalStore(suscribirse, () => aviso);
  return (
    <div role="status" aria-live="polite">
      {actual && <p className="aviso" key={actual.id}>{actual.texto}</p>}
    </div>
  );
}
