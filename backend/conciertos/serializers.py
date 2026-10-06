"""Serializadores: convierten los modelos en el JSON que recibe React.

Hay versiones "breves" para listas (solo lo que dibuja el boleto) y una de
detalle para la página del concierto.
"""
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers

from resenas.calificaciones import calificacion_artista, calificacion_recinto

from .models import Artista, Ciudad, Concierto, PrecioZona, Recinto, inicio_de_hoy


class CiudadSerializer(serializers.ModelSerializer):
    conciertos_proximos = serializers.IntegerField(read_only=True)  # viene de una anotación en la vista

    class Meta:
        model = Ciudad
        fields = ["nombre", "slug", "es_predeterminada", "conciertos_proximos"]


class CiudadBreveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ciudad
        fields = ["nombre", "slug"]


class ArtistaBreveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artista
        fields = ["nombre", "slug", "genero", "imagen_url"]


class RecintoBreveSerializer(serializers.ModelSerializer):
    ciudad = CiudadBreveSerializer()

    class Meta:
        model = Recinto
        fields = ["nombre", "slug", "ciudad"]


class RecintoSerializer(serializers.ModelSerializer):
    ciudad = CiudadBreveSerializer()

    class Meta:
        model = Recinto
        fields = ["nombre", "slug", "direccion", "latitud", "longitud", "ciudad"]


class PrecioZonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrecioZona
        fields = ["zona", "precio"]


class ConciertoListaSerializer(serializers.ModelSerializer):
    artista = ArtistaBreveSerializer()
    recinto = RecintoBreveSerializer()
    # Nota de las reseñas del artista (anotación de la vista; en el detalle no se usa).
    promedio_artista = serializers.SerializerMethodField()
    resenas_artista = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Concierto
        fields = [
            "slug", "titulo", "gira", "fecha_hora", "hora_por_confirmar", "estado",
            "artista", "recinto", "precio_desde", "moneda", "imagen_url", "genero",
            "promedio_artista", "resenas_artista",
        ]

    def get_promedio_artista(self, concierto):
        promedio = getattr(concierto, "promedio_artista", None)
        return round(float(promedio), 1) if promedio is not None else None


def se_puede_resenar(concierto):
    """Ya empezó y no se canceló. (ya_paso, en cambio, cuenta desde el día siguiente.)"""
    return concierto.fecha_hora <= timezone.now() and concierto.estado != Concierto.Estado.CANCELADO


class OtraFechaSerializer(serializers.ModelSerializer):
    recinto = RecintoBreveSerializer()
    ya_paso = serializers.SerializerMethodField()
    se_puede_resenar = serializers.SerializerMethodField()
    resenas = serializers.IntegerField(source="n_resenas", read_only=True, default=0)

    class Meta:
        model = Concierto
        fields = [
            "slug", "fecha_hora", "hora_por_confirmar", "estado", "precio_desde", "moneda", "recinto",
            "ya_paso", "se_puede_resenar", "resenas",
        ]

    def get_ya_paso(self, concierto):
        return concierto.fecha_hora < inicio_de_hoy()

    def get_se_puede_resenar(self, concierto):
        return se_puede_resenar(concierto)


class ConciertoDetalleSerializer(ConciertoListaSerializer):
    invitados = ArtistaBreveSerializer(many=True)
    recinto = RecintoSerializer()
    precios = PrecioZonaSerializer(many=True)
    ya_paso = serializers.SerializerMethodField()
    se_puede_resenar = serializers.SerializerMethodField()
    otras_fechas = serializers.SerializerMethodField()
    calificacion_artista = serializers.SerializerMethodField()
    calificacion_recinto = serializers.SerializerMethodField()
    # El detalle trae la calificación completa: se quitan los campos breves de la lista.
    promedio_artista = None
    resenas_artista = None

    class Meta(ConciertoListaSerializer.Meta):
        fields = [
            campo for campo in ConciertoListaSerializer.Meta.fields if campo not in ("promedio_artista", "resenas_artista")
        ] + [
            "invitados", "apertura_puertas", "url_boletos", "precios", "ya_paso", "se_puede_resenar",
            "otras_fechas", "calificacion_artista", "calificacion_recinto",
        ]

    def get_ya_paso(self, concierto):
        return concierto.fecha_hora < inicio_de_hoy()

    def get_se_puede_resenar(self, concierto):
        return se_puede_resenar(concierto)

    def get_calificacion_artista(self, concierto):
        return calificacion_artista(concierto.artista)

    def get_calificacion_recinto(self, concierto):
        return calificacion_recinto(concierto.recinto)

    def get_otras_fechas(self, concierto):
        """Las fechas próximas del mismo artista y las 5 pasadas más recientes, en orden cronológico."""
        hoy = inicio_de_hoy()
        otras = (
            Concierto.objects.filter(artista=concierto.artista)
            .exclude(pk=concierto.pk)
            .exclude(estado=Concierto.Estado.CANCELADO)
            .select_related("recinto__ciudad")
            .annotate(n_resenas=Count("resenas", filter=Q(resenas__oculta=False)))
        )
        futuras = list(otras.filter(fecha_hora__gte=hoy).order_by("fecha_hora"))
        pasadas = list(otras.filter(fecha_hora__lt=hoy).order_by("-fecha_hora")[:5])
        return OtraFechaSerializer(pasadas[::-1] + futuras, many=True).data
