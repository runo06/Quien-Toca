from django.utils import timezone
from rest_framework import serializers

from conciertos.models import Ciudad

from .models import Sugerencia


class SugerenciaSerializer(serializers.ModelSerializer):
    ciudad = serializers.SlugRelatedField(slug_field="slug", queryset=Ciudad.objects.all())
    concierto = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Sugerencia
        fields = [
            "id", "artista", "ciudad", "recinto", "fecha", "hora", "url_boletos", "comentario",
            "estado", "motivo_rechazo", "concierto", "creada",
        ]
        read_only_fields = ["estado", "motivo_rechazo", "creada"]

    def validate_fecha(self, fecha):
        if fecha < timezone.localdate():
            raise serializers.ValidationError("Ese día ya pasó. Sugiere conciertos que aún no ocurren.")
        return fecha

    def validate_artista(self, texto):
        return texto.strip()

    def validate_recinto(self, texto):
        return texto.strip()
