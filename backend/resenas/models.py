from django.conf import settings
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from conciertos.models import Concierto

LARGO_MINIMO_TEXTO = 20
DE_1_A_5 = [MinValueValidator(1), MaxValueValidator(5)]
ASPECTOS = ("show", "sonido", "puntualidad", "recinto")  # calificaciones opcionales


def entre_1_y_5(campo, opcional=False):
    """Restricción en la base: aunque alguien salte la API, no se guarda un 7 de 5."""
    rango = Q(**{f"{campo}__gte": 1, f"{campo}__lte": 5})
    if opcional:
        rango |= Q(**{f"{campo}__isnull": True})
    return models.CheckConstraint(condition=rango, name=f"resena_{campo}_de_1_a_5")


class ResenaQuerySet(models.QuerySet):
    def visibles(self):
        """Las que se muestran al público: las ocultas por un reporte no cuentan ni en promedios."""
        return self.filter(oculta=False)


class Resena(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resenas")
    # PROTECT: los conciertos nunca se borran, y si alguien lo intenta, sus reseñas lo impiden.
    concierto = models.ForeignKey(Concierto, on_delete=models.PROTECT, related_name="resenas")
    general = models.PositiveSmallIntegerField("calificación general", validators=DE_1_A_5)
    show = models.PositiveSmallIntegerField("show en vivo", null=True, blank=True, validators=DE_1_A_5)
    sonido = models.PositiveSmallIntegerField(null=True, blank=True, validators=DE_1_A_5)
    puntualidad = models.PositiveSmallIntegerField(null=True, blank=True, validators=DE_1_A_5)
    recinto = models.PositiveSmallIntegerField(null=True, blank=True, validators=DE_1_A_5)
    texto = models.TextField(validators=[MinLengthValidator(LARGO_MINIMO_TEXTO)], max_length=2000)
    asistio = models.BooleanField("confirmó que asistió", default=False)
    oculta = models.BooleanField(default=False, help_text="Oculta por moderación: no se muestra ni cuenta en los promedios.")
    creada = models.DateTimeField(auto_now_add=True)
    editada = models.DateTimeField(null=True, blank=True)

    objects = ResenaQuerySet.as_manager()

    class Meta:
        ordering = ["-creada"]
        verbose_name = "reseña"
        verbose_name_plural = "reseñas"
        constraints = [
            # Una sola reseña por persona y concierto, también a nivel de base.
            models.UniqueConstraint(fields=["usuario", "concierto"], name="una_resena_por_concierto"),
            models.CheckConstraint(condition=Q(asistio=True), name="resena_solo_si_asistio"),
            entre_1_y_5("general"),
            *[entre_1_y_5(campo, opcional=True) for campo in ASPECTOS],
        ]

    def __str__(self):
        return f"{self.usuario.first_name} sobre {self.concierto}"


class VotoUtil(models.Model):
    """Un "Me sirvió" de una persona a la reseña de otra."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votos_utiles")
    resena = models.ForeignKey(Resena, on_delete=models.CASCADE, related_name="votos")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "voto «Me sirvió»"
        verbose_name_plural = "votos «Me sirvió»"
        constraints = [models.UniqueConstraint(fields=["usuario", "resena"], name="un_voto_por_resena")]


class Reporte(models.Model):
    class Motivo(models.TextChoices):
        OFENSIVA = "ofensiva", "Ofensiva o con odio"
        SPAM = "spam", "Publicidad o spam"
        FALSA = "falsa", "No parece de alguien que asistió"
        OTRO = "otro", "Otro motivo"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADO = "aceptado", "Aceptado: reseña oculta"
        DESCARTADO = "descartado", "Descartado"

    resena = models.ForeignKey(Resena, on_delete=models.CASCADE, related_name="reportes", verbose_name="reseña")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reportes")
    motivo = models.CharField(max_length=20, choices=Motivo.choices)
    comentario = models.CharField(max_length=500, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    creado = models.DateTimeField(auto_now_add=True)
    revisado = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado"]
        constraints = [models.UniqueConstraint(fields=["usuario", "resena"], name="un_reporte_por_resena")]

    def __str__(self):
        return f"{self.get_motivo_display()} · reseña {self.resena_id}"
