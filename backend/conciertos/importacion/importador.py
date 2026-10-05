"""Guarda en la base los eventos de Ticketmaster sin duplicar.

Regla de oro: el id de Ticketmaster identifica a cada concierto, recinto y
artista. Si ya existe se actualiza; si no, se crea. Nunca se borra nada.
"""
from collections import Counter
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from conciertos.models import Artista, Ciudad, Concierto, Recinto

from .traducir import Descartado, traducir_evento


@dataclass
class Resumen:
    creados: int = 0
    actualizados: int = 0
    sin_cambios: int = 0
    descartados: Counter = field(default_factory=Counter)
    nombres_descartados: list = field(default_factory=list)
    errores: list = field(default_factory=list)


class Importador:
    def __init__(self, ahora=None):
        self.ciudades = list(Ciudad.objects.all())
        self.ahora = ahora or timezone.now()
        self.resumen = Resumen()

    def importar(self, eventos):
        for evento in eventos:
            try:
                datos = traducir_evento(evento, self.ciudades)
                # Cada concierto en su propia transacción: si falla, se deshace
                # solo ese y la importación sigue con los demás.
                with transaction.atomic():
                    resultado = self._guardar_concierto(datos)
            except Descartado as descarte:
                self.resumen.descartados[descarte.motivo] += 1
                self.resumen.nombres_descartados.append((descarte.motivo, evento.get("name", "")))
                continue
            except Exception as error:  # cualquier otro problema se reporta, no detiene la importación
                self.resumen.errores.append(f"{evento.get('id', '?')} ({evento.get('name', '')}): {error}")
                continue
            setattr(self.resumen, resultado, getattr(self.resumen, resultado) + 1)
        return self.resumen

    def _artista(self, datos):
        artista = Artista.objects.filter(id_ticketmaster=datos.id_ticketmaster).first()
        if artista is None:
            # Si ya se capturó a mano con el mismo nombre, se vincula en vez de duplicarlo.
            artista = Artista.objects.filter(id_ticketmaster__isnull=True, nombre__iexact=datos.nombre).first()
        artista = artista or Artista()
        artista.id_ticketmaster = datos.id_ticketmaster
        artista.nombre = datos.nombre
        if datos.genero:
            artista.genero = datos.genero
        if datos.imagen_url:
            artista.imagen_url = datos.imagen_url
        artista.save()
        return artista

    def _recinto(self, datos):
        recinto = Recinto.objects.filter(id_ticketmaster=datos.id_ticketmaster).first()
        if recinto is None:
            recinto = Recinto.objects.filter(
                id_ticketmaster__isnull=True, nombre__iexact=datos.nombre, ciudad=datos.ciudad
            ).first()
        recinto = recinto or Recinto()
        recinto.id_ticketmaster = datos.id_ticketmaster
        recinto.nombre = datos.nombre
        recinto.ciudad = datos.ciudad
        recinto.direccion = datos.direccion
        recinto.latitud = datos.latitud
        recinto.longitud = datos.longitud
        recinto.save()
        return recinto

    def _guardar_concierto(self, datos):
        """Devuelve el nombre del contador a sumar: creados, actualizados o sin_cambios."""
        artista = self._artista(datos.artista)
        invitados = [self._artista(a) for a in datos.invitados]
        valores = {
            "titulo": datos.titulo,
            "artista": artista,
            "recinto": self._recinto(datos.recinto),
            "fecha_hora": datos.fecha_hora,
            "hora_por_confirmar": datos.hora_por_confirmar,
            "estado": datos.estado,
            "url_boletos": datos.url_boletos,
            "imagen_url": datos.imagen_url,
            "genero": datos.genero,
        }
        if datos.precio_desde is not None:
            # Solo si Ticketmaster trae precio; si no, se respeta el capturado a mano.
            valores.update(precio_desde=datos.precio_desde, moneda=datos.moneda)

        concierto = Concierto.objects.filter(id_ticketmaster=datos.id_ticketmaster).first()
        if concierto is None:
            concierto = Concierto.objects.create(
                id_ticketmaster=datos.id_ticketmaster,
                origen=Concierto.Origen.TICKETMASTER,
                importado_en=self.ahora,
                **valores,
            )
            concierto.invitados.set(invitados)
            return "creados"

        cambios = [campo for campo, valor in valores.items() if getattr(concierto, campo) != valor]
        invitados_cambiaron = set(concierto.invitados.values_list("pk", flat=True)) != {a.pk for a in invitados}
        for campo in cambios:
            setattr(concierto, campo, valores[campo])
        concierto.importado_en = self.ahora  # se guarda siempre: "visto en la última importación"
        concierto.save()
        if invitados_cambiaron:
            concierto.invitados.set(invitados)
        return "actualizados" if cambios or invitados_cambiaron else "sin_cambios"
