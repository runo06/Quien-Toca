# Fase 0: hallazgos sobre los datos de Ticketmaster

Consulta del 4 de octubre de 2026: conciertos de música en México
(`countryCode=MX`, `classificationName=music`) de los próximos 12 meses.
Se usaron 14 llamadas de las 5,000 diarias.

## Cuántos conciertos hay

| Ciudad (zona metropolitana) | Conciertos | Cómo la escribe Ticketmaster |
|---|---:|---|
| Ciudad de México | 475 | "Ciudad de México", "México", "Mexico", "México CDMX", alcaldías |
| Monterrey | 109 | "Monterrey", "Col. Centro Monterrey", "Guadalupe" |
| Guadalajara | 80 | "Zapopan" (58), "Guadalajara", "Tlajomulco de Zuñiga" |
| Puebla | **0** | — |
| Tlaxcala | **0** | — |
| Otras | 44 | Sobre todo Guanajuato (31) |

Total: 708 conciertos. Ticketmaster no tiene eventos en los estados de Puebla
ni de Tlaxcala; ahí se venden por otras boleteras.

## Qué campos vienen (664 eventos de las 5 ciudades)

- **Siempre (95–100 %):** id, nombre, enlace, fecha, hora, zona horaria,
  estado, imágenes, género, recinto completo (dirección, ciudad, estado,
  código postal, coordenadas) y artista con id.
- **Nunca (0 %):** `priceRanges`. No hay ningún precio.
- **A veces:** mapa de zonas (55 %), taquilla del recinto (76 %).
- **Texto libre de poca utilidad:** `pleaseNote` (98 %) es casi siempre el
  mismo aviso de entrega y edad. La apertura de puertas aparece en 9 %.
- La gira aparece en el nombre en 9 % de los eventos.

## Detalles que afectan al diseño

- **Complementos:** hay eventos que no son el concierto en sí, como
  "Aquihayaquihay VIP+MEET&GREET" o "Abono Banamex Stage Vip". Comparten
  artista, recinto y día con el concierto real (27 grupos).
- **Varios artistas por evento:** 116 eventos traen más de un artista
  (festivales y teloneros).
- **Imágenes genéricas:** 205 imágenes tienen `fallback: true`. Son
  marcadores de Ticketmaster, no el cartel del evento.
- **Idioma:** todo llega en `en-us` aunque se pida otro idioma. Los géneros
  vienen en inglés ("Latin", "Ballads/Romantic").
- **Cancelados:** 13 eventos con estado `cancelled`.
- **Enlaces:** 704 apuntan a ticketmaster.com.mx y 4 a otra boletera (fgtix).

## Términos de uso

https://developer.ticketmaster.com/support/terms-of-use/

- Guardar contenido solo por periodos razonables para dar el servicio.
- Borrar contenido en 24 horas si el dueño lo pide.
- No generar ingresos con la API ni replicar la experiencia de Ticketmaster.
- Publicar una política de privacidad.

## Decisiones

1. Ticketmaster alcanza como fuente principal para CDMX, Guadalajara y
   Monterrey. Puebla y Tlaxcala dependen por completo de la captura manual.
2. Cada ciudad es una zona metropolitana; el concierto se asigna por las
   coordenadas del recinto.
3. Precio opcional. Si no hay precio: "Consulta precios en la boletera".
4. Concierto ↔ artista es de muchos a muchos, con un artista principal.
5. La importación descarta complementos (VIP, estacionamiento, abonos) y no
   usa imágenes `fallback`.
6. Los géneros se traducen al español con una tabla propia.
7. Imágenes enlazadas, no descargadas. En conciertos pasados se conservan
   artista, recinto y fecha para las reseñas.
8. Se mantienen las 5 ciudades. La ciudad por defecto es Ciudad de México;
   Puebla y Tlaxcala se llenan con captura manual y sugerencias.
9. El orden por precio se conserva; los conciertos sin precio van al final.
