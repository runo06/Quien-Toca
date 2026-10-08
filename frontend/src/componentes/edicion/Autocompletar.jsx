import { useEffect, useId, useRef, useState } from 'react';

const ESPERA_MS = 250;

/**
 * Campo con sugerencias (patrón "combobox" de ARIA): se escribe, aparecen opciones,
 * se eligen con flechas y Enter o con clic. Si nada coincide y hay alCrear, ofrece
 * "Agregar «texto»".
 *
 * buscar(texto, signal) devuelve la lista; etiquetaDe(opcion) dice cómo mostrarla.
 * valor es la opción elegida (o null); alElegir la recibe.
 */
export default function Autocompletar({ etiqueta, valor, alElegir, buscar, etiquetaDe, alCrear, error, placeholder, deshabilitado }) {
  const id = useId();
  const [texto, setTexto] = useState(valor ? etiquetaDe(valor) : '');
  const [opciones, setOpciones] = useState([]);
  const [abierto, setAbierto] = useState(false);
  const [activa, setActiva] = useState(-1);
  const [creando, setCreando] = useState(false);
  const caja = useRef(null);

  // Si el valor cambia desde fuera (p. ej. se limpió el formulario), el texto lo sigue.
  useEffect(() => setTexto(valor ? etiquetaDe(valor) : ''), [valor]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const limpio = texto.trim();
    if (!abierto || limpio.length < 2 || (valor && etiquetaDe(valor) === texto)) {
      setOpciones([]);
      return undefined;
    }
    const control = new AbortController();
    const temporizador = setTimeout(() => {
      buscar(limpio, control.signal).then(setOpciones).catch(() => {});
    }, ESPERA_MS);
    return () => {
      clearTimeout(temporizador);
      control.abort();
    };
  }, [texto, abierto]); // eslint-disable-line react-hooks/exhaustive-deps

  const limpio = texto.trim();
  const exacta = opciones.some((o) => etiquetaDe(o).toLowerCase() === limpio.toLowerCase());
  const puedeCrear = Boolean(alCrear) && limpio.length >= 2 && !exacta;
  const total = opciones.length + (puedeCrear ? 1 : 0);
  const mostrarLista = abierto && total > 0;

  function elegir(opcion) {
    alElegir(opcion);
    setTexto(etiquetaDe(opcion));
    setAbierto(false);
    setActiva(-1);
  }

  async function crear() {
    setCreando(true);
    try {
      elegir(await alCrear(limpio));
    } finally {
      setCreando(false);
    }
  }

  function alTeclear(evento) {
    if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      setAbierto(true);
      setActiva((a) => (total ? (a + 1) % total : -1));
    } else if (evento.key === 'ArrowUp') {
      evento.preventDefault();
      setActiva((a) => (total ? (a - 1 + total) % total : -1));
    } else if (evento.key === 'Enter' && mostrarLista && activa >= 0) {
      evento.preventDefault();
      if (activa < opciones.length) elegir(opciones[activa]);
      else crear();
    } else if (evento.key === 'Escape') {
      setAbierto(false);
    }
  }

  return (
    <div
      className="campo autocompletar" ref={caja}
      onBlur={(e) => { if (!caja.current.contains(e.relatedTarget)) setAbierto(false); }}
    >
      <label htmlFor={`${id}-entrada`}>{etiqueta}</label>
      <input
        id={`${id}-entrada`} className="entrada" type="text" role="combobox" autoComplete="off"
        aria-expanded={mostrarLista} aria-controls={`${id}-lista`} aria-autocomplete="list"
        aria-activedescendant={mostrarLista && activa >= 0 ? `${id}-op-${activa}` : undefined}
        aria-invalid={Boolean(error)} placeholder={placeholder} disabled={deshabilitado}
        value={texto}
        onChange={(e) => { setTexto(e.target.value); setAbierto(true); setActiva(-1); if (valor) alElegir(null); }}
        onFocus={() => setAbierto(true)}
        onKeyDown={alTeclear}
      />
      {mostrarLista && (
        <ul className="autocompletar__lista" id={`${id}-lista`} role="listbox">
          {opciones.map((opcion, i) => (
            <li
              key={opcion.id} id={`${id}-op-${i}`} role="option" aria-selected={i === activa} tabIndex={-1}
              onMouseDown={(e) => e.preventDefault()} onClick={() => elegir(opcion)}
            >
              {etiquetaDe(opcion)}
            </li>
          ))}
          {puedeCrear && (
            <li
              id={`${id}-op-${opciones.length}`} role="option" aria-selected={activa === opciones.length} tabIndex={-1}
              className="autocompletar__crear" onMouseDown={(e) => e.preventDefault()} onClick={crear}
            >
              {creando ? 'Agregando…' : `+ Agregar «${limpio}»`}
            </li>
          )}
        </ul>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
