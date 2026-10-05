// Los íconos del prototipo como componentes: <Icono nombre="estrella" />.
const TRAZOS = {
  estrella: <path fill="currentColor" d="M12 2.6l2.84 5.98 6.56.86-4.8 4.56 1.2 6.5L12 17.4 6.2 20.5l1.2-6.5-4.8-4.56 6.56-.86z" />,
  abajo: <path fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" d="M5 9l7 7 7-7" />,
  atras: <path fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" d="M15 5l-7 7 7 7" />,
  fuera: (
    <path
      fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"
      d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"
    />
  ),
};

export default function Icono({ nombre }) {
  // aria-hidden: es decoración; el texto del botón o enlace ya dice qué hace.
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {TRAZOS[nombre]}
    </svg>
  );
}
