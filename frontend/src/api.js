// Todas las llamadas al backend en un solo lugar.
// En desarrollo la base es /api (Vite la reenvía a Django); en producción,
// VITE_API_URL apunta al backend publicado.
const BASE = import.meta.env.VITE_API_URL ?? '/api';

export class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.estado = estado; // 0 = sin conexión, 404, 500...
  }
}

// --- Aviso de "el servidor está despertando" ---
// El backend gratuito de Render se duerme tras 15 minutos sin visitas y tarda
// alrededor de un minuto en despertar. Mientras tanto Render puede tardar en
// responder, contestar 502/503 o cortar la conexión.
const ESPERA_ANTES_DEL_AVISO = 4000; // ms: menos que esto es una carga normal
const PAUSA_ENTRE_INTENTOS = 3000;
const LIMITE_DE_ESPERA = 90000; // tras esto se rinde y muestra el error
const ESTADOS_DE_ARRANQUE = new Set([502, 503, 504]);

let peticionesLentas = 0;
const oyentes = new Set();

function cambiarLentas(delta) {
  peticionesLentas += delta;
  oyentes.forEach((oyente) => oyente());
}

/** Para useSyncExternalStore: avisa cuando cambia si hay peticiones lentas. */
export function suscribirseALentitud(oyente) {
  oyentes.add(oyente);
  return () => oyentes.delete(oyente);
}
export const hayPeticionesLentas = () => peticionesLentas > 0;

function esperar(ms, signal) {
  return new Promise((resolver, rechazar) => {
    const temporizador = setTimeout(resolver, ms);
    signal?.addEventListener('abort', () => {
      clearTimeout(temporizador);
      rechazar(new DOMException('Cancelada', 'AbortError'));
    }, { once: true });
  });
}

/** Un intento: devuelve la respuesta o lanza ErrorApi con estado 0 si no hubo conexión. */
async function intentar(url, signal) {
  try {
    return await fetch(url, { signal, headers: { Accept: 'application/json' } });
  } catch (error) {
    if (error.name === 'AbortError') throw error; // cancelada a propósito: no es un error real
    throw new ErrorApi('No pudimos conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.', 0);
  }
}

/** Reintenta mientras el servidor parezca estar arrancando, hasta LIMITE_DE_ESPERA. */
async function pedirConPaciencia(url, signal) {
  const inicio = Date.now();
  for (;;) {
    let respuesta;
    try {
      respuesta = await intentar(url, signal);
      if (!ESTADOS_DE_ARRANQUE.has(respuesta.status)) return respuesta;
    } catch (error) {
      // Sin internet en el equipo no es que el servidor duerma: no tiene caso esperar.
      if (error.name === 'AbortError' || !navigator.onLine) throw error;
    }
    if (Date.now() - inicio + PAUSA_ENTRE_INTENTOS > LIMITE_DE_ESPERA) {
      if (respuesta) return respuesta; // el error se reporta abajo, con su estado
      throw new ErrorApi('No pudimos conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.', 0);
    }
    await esperar(PAUSA_ENTRE_INTENTOS, signal);
  }
}

async function pedir(ruta, { parametros = {}, signal } = {}) {
  const url = new URL(BASE + ruta, window.location.origin);
  for (const [nombre, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== null && valor !== '') url.searchParams.set(nombre, valor);
  }

  let esLenta = false;
  const temporizador = setTimeout(() => {
    esLenta = true;
    cambiarLentas(+1);
  }, ESPERA_ANTES_DEL_AVISO);

  let respuesta;
  try {
    respuesta = await pedirConPaciencia(url, signal);
  } finally {
    clearTimeout(temporizador);
    if (esLenta) cambiarLentas(-1);
  }

  if (!respuesta.ok) {
    const mensaje = respuesta.status === 404
      ? 'No encontramos lo que buscas.'
      : 'El servidor tuvo un problema. Inténtalo de nuevo en un momento.';
    throw new ErrorApi(mensaje, respuesta.status);
  }
  return respuesta.json();
}

export const obtenerCiudades = (signal) => pedir('/ciudades/', { signal });

export const obtenerConciertos = (parametros, signal) => pedir('/conciertos/', { parametros, signal });

export const obtenerConcierto = (slug, signal) => pedir(`/conciertos/${encodeURIComponent(slug)}/`, { signal });
