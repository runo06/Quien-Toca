import { Link, useLocation } from 'react-router';
import { diaDelMes, diaSemanaCorto, hora, mesCorto } from '../../utilidades/fechas.js';
import { dinero, plural, subtituloDe } from '../../utilidades/texto.js';
import Cartel from '../cartel/Cartel.jsx';
import Icono from '../Icono.jsx';
import './Boleto.css';

/** Un concierto con forma de boleto: talón de fecha, cartel, datos y precio. */
export default function Boleto({ concierto }) {
  const { slug, artista, recinto, fecha_hora, hora_por_confirmar, precio_desde, moneda, imagen_url, promedio_artista, resenas_artista } = concierto;
  const ubicacion = useLocation();
  const enlace = `/concierto/${slug}`;
  // Se guarda de dónde venimos (con filtros) para que "volver" regrese al mismo lugar.
  const estado = { desde: ubicacion.pathname + ubicacion.search };
  const subtitulo = subtituloDe(concierto);

  return (
    <li className="boleto">
      <div className="boleto__fecha">
        <span className="dsem">{diaSemanaCorto(fecha_hora)}</span>
        <span className="dia">{diaDelMes(fecha_hora)}</span>
        <span className="mes">{mesCorto(fecha_hora)}</span>
      </div>
      <div className="boleto__cartel">
        <Cartel imagen={imagen_url} semilla={artista.slug} />
      </div>
      <div className="boleto__info">
        <h3 className="cartel">
          <Link to={enlace} state={estado}>{artista.nombre}</Link>
        </h3>
        <p className="apagado">{[subtitulo, recinto.nombre].filter(Boolean).join(', ')}</p>
        <p className="nota apagado">{hora_por_confirmar ? 'Hora por confirmar' : hora(fecha_hora)}</p>
        {resenas_artista > 0 && (
          <p className="nota">
            <Icono nombre="estrella" />
            <strong>{promedio_artista.toFixed(1)} de 5</strong>
            <span className="apagado">{plural(resenas_artista, 'reseña', 'reseñas')} de sus fechas pasadas</span>
          </p>
        )}
      </div>
      <div className="boleto__accion">
        {precio_desde != null ? (
          <p className="precio"><span>Desde</span><strong>{dinero(precio_desde, moneda)}</strong></p>
        ) : (
          <p className="precio precio--sin"><span>Precios</span><strong>En la boletera</strong></p>
        )}
        <Link className="boton" to={enlace} state={estado}>
          Ver boletos<span className="solo-lector"> de {artista.nombre}</span>
        </Link>
      </div>
    </li>
  );
}

/** Boletos grises mientras llegan los datos. */
export function BoletosCargando({ cantidad = 3 }) {
  return (
    <ol className="boletos" aria-hidden="true">
      {Array.from({ length: cantidad }, (_, i) => (
        <li key={i} className="boleto boleto--cargando">
          <div className="boleto__fecha"><span className="esqueleto" style={{ width: 44, height: 64 }} /></div>
          <div className="boleto__cartel esqueleto" />
          <div className="boleto__info">
            <span className="esqueleto" style={{ width: '60%', height: 30 }} />
            <span className="esqueleto" style={{ width: '40%', height: 16 }} />
          </div>
          <div className="boleto__accion"><span className="esqueleto" style={{ width: 140, height: 48, borderRadius: 999 }} /></div>
        </li>
      ))}
    </ol>
  );
}
