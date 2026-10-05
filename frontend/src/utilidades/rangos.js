import { diaDeLaSemana, hoyEnMexico, sumarDias } from './fechas.js';

// Las fichas de fecha. "valor" es lo que aparece en la dirección: ?fechas=30-dias
export const RANGOS = [
  { valor: 'fin-de-semana', etiqueta: 'Este fin de semana' },
  { valor: '30-dias', etiqueta: 'Próximos 30 días' },
  { valor: '3-meses', etiqueta: 'Próximos 3 meses' },
  { valor: 'todas', etiqueta: 'Cualquier fecha' },
];

export const RANGO_POR_DEFECTO = '3-meses';

export const esRangoValido = (valor) => RANGOS.some((r) => r.valor === valor);

/** Convierte una ficha en { desde, hasta } (texto "AAAA-MM-DD" o undefined). */
export function rangoDeFechas(valor, hoy = hoyEnMexico()) {
  switch (valor) {
    case 'fin-de-semana': {
      // De viernes a domingo. Si hoy ya es viernes, sábado o domingo, desde hoy.
      const dia = diaDeLaSemana(hoy);
      const desde = dia === 0 || dia >= 5 ? hoy : sumarDias(hoy, 5 - dia);
      return { desde, hasta: sumarDias(hoy, (7 - dia) % 7) };
    }
    case '30-dias':
      return { desde: hoy, hasta: sumarDias(hoy, 30) };
    case 'todas':
      return { desde: undefined, hasta: undefined };
    default:
      return { desde: hoy, hasta: sumarDias(hoy, 92) };
  }
}
