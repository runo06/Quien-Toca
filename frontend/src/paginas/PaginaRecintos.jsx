import { useCallback, useEffect, useState } from 'react';
import { Link, Navigate, useParams, useSearchParams } from 'react-router';
import { obtenerRecintos } from '../api.js';
import Buscador from '../componentes/inicio/Buscador.jsx';
import MensajeError from '../componentes/MensajeError.jsx';
import { leerCiudadGuardada, usarCiudades } from '../contexto/ciudades.jsx';
import { usarTituloDocumento } from '../hooks/usarTituloDocumento.js';
import { plural } from '../utilidades/texto.js';
import PaginaNoEncontrada from './PaginaNoEncontrada.jsx';
import '../componentes/perfil/Perfil.css';
import './PaginaInicio.css';

/** Recintos de una ciudad, con "Ver más". Se vuelve a pedir si cambia la ciudad o el texto. */
function usarRecintos(ciudad, q) {
  const [estado, setEstado] = useState({ lista: [], total: 0, pagina: 1, hayMas: false, cargando: true, error: null });
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    const control = new AbortController();
    setEstado((e) => ({ ...e, cargando: true, error: null }));
    obtenerRecintos({ ciudad, q, pagina: 1 }, control.signal)
      .then((d) => setEstado({ lista: d.resultados, total: d.total, pagina: 1, hayMas: Boolean(d.siguiente), cargando: false, error: null }))
      .catch((error) => { if (error.name !== 'AbortError') setEstado((e) => ({ ...e, cargando: false, error })); });
    return () => control.abort();
  }, [ciudad, q, intento]);

  const verMas = useCallback(async () => {
    setEstado((e) => ({ ...e, cargando: true }));
    try {
      const d = await obtenerRecintos({ ciudad, q, pagina: estado.pagina + 1 });
      setEstado((e) => ({ ...e, lista: [...e.lista, ...d.resultados], pagina: e.pagina + 1, hayMas: Boolean(d.siguiente), cargando: false }));
    } catch (error) {
      setEstado((e) => ({ ...e, cargando: false, error }));
    }
  }, [ciudad, q, estado.pagina]);

  return { ...estado, verMas, reintentar: () => setIntento((n) => n + 1) };
}

/** /recintos/:ciudad?q=texto */
export default function PaginaRecintos() {
  const { ciudad: slugCiudad } = useParams();
  const [parametros, setParametros] = useSearchParams();
  const ciudades = usarCiudades();
  const q = parametros.get('q') ?? '';
  const recintos = usarRecintos(slugCiudad, q.trim());
  const ciudad = ciudades.datos?.find((c) => c.slug === slugCiudad);
  usarTituloDocumento(ciudad ? `Recintos de ${ciudad.nombre} · ¿Quién toca?` : '¿Quién toca?');

  const cambiarTexto = useCallback(
    (valor) => setParametros(valor ? { q: valor } : {}, { replace: true }),
    [setParametros],
  );

  if (ciudades.cargando) return <div className="centro pagina-estado"><p role="status" className="apagado">Cargando…</p></div>;
  if (ciudades.error) return <div className="centro pagina-estado"><MensajeError error={ciudades.error} alReintentar={ciudades.reintentar} /></div>;
  if (!slugCiudad) {
    // /recintos a secas: la ciudad de la última visita o la predeterminada.
    const guardada = leerCiudadGuardada();
    const destino = ciudades.datos.find((c) => c.slug === guardada) ?? ciudades.datos.find((c) => c.es_predeterminada);
    return <Navigate to={`/recintos/${destino.slug}`} replace />;
  }
  if (!ciudad) return <PaginaNoEncontrada />;

  return (
    <section className="centro perfil">
      <h1 className="cartel t-seccion" id="titulo-vista" tabIndex={-1} style={{ marginTop: 24 }}>Recintos de {ciudad.nombre}</h1>
      <p className="apagado" style={{ marginTop: 10, maxWidth: '36em' }}>
        Elige un lugar para ver sus próximos conciertos y los que ya pasaron.
      </p>
      <div className="fichas" role="group" aria-label="Ciudad" style={{ marginTop: 22 }}>
        {ciudades.datos.map((c) => (
          <Link key={c.slug} className="ficha ficha--enlace" to={`/recintos/${c.slug}`} aria-current={c.slug === slugCiudad ? 'page' : undefined}>
            {c.nombre}
          </Link>
        ))}
      </div>
      <div style={{ marginTop: 18, maxWidth: 520 }}>
        <Buscador valor={q} alCambiar={cambiarTexto} etiqueta="Busca un recinto" ejemplo="Ej. Auditorio Nacional" />
      </div>

      {recintos.error && <div style={{ marginTop: 24 }}><MensajeError error={recintos.error} alReintentar={recintos.reintentar} /></div>}
      {!recintos.error && !recintos.cargando && !recintos.lista.length && (
        <div className="vacio" style={{ marginTop: 24 }}>
          <p>{q ? `Ningún recinto de ${ciudad.nombre} coincide con «${q}».` : `Todavía no hay conciertos registrados en ${ciudad.nombre}.`}</p>
        </div>
      )}
      <p className="solo-lector" role="status">{recintos.cargando ? 'Cargando recintos…' : plural(recintos.total, 'recinto', 'recintos')}</p>
      <ul className={`recintos__lista${recintos.cargando ? ' boletos--actualizando' : ''}`}>
        {recintos.lista.map((r) => (
          <li key={r.slug}>
            <Link className="recinto-tarjeta" to={`/recinto/${r.slug}`}>
              <h2 className="cartel">{r.nombre}</h2>
              {r.direccion && <p>{r.direccion}</p>}
              {r.proximos
                ? <strong>{plural(r.proximos, 'concierto próximo', 'conciertos próximos')}</strong>
                : <strong className="sin">Sin conciertos próximos · {plural(r.pasados, 'pasado', 'pasados')}</strong>}
            </Link>
          </li>
        ))}
      </ul>
      {recintos.hayMas && !recintos.cargando && (
        <button type="button" className="boton boton--linea" style={{ marginTop: 18 }} onClick={recintos.verMas}>Ver más recintos</button>
      )}
    </section>
  );
}
