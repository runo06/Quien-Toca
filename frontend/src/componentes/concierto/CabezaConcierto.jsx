import { Link } from 'react-router';
import { guardarConcierto } from '../../api.js';
import BotonAlternar from '../BotonAlternar.jsx';
import { fechaLarga, hora, horaSimple } from '../../utilidades/fechas.js';
import { listaConY, subtituloDe } from '../../utilidades/texto.js';
import Cartel from '../cartel/Cartel.jsx';

/** Cartel grande, fecha, artista y datos del recinto. */
export default function CabezaConcierto({ concierto }) {
  const { artista, invitados, recinto, fecha_hora, hora_por_confirmar, apertura_puertas, genero, imagen_url } = concierto;
  const subtitulo = subtituloDe(concierto);

  return (
    <div className="cabeza">
      <div className="cartelote">
        <Cartel imagen={imagen_url} semilla={artista.slug} tamano={760} />
      </div>
      <div>
        <p className="cuando">
          {fechaLarga(fecha_hora)}, {hora_por_confirmar ? 'hora por confirmar' : hora(fecha_hora)}
        </p>
        <h1 className="cartel" id="titulo-vista" tabIndex={-1}>{artista.nombre}</h1>
        {subtitulo && <p className="gira-nombre">{subtitulo}</p>}
        {invitados.length > 0 && (
          <p className="invitados apagado">Con {listaConY(invitados.map((i) => i.nombre))}</p>
        )}
        <div className="cabeza__acciones">
          {!concierto.ya_paso && (
            <BotonAlternar
              key={`${concierto.slug}-${concierto.guardado}`}
              activo={concierto.guardado}
              alternar={(guardar) => guardarConcierto(concierto.slug, guardar)}
              textos={{ activo: 'Guardado ✓', inactivo: 'Guardar', aviso: ['Guardado en Mis conciertos', 'Lo quitaste de Mis conciertos'] }}
            />
          )}
          <Link className="enlace" to={`/artista/${artista.slug}`}>Ver todo sobre {artista.nombre}</Link>
        </div>
        <dl className="datos">
          <div>
            <dt>Recinto</dt>
            <dd><Link to={`/recinto/${recinto.slug}`}>{recinto.nombre}</Link>, {recinto.ciudad.nombre}</dd>
          </div>
          {recinto.direccion && (
            <div>
              <dt>Dirección</dt>
              <dd>{recinto.direccion}</dd>
            </div>
          )}
          {apertura_puertas && (
            <div>
              <dt>Apertura de puertas</dt>
              <dd>{horaSimple(apertura_puertas)}</dd>
            </div>
          )}
          {genero && (
            <div>
              <dt>Género</dt>
              <dd>{genero}</dd>
            </div>
          )}
        </dl>
      </div>
    </div>
  );
}
