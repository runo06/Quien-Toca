const formatosDinero = {};

/** 780 -> "$780". Sin centavos: es un precio de referencia. */
export function dinero(cantidad, moneda = 'MXN') {
  formatosDinero[moneda] ??= new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: moneda,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  return formatosDinero[moneda].format(cantidad);
}

/** plural(1, 'concierto', 'conciertos') -> "1 concierto" */
export const plural = (n, uno, varios) => `${n.toLocaleString('es-MX')} ${n === 1 ? uno : varios}`;

/** ['A', 'B', 'C'] -> "A, B y C" */
export const listaConY = (nombres) => new Intl.ListFormat('es', { type: 'conjunction' }).format(nombres);

/** El texto bajo el artista: la gira, o el título si dice algo más que el nombre. */
export function subtituloDe(concierto) {
  if (concierto.gira) return concierto.gira;
  return concierto.titulo.trim().toLowerCase() !== concierto.artista.nombre.trim().toLowerCase()
    ? concierto.titulo
    : '';
}
