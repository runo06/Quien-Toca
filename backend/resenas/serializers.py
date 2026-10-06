from django.utils import timezone
from rest_framework import serializers

from conciertos.models import Concierto

from .models import ASPECTOS, LARGO_MINIMO_TEXTO, Reporte, Resena


class ConciertoDeResenaSerializer(serializers.ModelSerializer):
    """Lo mínimo para decir "Daniela R., Ciudad de México, 20 nov 2026"."""

    artista = serializers.CharField(source="artista.nombre")
    recinto = serializers.CharField(source="recinto.nombre")
    ciudad = serializers.CharField(source="recinto.ciudad.nombre")

    class Meta:
        model = Concierto
        fields = ["slug", "titulo", "fecha_hora", "artista", "recinto", "ciudad"]


class ResenaSerializer(serializers.ModelSerializer):
    autor = serializers.CharField(source="usuario.first_name", read_only=True)
    # Al escribir se manda el slug del concierto; al leer llegan sus datos.
    concierto = serializers.SlugRelatedField(slug_field="slug", queryset=Concierto.objects.all())
    asistio = serializers.BooleanField(write_only=True, required=False)
    utiles = serializers.IntegerField(read_only=True, default=0)  # anotación de la vista
    me_sirvio = serializers.BooleanField(read_only=True, default=False)
    es_mia = serializers.SerializerMethodField()

    class Meta:
        model = Resena
        fields = [
            "id", "autor", "es_mia", "concierto", "general", *ASPECTOS, "texto", "asistio",
            "utiles", "me_sirvio", "creada", "editada",
        ]
        read_only_fields = ["creada", "editada"]
        # El largo mínimo lo revisa validate_texto (sin contar espacios y con un mensaje claro).
        extra_kwargs = {"texto": {"validators": []}}
        # La unicidad usuario+concierto se revisa a mano abajo, con un mensaje claro.
        validators = []

    def get_es_mia(self, resena):
        usuario = self.context["request"].user
        return usuario.is_authenticated and resena.usuario_id == usuario.pk

    def to_representation(self, resena):
        datos = super().to_representation(resena)
        datos["concierto"] = ConciertoDeResenaSerializer(resena.concierto).data
        return datos

    def validate_texto(self, texto):
        texto = texto.strip()
        if len(texto) < LARGO_MINIMO_TEXTO:
            raise serializers.ValidationError(
                f"Escribe al menos {LARGO_MINIMO_TEXTO} caracteres para que tu reseña le sirva a alguien."
            )
        return texto

    def validate_concierto(self, concierto):
        if self.instance is not None and concierto != self.instance.concierto:
            raise serializers.ValidationError("No se puede cambiar el concierto de una reseña.")
        if self.instance is None:
            if concierto.fecha_hora > timezone.now():
                raise serializers.ValidationError("Solo se pueden reseñar conciertos que ya pasaron.")
            if concierto.estado == Concierto.Estado.CANCELADO:
                raise serializers.ValidationError("Este concierto se canceló: no hay nada que reseñar.")
            usuario = self.context["request"].user
            if Resena.objects.filter(usuario=usuario, concierto=concierto).exists():
                raise serializers.ValidationError("Ya reseñaste este concierto. Puedes editar tu reseña.")
        return concierto

    def validate(self, datos):
        if self.instance is None and not datos.get("asistio"):
            raise serializers.ValidationError({"asistio": "Solo pueden reseñar quienes asistieron."})
        return datos

    def create(self, datos):
        return Resena.objects.create(usuario=self.context["request"].user, **datos)

    def update(self, resena, datos):
        datos.pop("asistio", None)
        datos.pop("concierto", None)
        for campo, valor in datos.items():
            setattr(resena, campo, valor)
        resena.editada = timezone.now()
        resena.save()
        return resena


class ReporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reporte
        fields = ["motivo", "comentario"]
