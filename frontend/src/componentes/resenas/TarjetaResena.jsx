import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { borrarResena, marcarMeSirvio } from '../../api.js';
import { usarSesion } from '../../hooks/usarSesion.js';
import { fechaMedia } from '../../utilidades/fechas.js';
import { avisar } from '../AvisoFlotante.jsx';
import Estrellas from './Estrellas.jsx';
import FormularioReporte from './FormularioReporte.jsx';
import FormularioResena from './FormularioResena.jsx';

/**
 * Una reseña con el sello "Asistió".
 * Variante breve (conArtista): dice de qué artista es y no lleva botones; va en el inicio.
 * Completa: "Me sirvió" y "Reportar" en las ajenas; "Editar" y "Borrar" en las propias.
 */
export default function TarjetaResena({ resena, conArtista = false, alCambiar, alBorrar }) {
  const usuario = usarSesion();
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const [modo, setModo] = useState('ver'); // ver | editar | borrar | reportar
  const [ocupado, setOcupado] = useState(false);
  const { concierto } = resena;

  if (modo === 'editar') {
    return (
      <FormularioResena
        resena={resena}
        alGuardar={(nueva) => { alCambiar(nueva); setModo('ver'); avisar('Reseña actualizada'); }}
        alCancelar={() => setModo('ver')}
      />
    );
  }

  const irAEntrar = () => navegar('/entrar', { state: { desde: ubicacion.pathname + ubicacion.search } });

  async function alternarMeSirvio() {
    if (!usuario) return irAEntrar();
    setOcupado(true);
    try {
      const { utiles, me_sirvio } = await marcarMeSirvio(resena.id, !resena.me_sirvio);
      alCambiar({ ...resena, utiles, me_sirvio });
    } catch (error) {
      avisar(error.message);
    } finally {
      setOcupado(false);
    }
  }

  async function borrar() {
    setOcupado(true);
    try {
      await borrarResena(resena.id);
      alBorrar(resena.id);
      avisar('Reseña borrada');
    } catch (error) {
      avisar(error.message);
      setOcupado(false);
    }
  }

  const lugar = `${concierto.ciudad}, ${fechaMedia(concierto.fecha_hora)}`;

  return (
    <article className="resena" aria-label={`Reseña de ${resena.autor}`}>
      <div className="resena__arriba">
        <Estrellas valor={resena.general} />
        <span className="sello">Asistió</span>
      </div>
      <p className="resena__texto">{resena.texto}</p>
      <p className="resena__pie">
        <strong>
          {resena.autor} {resena.es_mia && <span className="tuya">Tu reseña</span>}
        </strong>
        <span className="apagado">
          {conArtista ? (
            <><Link to={`/concierto/${concierto.slug}`}>{concierto.artista}</Link>, {lugar}</>
          ) : (
            lugar
          )}
          {resena.editada && ' · editada'}
        </span>
      </p>

      {!conArtista && modo === 'ver' && (
        <div className="resena__acciones">
          {resena.es_mia ? (
            <>
              <button type="button" className="enlace" onClick={() => setModo('editar')}>Editar</button>
              <button type="button" className="enlace" onClick={() => setModo('borrar')}>Borrar</button>
            </>
          ) : (
            <>
              <button type="button" className="util" aria-pressed={resena.me_sirvio} disabled={ocupado} onClick={alternarMeSirvio}>
                Me sirvió ({resena.utiles})
              </button>
              <button type="button" className="enlace" onClick={() => (usuario ? setModo('reportar') : irAEntrar())}>
                Reportar
              </button>
            </>
          )}
        </div>
      )}

      {modo === 'borrar' && (
        <div className="resena__confirmar" role="group" aria-label="Confirmar borrado">
          <p>¿Borrar tu reseña? No se puede deshacer.</p>
          <button type="button" className="boton boton--chico" disabled={ocupado} onClick={borrar}>Sí, borrar</button>
          <button type="button" className="enlace" onClick={() => setModo('ver')}>Cancelar</button>
        </div>
      )}
      {modo === 'reportar' && (
        <FormularioReporte
          resena={resena}
          alTerminar={() => { setModo('ver'); avisar('Gracias. Revisaremos esta reseña.'); }}
          alCancelar={() => setModo('ver')}
        />
      )}
    </article>
  );
}
