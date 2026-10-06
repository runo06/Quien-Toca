import Icono from '../Icono.jsx';

/** Cinco estrellas, encendidas hasta el valor. El lector de pantalla oye "4 de 5 estrellas". */
export default function Estrellas({ valor }) {
  return (
    <span className="estrellas" role="img" aria-label={`${valor} de 5 estrellas`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= valor ? 'on' : undefined}><Icono nombre="estrella" /></span>
      ))}
    </span>
  );
}
