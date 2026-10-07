from django.conf import settings
from django.db import models

from conciertos.models import Artista, Concierto


class ArtistaSeguido(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artistas_seguidos")
    artista = models.ForeignKey(Artista, on_delete=models.CASCADE, related_name="seguidores")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "artista seguido"
        verbose_name_plural = "artistas seguidos"
        constraints = [models.UniqueConstraint(fields=["usuario", "artista"], name="seguir_una_vez")]

    def __str__(self):
        return f"{self.usuario.first_name} sigue a {self.artista}"


class ConciertoGuardado(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conciertos_guardados")
    concierto = models.ForeignKey(Concierto, on_delete=models.CASCADE, related_name="guardados")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "concierto guardado"
        verbose_name_plural = "conciertos guardados"
        constraints = [models.UniqueConstraint(fields=["usuario", "concierto"], name="guardar_una_vez")]

    def __str__(self):
        return f"{self.usuario.first_name} guardó {self.concierto}"
