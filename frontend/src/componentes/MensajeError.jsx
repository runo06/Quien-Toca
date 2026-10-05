/** Caja de error con botón para reintentar. role="alert" hace que el lector de pantalla la anuncie. */
export default function MensajeError({ error, alReintentar }) {
  return (
    <div className="vacio vacio--error" role="alert">
      <p>{error?.message ?? 'Algo salió mal.'}</p>
      {alReintentar && (
        <button type="button" className="boton boton--linea" onClick={alReintentar}>
          Reintentar
        </button>
      )}
    </div>
  );
}
