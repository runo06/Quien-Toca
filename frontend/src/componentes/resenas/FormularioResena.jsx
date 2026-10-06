import { useId, useRef, useState } from 'react';
import { crearResena, editarResena } from '../../api.js';
import { fechaMedia } from '../../utilidades/fechas.js';
import Icono from '../Icono.jsx';

const PALABRAS = ['', 'Malo', 'Regular', 'Bueno', 'Muy bueno', 'Increíble'];
const ASPECTOS = [['show', 'Show en vivo'], ['sonido', 'Sonido'], ['puntualidad', 'Puntualidad'], ['recinto', 'El recinto']];
const MINIMO = 20;

/** Cinco botones (estrellas o tramos). Volver a pulsar el elegido lo quita, si se permite. */
function Escala({ valor, alCambiar, clase, interior, etiquetaId, opcional = false }) {
  return (
    <span className={clase === 'estrella' ? 'calif__botones' : 'tramos'} role="group" aria-labelledby={etiquetaId}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n} type="button" className={`${clase}${valor && n <= valor ? ' on' : ''}`}
          aria-pressed={n === valor} aria-label={`${n} de 5`}
          onClick={() => alCambiar(opcional && n === valor ? null : n)}
        >
          {interior}
        </button>
      ))}
    </span>
  );
}

/**
 * Para crear (con fechas: las que la persona puede reseñar) o editar (con resena).
 * alGuardar recibe la reseña como la devolvió el servidor.
 */
export default function FormularioResena({ fechas = [], resena, alGuardar, alCancelar }) {
  const id = useId();
  const editando = Boolean(resena);
  const [valores, setValores] = useState(() => ({
    concierto: resena?.concierto.slug ?? fechas[0]?.slug ?? '',
    general: resena?.general ?? null,
    show: resena?.show ?? null,
    sonido: resena?.sonido ?? null,
    puntualidad: resena?.puntualidad ?? null,
    recinto: resena?.recinto ?? null,
    texto: resena?.texto ?? '',
    asistio: false,
  }));
  const [errores, setErrores] = useState({});
  const [enviando, setEnviando] = useState(false);
  const referencias = { general: useRef(null), texto: useRef(null), asistio: useRef(null) };

  const poner = (campo, valor) => {
    setValores((actuales) => ({ ...actuales, [campo]: valor }));
    setErrores((actuales) => ({ ...actuales, [campo]: undefined, general_api: undefined }));
  };

  function validar() {
    const fallas = {};
    if (!valores.general) fallas.general = 'Elige de 1 a 5 estrellas.';
    if (valores.texto.trim().length < MINIMO) fallas.texto = `Escribe al menos ${MINIMO} caracteres para que tu reseña le sirva a alguien.`;
    if (!editando && !valores.asistio) fallas.asistio = 'Solo pueden reseñar quienes asistieron.';
    return fallas;
  }

  async function enviar(evento) {
    evento.preventDefault();
    const fallas = validar();
    setErrores(fallas);
    const primera = ['general', 'texto', 'asistio'].find((campo) => fallas[campo]);
    if (primera) {
      // El foco va al primer campo con error: quien usa teclado o lector llega directo.
      const elemento = referencias[primera].current;
      (elemento?.querySelector?.('button') ?? elemento)?.focus();
      return;
    }
    setEnviando(true);
    const datos = { ...valores, texto: valores.texto.trim() };
    try {
      if (editando) {
        delete datos.concierto;
        delete datos.asistio;
      }
      alGuardar(editando ? await editarResena(resena.id, datos) : await crearResena(datos));
    } catch (error) {
      const primero = (campo) => [].concat(error.campos?.[campo] ?? [])[0];
      setErrores({
        general: primero('general'), texto: primero('texto'), asistio: primero('asistio'),
        // Errores sin campo propio (p. ej. "Ya reseñaste este concierto") van arriba del botón.
        general_api: primero('concierto') ?? primero('non_field_errors') ?? (error.campos && Object.keys(error.campos).length ? undefined : error.message),
      });
      setEnviando(false);
    }
  }

  const fechaElegida = fechas.find((f) => f.slug === valores.concierto);

  return (
    <form className="formulario" onSubmit={enviar} noValidate aria-busy={enviando} aria-labelledby={`${id}-titulo`}>
      <h3 className="cartel" id={`${id}-titulo`}>{editando ? 'Edita tu reseña' : 'Tu reseña'}</h3>

      {editando ? (
        <p className="apagado">{resena.concierto.ciudad}, {fechaMedia(resena.concierto.fecha_hora)}</p>
      ) : fechas.length > 1 ? (
        <div className="campo">
          <label htmlFor={`${id}-fecha`}>¿A qué fecha fuiste?</label>
          <select className="entrada" id={`${id}-fecha`} value={valores.concierto} onChange={(e) => poner('concierto', e.target.value)}>
            {fechas.map((f) => (
              <option key={f.slug} value={f.slug}>{f.ciudad}, {f.recinto}, {fechaMedia(f.fecha_hora)}</option>
            ))}
          </select>
        </div>
      ) : (
        fechaElegida && <p className="apagado">{fechaElegida.ciudad}, {fechaElegida.recinto}, {fechaMedia(fechaElegida.fecha_hora)}</p>
      )}

      <fieldset className="grupo" ref={referencias.general}>
        <legend id={`${id}-general`}>¿Cómo estuvo el concierto?</legend>
        <div className="calif">
          <Escala
            valor={valores.general} alCambiar={(n) => poner('general', n)} clase="estrella"
            interior={<Icono nombre="estrella" />} etiquetaId={`${id}-general`}
          />
          <span className="calif__palabra" aria-live="polite">{PALABRAS[valores.general ?? 0]}</span>
        </div>
        {errores.general && <p className="error">{errores.general}</p>}
      </fieldset>

      <fieldset className="grupo">
        <legend>Detalles, si quieres</legend>
        <div className="aspectos">
          {ASPECTOS.map(([campo, nombre]) => (
            <div className="aspecto" key={campo}>
              <span className="aspecto__nombre" id={`${id}-${campo}`}>{nombre}</span>
              <Escala
                valor={valores[campo]} alCambiar={(n) => poner(campo, n)} clase="tramo"
                interior={<i />} etiquetaId={`${id}-${campo}`} opcional
              />
            </div>
          ))}
        </div>
      </fieldset>

      <div className="campo">
        <label htmlFor={`${id}-texto`}>Cuéntalo con tus palabras</label>
        <textarea
          className="entrada" id={`${id}-texto`} ref={referencias.texto} maxLength={2000}
          placeholder="¿Qué te gustó? ¿Qué le dirías a alguien que va a ir?"
          value={valores.texto} onChange={(e) => poner('texto', e.target.value)}
          aria-invalid={Boolean(errores.texto)} aria-describedby={`${id}-contador${errores.texto ? ` ${id}-e-texto` : ''}`}
        />
        <p className="contador" id={`${id}-contador`}>
          {valores.texto.trim().length < MINIMO
            ? `${valores.texto.trim().length} de ${MINIMO} caracteres mínimos`
            : `${valores.texto.length} de 2000`}
        </p>
        {errores.texto && <p className="error" id={`${id}-e-texto`}>{errores.texto}</p>}
      </div>

      {!editando && (
        <div>
          <label className="casilla" htmlFor={`${id}-asistio`}>
            <input
              type="checkbox" id={`${id}-asistio`} ref={referencias.asistio}
              checked={valores.asistio} onChange={(e) => poner('asistio', e.target.checked)}
            />
            <span>Confirmo que asistí a este concierto</span>
          </label>
          {errores.asistio && <p className="error" style={{ marginTop: 8 }}>{errores.asistio}</p>}
        </div>
      )}

      {errores.general_api && <p className="error" role="alert">{errores.general_api}</p>}
      <div className="formulario__pie">
        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Publicar reseña'}
        </button>
        <button type="button" className="enlace" onClick={alCancelar}>Cancelar</button>
      </div>
    </form>
  );
}
