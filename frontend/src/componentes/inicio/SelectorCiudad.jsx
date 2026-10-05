import { useEffect, useRef, useState } from 'react';
import { plural } from '../../utilidades/texto.js';
import Icono from '../Icono.jsx';

/**
 * El titular "¿Quién toca en [ciudad]?": la ciudad es un botón que abre la lista.
 * Se cierra con Escape, al hacer clic fuera o al elegir.
 */
export default function SelectorCiudad({ ciudades, actual, alElegir }) {
  const [abierto, setAbierto] = useState(false);
  const boton = useRef(null);
  const lista = useRef(null);

  useEffect(() => {
    if (!abierto) return;
    // Al abrir, el foco va a la ciudad actual para elegir con el teclado.
    (lista.current.querySelector('[aria-pressed="true"]') ?? lista.current.querySelector('button'))?.focus();

    function alTeclear(evento) {
      if (evento.key === 'Escape') {
        setAbierto(false);
        boton.current.focus();
      }
    }
    function alPresionar(evento) {
      if (!lista.current.contains(evento.target) && !boton.current.contains(evento.target)) setAbierto(false);
    }
    document.addEventListener('keydown', alTeclear);
    document.addEventListener('mousedown', alPresionar);
    return () => {
      document.removeEventListener('keydown', alTeclear);
      document.removeEventListener('mousedown', alPresionar);
    };
  }, [abierto]);

  function elegir(slug) {
    setAbierto(false);
    boton.current.focus();
    if (slug !== actual.slug) alElegir(slug);
  }

  return (
    <div className="portada__titular">
      <h1 className="titular" id="titulo-vista" tabIndex={-1}>
        <span className="titular__linea">¿Quién toca en</span>{' '}
        <span className="titular__linea">
          <button
            ref={boton}
            type="button"
            className="ciudad"
            aria-expanded={abierto}
            aria-controls="ciudad-lista"
            onClick={() => setAbierto((a) => !a)}
          >
            <span className="solo-lector">Cambiar de ciudad. Ciudad actual: </span>
            {actual.nombre}
            <Icono nombre="abajo" />
          </button>
          ?
        </span>
      </h1>
      <div className="ciudades" id="ciudad-lista" ref={lista} hidden={!abierto}>
        {ciudades.map((ciudad) => (
          <button
            key={ciudad.slug}
            type="button"
            className="ciudades__op"
            aria-pressed={ciudad.slug === actual.slug}
            onClick={() => elegir(ciudad.slug)}
          >
            {ciudad.nombre}
            <span>{plural(ciudad.conciertos_proximos, 'concierto', 'conciertos')}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
