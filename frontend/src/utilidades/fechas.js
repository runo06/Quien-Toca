// Fechas siempre en la hora de México, sin importar la zona horaria de quien visita.
const ZONA = 'America/Mexico_City';

function formatear(fechaIso, opciones) {
  return new Intl.DateTimeFormat('es-MX', { timeZone: ZONA, ...opciones }).format(new Date(fechaIso));
}

const capitalizar = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);
const sinPunto = (texto) => texto.replace('.', '');

/** "Sáb" */
export const diaSemanaCorto = (iso) => capitalizar(sinPunto(formatear(iso, { weekday: 'short' })));

/** "20" */
export const diaDelMes = (iso) => formatear(iso, { day: 'numeric' });

/** "nov" */
export const mesCorto = (iso) => sinPunto(formatear(iso, { month: 'short' }));

/** "20 nov" */
export const fechaCorta = (iso) => `${diaDelMes(iso)} ${mesCorto(iso)}`;

/** "20 nov 2026" */
export const fechaMedia = (iso) => `${fechaCorta(iso)} ${formatear(iso, { year: 'numeric' })}`;

/** "Viernes 20 de noviembre de 2026" */
export const fechaLarga = (iso) =>
  capitalizar(formatear(iso, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).replace(',', ''));

/** "9:00 p.m." */
export const hora = (iso) => formatear(iso, { hour: 'numeric', minute: '2-digit', hour12: true });

/** "19:00:00" (hora sin fecha, como la manda Django) -> "7:00 p.m." */
export function horaSimple(texto) {
  const [h, m] = texto.split(':').map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'a.m.' : 'p.m.'}`;
}

/** Hoy en México como "AAAA-MM-DD". (en-CA usa justo ese formato) */
export const hoyEnMexico = () => new Intl.DateTimeFormat('en-CA', { timeZone: ZONA }).format(new Date());

/** Suma días a una fecha "AAAA-MM-DD". Se calcula en UTC para evitar líos de horario. */
export function sumarDias(fecha, dias) {
  const d = new Date(`${fecha}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

/** 0 = domingo ... 6 = sábado */
export const diaDeLaSemana = (fecha) => new Date(`${fecha}T12:00:00Z`).getUTCDay();
