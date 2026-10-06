import { useId, useState } from 'react';
import { reportarResena } from '../../api.js';

const MOTIVOS = [
  ['ofensiva', 'Es ofensiva o tiene odio'],
  ['spam', 'Es publicidad o spam'],
  ['falsa', 'No parece de alguien que asistió'],
  ['otro', 'Otro motivo'],
];

/** Reporte de una reseña: queda pendiente hasta que alguien lo revise en el panel. */
export default function FormularioReporte({ resena, alTerminar, alCancelar }) {
  const id = useId();
  const [motivo, setMotivo] = useState('');
  const [comentario, setComentario] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento) {
    evento.preventDefault();
    if (!motivo) {
      setError('Elige un motivo.');
      return;
    }
    setEnviando(true);
    try {
      await reportarResena(resena.id, { motivo, comentario: comentario.trim() });
      alTerminar();
    } catch (falla) {
      setError(falla.message);
      setEnviando(false);
    }
  }

  return (
    <form className="resena__confirmar" onSubmit={enviar} noValidate aria-busy={enviando}>
      <fieldset className="grupo" style={{ flexBasis: '100%' }}>
        <legend>¿Por qué quieres reportar esta reseña?</legend>
        <div className="opciones-reporte">
          {MOTIVOS.map(([valor, texto]) => (
            <label key={valor}>
              <input
                type="radio" name={`${id}-motivo`} value={valor} checked={motivo === valor}
                onChange={() => { setMotivo(valor); setError(''); }}
              />
              {texto}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="campo" style={{ flexBasis: '100%' }}>
        <label htmlFor={`${id}-comentario`}>Algo más, si quieres</label>
        <input className="entrada" id={`${id}-comentario`} maxLength={500} value={comentario} onChange={(e) => setComentario(e.target.value)} />
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <button type="submit" className="boton boton--chico" disabled={enviando}>{enviando ? 'Enviando…' : 'Enviar reporte'}</button>
      <button type="button" className="enlace" onClick={alCancelar}>Cancelar</button>
    </form>
  );
}
