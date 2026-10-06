import { useSyncExternalStore } from 'react';
import { suscribirseASesion, usuarioActual } from '../api.js';

/** El usuario con sesión iniciada ({ id, nombre, email }) o null. Se actualiza al entrar o salir. */
export function usarSesion() {
  return useSyncExternalStore(suscribirseASesion, usuarioActual);
}
