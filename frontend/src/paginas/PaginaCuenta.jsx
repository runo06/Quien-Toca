import { useId, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router';
import { entrar, registrarse } from '../api.js';
import { avisar } from '../componentes/AvisoFlotante.jsx';
import { usarSesion } from '../hooks/usarSesion.js';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import './PaginaCuenta.css';

/** Un campo con su etiqueta y su error, enlazados para el lector de pantalla. */
function Campo({ etiqueta, error, ayuda, ...entrada }) {
  const id = useId();
  const descripcion = [error && `${id}-error`, ayuda && `${id}-ayuda`].filter(Boolean).join(' ') || undefined;
  return (
    <div className="campo">
      <label htmlFor={id}>{etiqueta}</label>
      <input
        className="entrada" id={id} aria-invalid={Boolean(error)} aria-describedby={descripcion} {...entrada}
      />
      {ayuda && <p className="letra-chica" id={`${id}-ayuda`} style={{ margin: 0 }}>{ayuda}</p>}
      {error && <p className="error" id={`${id}-error`}>{error}</p>}
    </div>
  );
}

/**
 * /entrar y /registro: el mismo formulario con un campo más.
 * Al terminar vuelve a donde estabas (state.desde), p. ej. al concierto que querías reseñar.
 */
export default function PaginaCuenta({ modo }) {
  const esRegistro = modo === 'registro';
  const usuario = usarSesion();
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const destino = ubicacion.state?.desde ?? '/';
  const [valores, setValores] = useState({ nombre: '', email: '', password: '' });
  const [errores, setErrores] = useState({});
  const [enviando, setEnviando] = useState(false);

  usarTituloDocumento(esRegistro ? 'Crear cuenta · ¿Quién toca?' : 'Iniciar sesión · ¿Quién toca?');

  if (usuario && !enviando) return <Navigate to={destino} replace />;

  const cambiar = (campo) => (evento) => {
    setValores((actuales) => ({ ...actuales, [campo]: evento.target.value }));
    setErrores((actuales) => ({ ...actuales, [campo]: undefined })); // al corregir, se quita su error
  };

  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setErrores({});
    try {
      const nuevo = esRegistro
        ? await registrarse(valores)
        : await entrar(valores.email, valores.password);
      avisar(esRegistro ? `¡Listo, ${nuevo.nombre}! Ya tienes cuenta.` : `Hola de nuevo, ${nuevo.nombre}`);
      navegar(destino, { replace: true });
    } catch (error) {
      // Django manda una lista de mensajes por campo; se muestra el primero.
      const primero = (campo) => [].concat(error.campos?.[campo] ?? [])[0];
      setErrores({
        nombre: primero('nombre'),
        email: primero('email'),
        password: [].concat(error.campos?.password ?? []).join(' ') || undefined,
        general: Object.keys(error.campos ?? {}).length ? undefined : error.message,
      });
      setEnviando(false);
    }
  }

  return (
    <div className="centro cuenta">
      <form className="formulario cuenta__caja" onSubmit={enviar} noValidate aria-busy={enviando}>
        <h1 className="cartel" id="titulo-vista" tabIndex={-1}>{esRegistro ? 'Crea tu cuenta' : 'Inicia sesión'}</h1>
        <p className="apagado">
          {esRegistro
            ? 'Con tu cuenta puedes reseñar los conciertos a los que fuiste y marcar las reseñas que te sirvieron.'
            : 'Para reseñar conciertos y marcar las reseñas que te sirvieron.'}
        </p>
        {errores.general && <p className="error" role="alert">{errores.general}</p>}
        {esRegistro && (
          <Campo
            etiqueta="Tu nombre" ayuda="Así aparecerá en tus reseñas. Ej. Sofía M." autoComplete="name"
            value={valores.nombre} onChange={cambiar('nombre')} error={errores.nombre} required
          />
        )}
        <Campo
          etiqueta="Correo" type="email" autoComplete="email" inputMode="email"
          value={valores.email} onChange={cambiar('email')} error={errores.email} required
        />
        <Campo
          etiqueta="Contraseña" type="password" autoComplete={esRegistro ? 'new-password' : 'current-password'}
          ayuda={esRegistro ? 'Al menos 8 caracteres, que no sea fácil de adivinar.' : undefined}
          value={valores.password} onChange={cambiar('password')} error={errores.password} required
        />
        <div className="formulario__pie">
          <button type="submit" className="boton" disabled={enviando}>
            {enviando ? 'Un momento…' : esRegistro ? 'Crear cuenta' : 'Entrar'}
          </button>
        </div>
        <p>
          {esRegistro ? '¿Ya tienes cuenta? ' : '¿Aún no tienes cuenta? '}
          <Link className="enlace" to={esRegistro ? '/entrar' : '/registro'} state={ubicacion.state} replace>
            {esRegistro ? 'Inicia sesión' : 'Crea una'}
          </Link>
        </p>
      </form>
    </div>
  );
}
