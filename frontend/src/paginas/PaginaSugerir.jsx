import { useId, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { obtenerRecintos, sugerirConcierto } from '../api.js';
import { leerCiudadGuardada, usarCiudades } from '../contexto/ciudades.jsx';
import { usarPeticion } from '../hooks/usarPeticion.js';
import { usarSesion } from '../hooks/usarSesion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import { hoyEnMexico } from '../utilidades/fechas.js';
import './PaginaCuenta.css';

function Campo({ etiqueta, error, ayuda, children }) {
  return (
    <div className="campo">
      {etiqueta}
      {children}
      {ayuda && <p className="letra-chica" style={{ margin: 0 }}>{ayuda}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

function Formulario({ alTerminar }) {
  const id = useId();
  const ciudades = usarCiudades();
  const inicial = ciudades.datos?.find((c) => c.slug === leerCiudadGuardada())?.slug
    ?? ciudades.datos?.find((c) => c.es_predeterminada)?.slug ?? '';
  const [valores, setValores] = useState({
    artista: '', ciudad: inicial, recinto: '', fecha: '', hora: '', url_boletos: '', comentario: '',
  });
  const [errores, setErrores] = useState({});
  const [enviando, setEnviando] = useState(false);
  // Los recintos que ya conocemos en esa ciudad, para sugerirlos mientras se escribe.
  const recintos = usarPeticion(
    (signal) => obtenerRecintos({ ciudad: valores.ciudad || inicial, pagina: 1 }, signal),
    [valores.ciudad || inicial],
  );

  const poner = (campo) => (evento) => {
    setValores((v) => ({ ...v, [campo]: evento.target.value }));
    setErrores((e) => ({ ...e, [campo]: undefined }));
  };

  async function enviar(evento) {
    evento.preventDefault();
    const faltan = {};
    for (const [campo, mensaje] of [
      ['artista', 'Escribe quién toca.'], ['recinto', 'Escribe el lugar.'], ['fecha', 'Elige el día.'],
      ['url_boletos', 'Pega el enlace donde venden los boletos.'],
    ]) if (!valores[campo].trim()) faltan[campo] = mensaje;
    if (Object.keys(faltan).length) {
      setErrores(faltan);
      return;
    }
    setEnviando(true);
    try {
      await sugerirConcierto({ ...valores, ciudad: valores.ciudad || inicial, hora: valores.hora || null });
      alTerminar(valores.artista);
    } catch (error) {
      const primero = (campo) => [].concat(error.campos?.[campo] ?? [])[0];
      setErrores({
        artista: primero('artista'), recinto: primero('recinto'), fecha: primero('fecha'),
        url_boletos: primero('url_boletos'),
        general: Object.keys(error.campos ?? {}).length ? undefined : error.message,
      });
      setEnviando(false);
    }
  }

  const etiqueta = (campo, texto) => <label htmlFor={`${id}-${campo}`}>{texto}</label>;
  const entrada = (campo, props = {}) => (
    <input
      className="entrada" id={`${id}-${campo}`} value={valores[campo]} onChange={poner(campo)}
      aria-invalid={Boolean(errores[campo])} {...props}
    />
  );

  return (
    <form className="formulario cuenta__caja" onSubmit={enviar} noValidate aria-busy={enviando}>
      <h1 className="cartel" id="titulo-vista" tabIndex={-1}>Sugiere un concierto</h1>
      <p className="apagado">¿Falta uno en la cartelera? Cuéntanos y lo revisamos antes de publicarlo.</p>
      {errores.general && <p className="error" role="alert">{errores.general}</p>}

      <Campo etiqueta={etiqueta('artista', '¿Quién toca?')} error={errores.artista}>
        {entrada('artista', { placeholder: 'Ej. Café Tacvba', autoComplete: 'off' })}
      </Campo>
      <div className="campo">
        {etiqueta('ciudad', 'Ciudad')}
        <select className="entrada" id={`${id}-ciudad`} value={valores.ciudad || inicial} onChange={poner('ciudad')}>
          {ciudades.datos?.map((c) => <option key={c.slug} value={c.slug}>{c.nombre}</option>)}
        </select>
      </div>
      <Campo etiqueta={etiqueta('recinto', '¿Dónde?')} error={errores.recinto} ayuda="Si ya lo conocemos, aparece mientras escribes.">
        {entrada('recinto', { placeholder: 'Ej. Auditorio Nacional', list: `${id}-recintos`, autoComplete: 'off' })}
        <datalist id={`${id}-recintos`}>
          {recintos.datos?.resultados.map((r) => <option key={r.slug} value={r.nombre} />)}
        </datalist>
      </Campo>
      <div className="doble" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 18 }}>
        <Campo etiqueta={etiqueta('fecha', 'Día')} error={errores.fecha}>
          {entrada('fecha', { type: 'date', min: hoyEnMexico() })}
        </Campo>
        <Campo etiqueta={etiqueta('hora', 'Hora (si ya se sabe)')}>
          {entrada('hora', { type: 'time' })}
        </Campo>
      </div>
      <Campo etiqueta={etiqueta('url_boletos', '¿Dónde venden los boletos?')} error={errores.url_boletos}>
        {entrada('url_boletos', { type: 'url', inputMode: 'url', placeholder: 'https://…' })}
      </Campo>
      <Campo etiqueta={etiqueta('comentario', 'Algo más, si quieres')}>
        {entrada('comentario', { maxLength: 500 })}
      </Campo>
      <div className="formulario__pie">
        <button type="submit" className="boton" disabled={enviando}>{enviando ? 'Enviando…' : 'Enviar sugerencia'}</button>
      </div>
    </form>
  );
}

/** /sugerir */
export default function PaginaSugerir() {
  const usuario = usarSesion();
  const ubicacion = useLocation();
  const [enviada, setEnviada] = useState(null);
  usarTituloDocumento('Sugerir un concierto · ¿Quién toca?');

  return (
    <div className="centro cuenta">
      {!usuario ? (
        <div className="formulario cuenta__caja">
          <h1 className="cartel" id="titulo-vista" tabIndex={-1}>Sugiere un concierto</h1>
          <p className="apagado">Inicia sesión para sugerir un concierto que falta en la cartelera.</p>
          <div><Link className="boton" to="/entrar" state={{ desde: ubicacion.pathname }}>Iniciar sesión</Link></div>
        </div>
      ) : enviada ? (
        <div className="formulario cuenta__caja" role="status">
          <h1 className="cartel" id="titulo-vista" tabIndex={-1}>¡Gracias!</h1>
          <p>Revisaremos tu sugerencia de <strong>{enviada}</strong>. Puedes ver en qué va en <Link className="enlace" to="/mis-conciertos">Mis conciertos</Link>.</p>
          <div><button type="button" className="boton boton--linea" onClick={() => setEnviada(null)}>Sugerir otro</button></div>
        </div>
      ) : (
        <Formulario alTerminar={setEnviada} />
      )}
    </div>
  );
}
