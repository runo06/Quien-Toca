// Contexto: las ciudades se piden una sola vez y cualquier componente puede leerlas
// con usarCiudades(), sin pasarlas como prop de componente en componente.
import { createContext, useContext } from 'react';
import { obtenerCiudades } from '../api.js';
import { usarPeticion } from '../hooks/usarPeticion.js';

const ContextoCiudades = createContext(null);

export function ProveedorCiudades({ children }) {
  const peticion = usarPeticion(obtenerCiudades, []);
  return <ContextoCiudades.Provider value={peticion}>{children}</ContextoCiudades.Provider>;
}

/** Devuelve { datos, cargando, error, reintentar }. datos es la lista de ciudades. */
export function usarCiudades() {
  return useContext(ContextoCiudades);
}

const CLAVE_CIUDAD = 'quien-toca:ciudad';

// localStorage puede fallar (modo privado, almacenamiento bloqueado): por eso el try.
export function leerCiudadGuardada() {
  try {
    return localStorage.getItem(CLAVE_CIUDAD);
  } catch {
    return null;
  }
}

export function guardarCiudad(slug) {
  try {
    localStorage.setItem(CLAVE_CIUDAD, slug);
  } catch {
    // sin almacenamiento: la próxima vez se usa la ciudad predeterminada
  }
}
