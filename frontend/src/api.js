// Todas las llamadas al backend en un solo lugar.
// En desarrollo la base es /api (Vite la reenvía a Django); en producción,
// VITE_API_URL apunta al backend publicado.
const BASE = import.meta.env.VITE_API_URL ?? '/api';

export class ErrorApi extends Error {
  constructor(mensaje, estado, campos = {}) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.estado = estado; // 0 = sin conexión, 404, 500...
    this.campos = campos; // errores por campo de un 400: { texto: ['Escribe al menos...'] }
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
const SIN_CONEXION = 'No pudimos conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.';

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
async function intentar(url, opciones) {
  try {
    return await fetch(url, opciones);
  } catch (error) {
    if (error.name === 'AbortError') throw error; // cancelada a propósito: no es un error real
    throw new ErrorApi(SIN_CONEXION, 0);
  }
}

/** Reintenta mientras el servidor parezca estar arrancando, hasta LIMITE_DE_ESPERA. */
async function pedirConPaciencia(url, opciones) {
  const inicio = Date.now();
  for (;;) {
    let respuesta;
    try {
      respuesta = await intentar(url, opciones);
      if (!ESTADOS_DE_ARRANQUE.has(respuesta.status)) return respuesta;
    } catch (error) {
      // Sin internet en el equipo no es que el servidor duerma: no tiene caso esperar.
      if (error.name === 'AbortError' || !navigator.onLine) throw error;
    }
    if (Date.now() - inicio + PAUSA_ENTRE_INTENTOS > LIMITE_DE_ESPERA) {
      if (respuesta) return respuesta; // el error se reporta abajo, con su estado
      throw new ErrorApi(SIN_CONEXION, 0);
    }
    await esperar(PAUSA_ENTRE_INTENTOS, opciones.signal);
  }
}

// --- Sesión ---
// El token de acceso (dura 15 min) vive solo en memoria. El de renovación (30 días)
// se guarda en localStorage para no pedir la contraseña en cada visita; con él se
// pide un access nuevo cuando hace falta. Cada renovación entrega otro refresh y
// el viejo queda anulado en el servidor.
const CLAVE_SESION = 'quien-toca:sesion';
let access = null;
let sesion = leerSesionGuardada(); // { refresh, usuario } o null
const oyentesSesion = new Set();

function leerSesionGuardada() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_SESION));
  } catch {
    return null; // modo privado o dato corrupto: sin sesión
  }
}

function guardarSesion(nueva) {
  sesion = nueva;
  try {
    if (nueva) localStorage.setItem(CLAVE_SESION, JSON.stringify(nueva));
    else localStorage.removeItem(CLAVE_SESION);
  } catch {
    // sin almacenamiento: la sesión dura mientras la pestaña siga abierta
  }
  oyentesSesion.forEach((oyente) => oyente());
}

/** Para useSyncExternalStore: avisa cuando alguien entra o sale. */
export function suscribirseASesion(oyente) {
  oyentesSesion.add(oyente);
  return () => oyentesSesion.delete(oyente);
}
export const usuarioActual = () => sesion?.usuario ?? null;

function abrirSesion({ access: nuevoAccess, refresh, usuario }) {
  access = nuevoAccess;
  guardarSesion({ refresh, usuario });
  return usuario;
}

function cerrarSesionLocal() {
  access = null;
  guardarSesion(null);
}

// Si la sesión se cierra o se abre en otra pestaña, esta se entera.
window.addEventListener('storage', (evento) => {
  if (evento.key !== CLAVE_SESION) return;
  access = null;
  sesion = leerSesionGuardada();
  oyentesSesion.forEach((oyente) => oyente());
});

let renovando = null;

/** Pide un access nuevo con el refresh. Varias peticiones a la vez comparten la misma renovación. */
function renovarAccess() {
  renovando ??= (async () => {
    // Se lee de localStorage: otra pestaña pudo haberlo renovado (y anulado el que teníamos).
    const refresh = leerSesionGuardada()?.refresh ?? sesion?.refresh;
    if (!refresh) return false;
    try {
      const datos = await enviar('/cuentas/renovar/', { metodo: 'POST', cuerpo: { refresh } });
      access = datos.access;
      guardarSesion({ ...sesion, refresh: datos.refresh });
      return true;
    } catch (error) {
      if (error.estado === 401) cerrarSesionLocal(); // caducó o fue anulado: hay que volver a entrar
      return false;
    } finally {
      renovando = null;
    }
  })();
  return renovando;
}

const MENSAJES = {
  401: 'Tu sesión terminó. Vuelve a iniciar sesión.',
  403: 'No tienes permiso para hacer eso.',
  404: 'No encontramos lo que buscas.',
  429: 'Demasiados intentos seguidos. Espera un minuto y vuelve a probar.',
};

/** Una petición sin lógica de sesión: arma la dirección, avisa si tarda y traduce los errores. */
async function enviar(ruta, { metodo = 'GET', cuerpo, parametros = {}, signal, token } = {}) {
  const url = new URL(BASE + ruta, window.location.origin);
  for (const [nombre, valor] of Object.entries(parametros)) {
    if (valor !== undefined && valor !== null && valor !== '') url.searchParams.set(nombre, valor);
  }
  const cabeceras = { Accept: 'application/json' };
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';
  if (token) cabeceras.Authorization = `Bearer ${token}`;
  const opciones = { method: metodo, headers: cabeceras, signal, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) };

  let esLenta = false;
  const temporizador = setTimeout(() => {
    esLenta = true;
    cambiarLentas(+1);
  }, ESPERA_ANTES_DEL_AVISO);

  let respuesta;
  try {
    respuesta = await pedirConPaciencia(url, opciones);
  } finally {
    clearTimeout(temporizador);
    if (esLenta) cambiarLentas(-1);
  }

  const datos = await respuesta.json().catch(() => null); // 204 y 205 no traen cuerpo
  if (!respuesta.ok) {
    const mensaje = datos?.detail
      ?? MENSAJES[respuesta.status]
      ?? (respuesta.status === 400 ? 'Revisa los datos marcados.' : 'El servidor tuvo un problema. Inténtalo de nuevo en un momento.');
    throw new ErrorApi(mensaje, respuesta.status, respuesta.status === 400 ? datos ?? {} : {});
  }
  return datos;
}

/** Como enviar, pero con la sesión: agrega el token y, si caducó, lo renueva y reintenta una vez. */
async function pedir(ruta, opciones = {}) {
  if (sesion && !access) await renovarAccess(); // recién abierta la página: aún no hay access
  const token = access;
  try {
    return await enviar(ruta, { ...opciones, token });
  } catch (error) {
    if (error.estado !== 401 || !token) throw error;
    const renovado = await renovarAccess();
    if (!renovado && sesion) throw error; // no se pudo renovar (sin conexión): se respeta el error
    // Renovado: con el token nuevo. Si la sesión se cerró, como visitante: lo público sigue sirviendo.
    return enviar(ruta, { ...opciones, token: access });
  }
}

// --- Conciertos ---
export const obtenerCiudades = (signal) => pedir('/ciudades/', { signal });

export const obtenerConciertos = (parametros, signal) => pedir('/conciertos/', { parametros, signal });

export const obtenerConcierto = (slug, signal) => pedir(`/conciertos/${encodeURIComponent(slug)}/`, { signal });

export const obtenerArtista = (slug, signal) => pedir(`/artistas/${encodeURIComponent(slug)}/`, { signal });

/** parametros: { ciudad, q, pagina } */
export const obtenerRecintos = (parametros, signal) => pedir('/recintos/', { parametros, signal });

export const obtenerRecinto = (slug, signal) => pedir(`/recintos/${encodeURIComponent(slug)}/`, { signal });

// --- Cuentas ---
export const registrarse = async (datos) =>
  abrirSesion(await enviar('/cuentas/registro/', { metodo: 'POST', cuerpo: datos }));

export const entrar = async (email, password) =>
  abrirSesion(await enviar('/cuentas/entrar/', { metodo: 'POST', cuerpo: { email, password } }));

export async function salir() {
  const refresh = sesion?.refresh;
  cerrarSesionLocal(); // en este equipo se cierra aunque el servidor no conteste
  if (refresh) await enviar('/cuentas/salir/', { metodo: 'POST', cuerpo: { refresh } }).catch(() => {});
}

// --- Reseñas ---
/** parametros: { concierto, artista, recinto, ciudad, pagina } */
export const obtenerResenas = (parametros, signal) => pedir('/resenas/', { parametros, signal });

export const obtenerMisResenas = (signal) => pedir('/resenas/mias/', { signal });

export const crearResena = (datos) => pedir('/resenas/', { metodo: 'POST', cuerpo: datos });

export const editarResena = (id, datos) => pedir(`/resenas/${id}/`, { metodo: 'PATCH', cuerpo: datos });

export const borrarResena = (id) => pedir(`/resenas/${id}/`, { metodo: 'DELETE' });

/** Marca (true) o quita (false) el "Me sirvió". Devuelve { utiles, me_sirvio }. */
export const marcarMeSirvio = (id, marcar) => pedir(`/resenas/${id}/util/`, { metodo: marcar ? 'POST' : 'DELETE' });

export const reportarResena = (id, datos) => pedir(`/resenas/${id}/reportar/`, { metodo: 'POST', cuerpo: datos });
