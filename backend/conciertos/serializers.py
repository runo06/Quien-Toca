"""Serializadores: convierten los modelos en el JSON que recibe React.

Hay versiones "breves" para listas (solo lo que dibuja el boleto) y una de
detalle para la página del concierto.
"""
from rest_framework import serializers

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

    class Meta:
        model = Concierto
        fields = [
            "slug", "titulo", "gira", "fecha_hora", "hora_por_confirmar", "estado",
            "artista", "recinto", "precio_desde", "moneda", "imagen_url", "genero",
        ]


class OtraFechaSerializer(serializers.ModelSerializer):
    recinto = RecintoBreveSerializer()
    ya_paso = serializers.SerializerMethodField()

    class Meta:
        model = Concierto
        fields = ["slug", "fecha_hora", "hora_por_confirmar", "estado", "precio_desde", "moneda", "recinto", "ya_paso"]

    def get_ya_paso(self, concierto):
        return concierto.fecha_hora < inicio_de_hoy()


class ConciertoDetalleSerializer(ConciertoListaSerializer):
    invitados = ArtistaBreveSerializer(many=True)
    recinto = RecintoSerializer()
    precios = PrecioZonaSerializer(many=True)
    ya_paso = serializers.SerializerMethodField()
    otras_fechas = serializers.SerializerMethodField()

    class Meta(ConciertoListaSerializer.Meta):
        fields = ConciertoListaSerializer.Meta.fields + [
            "invitados", "apertura_puertas", "url_boletos", "precios", "ya_paso", "otras_fechas",
        ]

    def get_ya_paso(self, concierto):
        return concierto.fecha_hora < inicio_de_hoy()

    def get_otras_fechas(self, concierto):
        """Las fechas próximas del mismo artista y las 5 pasadas más recientes, en orden cronológico."""
        hoy = inicio_de_hoy()
        otras = (
            Concierto.objects.filter(artista=concierto.artista)
            .exclude(pk=concierto.pk)
            .exclude(estado=Concierto.Estado.CANCELADO)
            .select_related("recinto__ciudad")
        )
        futuras = list(otras.filter(fecha_hora__gte=hoy).order_by("fecha_hora"))
        pasadas = list(otras.filter(fecha_hora__lt=hoy).order_by("-fecha_hora")[:5])
        return OtraFechaSerializer(pasadas[::-1] + futuras, many=True).data
