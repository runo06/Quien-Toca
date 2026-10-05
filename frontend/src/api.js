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

async function pedir(ruta, { parametros = {}, signal } = {}) {
  const url = new URL(BASE + ruta, window.location.origin);
  for (const [nombre, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== null && valor !== '') url.searchParams.set(nombre, valor);
  }

  let respuesta;
  try {
    respuesta = await fetch(url, { signal, headers: { Accept: 'application/json' } });
  } catch (error) {
    if (error.name === 'AbortError') throw error; // cancelada a propósito: no es un error real
    throw new ErrorApi('No pudimos conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.', 0);
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
