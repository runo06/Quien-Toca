import { useId, useState } from 'react';
import { Link } from 'react-router';
import {
  buscarArtistasEdicion, buscarRecintosEdicion, capturarGira, crearArtistaEdicion, crearRecintoEdicion,
} from '../../api.js';
import { leerCiudadGuardada, usarCiudades } from '../../contexto/ciudades.jsx';
import { fechaMedia, hoyEnMexico } from '../../utilidades/fechas.js';
import { avisar } from '../AvisoFlotante.jsx';
import Autocompletar from './Autocompletar.jsx';

let siguienteFila = 1;
const filaVacia = (ciudad) => ({ clave: siguienteFila++, ciudad, recinto: null, fecha: '', hora: '', url_boletos: '', precio_desde: '' });
const primero = (lista) => [].concat(lista ?? [])[0];

function FilaFecha({ fila, numero, errores, ciudades, alCambiar, alQuitar, puedeQuitar }) {
  const id = useId();
  const poner = (campo) => (evento) => alCambiar({ ...fila, [campo]: evento.target.value });
  return (
    <fieldset className="fila-fecha">
      <legend>Fecha {numero}</legend>
      <div className="fila-fecha__campos">
        <div className="campo">
          <label htmlFor={`${id}-ciudad`}>Ciudad</label>
          <select
            className="entrada" id={`${id}-ciudad`} value={fila.ciudad}
            onChange={(e) => alCambiar({ ...fila, ciudad: e.target.value, recinto: null })}
          >
            {ciudades.map((c) => <option key={c.slug} value={c.slug}>{c.nombre}</option>)}
          </select>
        </div>
        <Autocompletar
          etiqueta="Recinto" valor={fila.recinto} placeholder="Ej. Auditorio Nacional"
          etiquetaDe={(r) => r.nombre}
          buscar={(texto, signal) => buscarRecintosEdicion(texto, fila.ciudad, signal)}
          alCrear={(nombre) => crearRecintoEdicion({ nombre, ciudad: fila.ciudad })}
          alElegir={(recinto) => alCambiar({ ...fila, recinto })}
          error={primero(errores.recinto)}
        />
        <div className="campo">
          <label htmlFor={`${id}-fecha`}>Día</label>
          <input className="entrada" id={`${id}-fecha`} type="date" min={hoyEnMexico()} value={fila.fecha} onChange={poner('fecha')} aria-invalid={Boolean(errores.fecha)} />
          {errores.fecha && <p className="error">{primero(errores.fecha)}</p>}
        </div>
        <div className="campo">
          <label htmlFor={`${id}-hora`}>Hora <span className="apagado">(opcional)</span></label>
          <input className="entrada" id={`${id}-hora`} type="time" value={fila.hora} onChange={poner('hora')} />
        </div>
        <div className="campo">
          <label htmlFor={`${id}-url`}>Otra boletera <span className="apagado">(opcional)</span></label>
          <input className="entrada" id={`${id}-url`} type="url" placeholder="https://…" value={fila.url_boletos} onChange={poner('url_boletos')} aria-invalid={Boolean(errores.url_boletos)} />
          {errores.url_boletos && <p className="error">{primero(errores.url_boletos)}</p>}
        </div>
        <div className="campo">
          <label htmlFor={`${id}-precio`}>Precio desde <span className="apagado">(opcional)</span></label>
          <input className="entrada" id={`${id}-precio`} type="number" min="0" step="1" inputMode="numeric" value={fila.precio_desde} onChange={poner('precio_desde')} />
        </div>
      </div>
      {puedeQuitar && <button type="button" className="enlace" onClick={alQuitar}>Quitar esta fecha</button>}
    </fieldset>
  );
}

/** Captura de una gira: los datos comunes una vez y las fechas que hagan falta. */
export default function FormularioGira() {
  const id = useId();
  const ciudades = usarCiudades();
  const ciudadInicial = leerCiudadGuardada() ?? ciudades.datos?.find((c) => c.es_predeterminada)?.slug ?? 'cdmx';
  const [comunes, setComunes] = useState({ artista: null, gira: '', url_boletos: '', imagen_url: '', genero: '' });
  const [filas, setFilas] = useState(() => [filaVacia(ciudadInicial)]);
  const [errores, setErrores] = useState({});
  const [enviando, setEnviando] = useState(false);
  const [creados, setCreados] = useState(null);

  // Al corregir un campo, su error se quita.
  const quitarError = (campo) => setErrores((e) => ({ ...e, [campo]: undefined, general: undefined }));
  const poner = (campo) => (evento) => {
    setComunes((c) => ({ ...c, [campo]: evento.target.value }));
    quitarError(campo);
  };

  async function enviar(evento) {
    evento.preventDefault();
    const faltan = {};
    if (!comunes.artista) faltan.artista = ['Elige o agrega al artista.'];
    if (!comunes.url_boletos.trim()) faltan.url_boletos = ['Pega el enlace de la boletera.'];
    const fechas = filas.map((f) => {
      const e = {};
      if (!f.recinto) e.recinto = ['Elige o agrega el recinto.'];
      if (!f.fecha) e.fecha = ['Elige el día.'];
      return e;
    });
    if (Object.keys(faltan).length || fechas.some((e) => Object.keys(e).length)) {
      setErrores({ ...faltan, fechas });
      return;
    }
    setEnviando(true);
    setErrores({});
    try {
      const resultado = await capturarGira({
        artista: comunes.artista.id, gira: comunes.gira.trim(), url_boletos: comunes.url_boletos.trim(),
        imagen_url: comunes.imagen_url.trim(), genero: comunes.genero.trim(),
        fechas: filas.map((f) => ({
          recinto: f.recinto.id, fecha: f.fecha, hora: f.hora || null,
          url_boletos: f.url_boletos.trim(), precio_desde: f.precio_desde === '' ? null : f.precio_desde,
        })),
      });
      setCreados(resultado);
      avisar(`Se crearon ${resultado.length} conciertos`);
    } catch (error) {
      setErrores({ ...error.campos, general: Object.keys(error.campos ?? {}).length ? undefined : error.message });
    } finally {
      setEnviando(false);
    }
  }

  if (creados) {
    return (
      <div className="formulario" role="status">
        <h2 className="cartel">Listo: {creados.length} {creados.length === 1 ? 'concierto' : 'conciertos'}</h2>
        <ul className="lista-simple">
          {creados.map((c) => (
            <li key={c.slug}><Link to={`/concierto/${c.slug}`}>{c.recinto.ciudad.nombre}, {c.recinto.nombre} · {fechaMedia(c.fecha_hora)}</Link></li>
          ))}
        </ul>
        <div><button type="button" className="boton" onClick={() => { setCreados(null); setFilas([filaVacia(ciudadInicial)]); setComunes({ artista: null, gira: '', url_boletos: '', imagen_url: '', genero: '' }); }}>Capturar otra gira</button></div>
      </div>
    );
  }

  return (
    <form className="formulario" onSubmit={enviar} noValidate aria-busy={enviando}>
      <h2 className="cartel">Capturar gira</h2>
      <p className="apagado">Los datos de la gira una sola vez y abajo cada fecha. Si una fecha ya existe, se marca y no se guarda ninguna.</p>
      {errores.general && <p className="error" role="alert">{errores.general}</p>}

      <div className="rejilla-dos">
        <Autocompletar
          etiqueta="Artista" valor={comunes.artista} placeholder="Ej. Café Tacvba"
          etiquetaDe={(a) => a.nombre} buscar={buscarArtistasEdicion} alCrear={crearArtistaEdicion}
          alElegir={(artista) => {
            setComunes((c) => ({ ...c, artista, genero: c.genero || artista?.genero || '' }));
            quitarError('artista');
          }}
          error={primero(errores.artista)}
        />
        <div className="campo">
          <label htmlFor={`${id}-gira`}>Nombre de la gira <span className="apagado">(opcional)</span></label>
          <input className="entrada" id={`${id}-gira`} value={comunes.gira} onChange={poner('gira')} maxLength={150} />
        </div>
        <div className="campo">
          <label htmlFor={`${id}-url`}>Boletera</label>
          <input className="entrada" id={`${id}-url`} type="url" placeholder="https://…" value={comunes.url_boletos} onChange={poner('url_boletos')} aria-invalid={Boolean(errores.url_boletos)} />
          {errores.url_boletos && <p className="error">{primero(errores.url_boletos)}</p>}
        </div>
        <div className="campo">
          <label htmlFor={`${id}-imagen`}>Imagen (URL) <span className="apagado">(opcional)</span></label>
          <input className="entrada" id={`${id}-imagen`} type="url" placeholder="https://…" value={comunes.imagen_url} onChange={poner('imagen_url')} aria-invalid={Boolean(errores.imagen_url)} />
          {errores.imagen_url && <p className="error">{primero(errores.imagen_url)}</p>}
        </div>
        <div className="campo">
          <label htmlFor={`${id}-genero`}>Género <span className="apagado">(opcional)</span></label>
          <input className="entrada" id={`${id}-genero`} value={comunes.genero} onChange={poner('genero')} maxLength={60} />
        </div>
      </div>

      <h3 className="subtitulo">Fechas</h3>
      {filas.map((fila, i) => (
        <FilaFecha
          key={fila.clave} fila={fila} numero={i + 1} ciudades={ciudades.datos ?? []}
          errores={errores.fechas?.[i] ?? {}} puedeQuitar={filas.length > 1}
          alCambiar={(nueva) => {
            setFilas((fs) => fs.map((f) => (f.clave === fila.clave ? nueva : f)));
            // Se quitan los errores de los campos de esta fila que cambiaron.
            setErrores((e) => {
              if (!e.fechas?.[i]) return e;
              const delaFila = Object.fromEntries(Object.entries(e.fechas[i]).filter(([campo]) => nueva[campo] === fila[campo]));
              return { ...e, fechas: e.fechas.map((x, j) => (j === i ? delaFila : x)) };
            });
          }}
          alQuitar={() => {
            setFilas((fs) => fs.filter((f) => f.clave !== fila.clave));
            setErrores((e) => ({ ...e, fechas: e.fechas?.filter((_, j) => j !== i) }));
          }}
        />
      ))}
      <div>
        <button type="button" className="boton boton--linea boton--chico" onClick={() => setFilas((fs) => [...fs, filaVacia(fs.at(-1)?.ciudad ?? ciudadInicial)])}>
          + Agregar otra fecha
        </button>
      </div>
      <div className="formulario__pie">
        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? 'Creando…' : `Crear ${filas.length} ${filas.length === 1 ? 'concierto' : 'conciertos'}`}
        </button>
      </div>
    </form>
  );
}
