"""Guarda en la base los eventos de Ticketmaster sin duplicar.

Regla de oro: el id de Ticketmaster identifica a cada concierto, recinto y
artista. Si ya existe se actualiza; si no, se crea. Nunca se borra nada.
"""
from collections import Counter
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from conciertos.models import Artista, Ciudad, Concierto, Recinto

from .traducir import Descartado, agrupar, fusionar, traducir_evento


@dataclass
class Resumen:
    creados: int = 0
    actualizados: int = 0
    sin_cambios: int = 0
    agrupados: int = 0  # eventos que se sumaron a otro (abonos, funciones repetidas)
    descartados: Counter = field(default_factory=Counter)
    nombres_descartados: list = field(default_factory=list)
    errores: list = field(default_factory=list)


class Importador:
    def __init__(self, ahora=None):
        self.ciudades = list(Ciudad.objects.all())
        self.ahora = ahora or timezone.now()
        self.resumen = Resumen()

    def importar(self, eventos):
        # 1. Traducir todos los eventos y apartar los descartados.
        traducidos = []
        for evento in eventos:
            try:
                traducidos.append(traducir_evento(evento, self.ciudades))
            except Descartado as descarte:
                self.resumen.descartados[descarte.motivo] += 1
                self.resumen.nombres_descartados.append((descarte.motivo, evento.get("name", "")))
            except Exception as error:  # un evento con datos raros no detiene la importación
                self.resumen.errores.append(f"{evento.get('id', '?')} ({evento.get('name', '')}): {error}")

        # 2. Juntar los que son el mismo concierto y guardar uno por grupo.
        for grupo in agrupar(traducidos):
            datos = fusionar(grupo)
            ids = [d.id_ticketmaster for d in grupo]
            try:
                # Cada concierto en su propia transacción: si falla, se deshace
                # solo ese y la importación sigue con los demás.
                with transaction.atomic():
                    resultado = self._guardar_concierto(datos, ids)
            except Exception as error:
                self.resumen.errores.append(f"{datos.id_ticketmaster} ({datos.titulo}): {error}")
                continue
            setattr(self.resumen, resultado, getattr(self.resumen, resultado) + 1)
            self.resumen.agrupados += len(grupo) - 1

        # 3. Los recintos que se habían guardado como artista, ya sin conciertos, sobran.
        ids_recinto = {i for datos in traducidos for i in datos.ids_recinto_como_artista}
        Artista.objects.filter(
            id_ticketmaster__in=ids_recinto, conciertos__isnull=True, participaciones__isnull=True
        ).delete()
        return self.resumen

    def _artista(self, datos):
        artista = None
        if datos.id_ticketmaster:
            artista = Artista.objects.filter(id_ticketmaster=datos.id_ticketmaster).first()
        if artista is None:
            # Nuevo, o sin id porque salió del título: si ya existe uno sin id con el
            # mismo nombre (capturado a mano o de otra noche), se reusa en vez de duplicarlo.
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

    def _guardar_concierto(self, datos, ids):
        """Devuelve el nombre del contador a sumar: creados, actualizados o sin_cambios.

        ids son todos los eventos del grupo: el concierto se busca por cualquiera
        de ellos, así no se duplica si otra noche manda un evento distinto del grupo.
        """
        # __overlap: "la lista guardada comparte al menos un id con esta lista".
        concierto = (
            Concierto.objects.filter(Q(id_ticketmaster__in=ids) | Q(ids_agrupados__overlap=ids)).order_by("pk").first()
        )
        if (
            concierto is not None
            and datos.artista.id_ticketmaster is None
            and concierto.artista.id_ticketmaster not in datos.ids_recinto_como_artista
        ):
            # El artista salió del título: se respeta el que ya tiene, por si lo corregiste
            # a mano ("Jeanette Gira 50 Aniversario" -> "Jeanette"). Salvo que sea el recinto.
            artista = concierto.artista
        else:
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

        if concierto is None:
            concierto = Concierto.objects.create(
                id_ticketmaster=datos.id_ticketmaster,
                ids_agrupados=sorted(ids),
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
        # Se acumulan los ids: un evento que llegó alguna vez sigue apuntando a este concierto.
        concierto.ids_agrupados = sorted(set(concierto.ids_agrupados) | set(ids) | {concierto.id_ticketmaster})
        concierto.importado_en = self.ahora  # se guarda siempre: "visto en la última importación"
        concierto.save()
        if invitados_cambiaron:
            concierto.invitados.set(invitados)
        return "actualizados" if cambios or invitados_cambiaron else "sin_cambios"
