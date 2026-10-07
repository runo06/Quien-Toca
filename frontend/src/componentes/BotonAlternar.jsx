import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { usarSesion } from '../hooks/usarSesion.js';
import { avisar } from './AvisoFlotante.jsx';

/**
 * Botón de dos estados que necesita sesión ("Seguir" / "Siguiendo", "Guardar" / "Guardado").
 * Sin sesión lleva a /entrar y vuelve aquí. alternar(nuevoValor) llama a la API y
 * devuelve la respuesta; el botón cambia al instante y se corrige si la API falla.
 */
export default function BotonAlternar({ activo: activoInicial, alternar, textos, alCambiar }) {
  const usuario = usarSesion();
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const [activo, setActivo] = useState(activoInicial);
  const [ocupado, setOcupado] = useState(false);

  async function alPulsar() {
    if (!usuario) {
      navegar('/entrar', { state: { desde: ubicacion.pathname + ubicacion.search } });
      return;
    }
    const nuevo = !activo;
    setActivo(nuevo); // respuesta inmediata; se revierte si falla
    setOcupado(true);
    try {
      const datos = await alternar(nuevo);
      alCambiar?.(datos);
      if (textos.aviso) avisar(nuevo ? textos.aviso[0] : textos.aviso[1]);
    } catch (error) {
      setActivo(!nuevo);
      avisar(error.message);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <button
      type="button" className={`boton ${activo ? 'boton--linea' : ''} boton--chico`}
      aria-pressed={activo} disabled={ocupado} onClick={alPulsar}
    >
      {activo ? textos.activo : textos.inactivo}
    </button>
  );
}
