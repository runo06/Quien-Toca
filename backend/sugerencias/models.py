from django.conf import settings
from django.db import models

from conciertos.models import Ciudad, Concierto


class Sugerencia(models.Model):
    """Un concierto que alguien echa de menos. Queda pendiente hasta que lo revises en el panel."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sugerencias")
    artista = models.CharField(max_length=200)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, related_name="sugerencias")
    recinto = models.CharField(max_length=200)
    fecha = models.DateField()
    hora = models.TimeField(null=True, blank=True, help_text="Vacía si aún no se anuncia.")
    url_boletos = models.URLField("dónde venden los boletos", max_length=500)
    comentario = models.CharField(max_length=500, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    motivo_rechazo = models.CharField(
        "motivo del rechazo", max_length=300, blank=True, help_text="Lo verá quien lo sugirió."
    )
    concierto = models.ForeignKey(
        Concierto, on_delete=models.SET_NULL, null=True, blank=True, related_name="sugerencias",
        verbose_name="concierto creado",
    )
    creada = models.DateTimeField(auto_now_add=True)
    revisada = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.artista} · {self.recinto}, {self.ciudad} · {self.fecha:%d/%m/%Y}"
