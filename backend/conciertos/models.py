from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify


def inicio_de_hoy():
    """Medianoche de hoy en la hora de México. Un concierto de hoy sigue en cartelera todo el día."""
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def slug_unico(instancia, texto, largo_maximo=100):
    """Convierte el texto en slug y le agrega -2, -3... si ya lo usa otro registro."""
    base = slugify(texto)[:largo_maximo].strip("-") or "sin-nombre"
    modelo = type(instancia)
    candidato, numero = base, 2
    while modelo.objects.filter(slug=candidato).exclude(pk=instancia.pk).exists():
        candidato = f"{base}-{numero}"
        numero += 1
    return candidato


class Ciudad(models.Model):
    """Una zona metropolitana: el centro y un radio en km."""

    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    latitud = models.FloatField()
    longitud = models.FloatField()
    radio_km = models.PositiveSmallIntegerField(
        "radio (km)", help_text="Los recintos a esta distancia del centro pertenecen a la ciudad."
    )
    es_predeterminada = models.BooleanField("predeterminada", default=False)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "ciudades"
        constraints = [
            models.UniqueConstraint(
                fields=["es_predeterminada"], condition=Q(es_predeterminada=True), name="una_ciudad_predeterminada"
            ),
        ]

    def __str__(self):
        return self.nombre


class Recinto(models.Model):
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="Se genera solo si lo dejas vacío.")
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, related_name="recintos")
    direccion = models.CharField("dirección", max_length=255, blank=True)
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)
    id_ticketmaster = models.CharField("id de Ticketmaster", max_length=64, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.ciudad})"

    def save(self, *args, **kwargs):
        # Un id vacío se guarda como NULL: así varios recintos manuales no chocan con unique.
        self.id_ticketmaster = self.id_ticketmaster or None
        if not self.slug:
            self.slug = slug_unico(self, f"{self.nombre} {self.ciudad.slug}")
        super().save(*args, **kwargs)


class Artista(models.Model):
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="Se genera solo si lo dejas vacío.")
    genero = models.CharField("género", max_length=60, blank=True)
    imagen_url = models.URLField("imagen (URL)", max_length=500, blank=True)
    id_ticketmaster = models.CharField("id de Ticketmaster", max_length=64, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.id_ticketmaster = self.id_ticketmaster or None
        if not self.slug:
            self.slug = slug_unico(self, self.nombre)
        super().save(*args, **kwargs)


class ConciertoQuerySet(models.QuerySet):
    def proximos(self):
        """Los que se muestran en la cartelera: de hoy en adelante y no cancelados."""
        return self.filter(fecha_hora__gte=inicio_de_hoy()).exclude(estado=Concierto.Estado.CANCELADO)


class Concierto(models.Model):
    class Origen(models.TextChoices):
        TICKETMASTER = "ticketmaster", "Ticketmaster"
        MANUAL = "manual", "Captura manual"

    class Estado(models.TextChoices):
        EN_VENTA = "en_venta", "En venta"
        SIN_VENTA = "sin_venta", "Sin venta"
        CANCELADO = "cancelado", "Cancelado"
        POSPUESTO = "pospuesto", "Pospuesto"
        REPROGRAMADO = "reprogramado", "Reprogramado"

    # Campos que la importación sobrescribe en los conciertos de Ticketmaster.
    # Los demás (gira, apertura de puertas, precios por zona) solo se capturan a mano.
    CAMPOS_TICKETMASTER = (
        "titulo", "artista", "invitados", "recinto", "fecha_hora", "hora_por_confirmar",
        "estado", "url_boletos", "imagen_url", "genero",
    )

    titulo = models.CharField("título", max_length=255)
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="Se genera solo si lo dejas vacío.")
    artista = models.ForeignKey(
        Artista, on_delete=models.PROTECT, related_name="conciertos", verbose_name="artista principal"
    )
    invitados = models.ManyToManyField(
        Artista, blank=True, related_name="participaciones", verbose_name="artistas invitados"
    )
    recinto = models.ForeignKey(Recinto, on_delete=models.PROTECT, related_name="conciertos")
    fecha_hora = models.DateTimeField("fecha y hora", db_index=True)
    hora_por_confirmar = models.BooleanField("hora por confirmar", default=False)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.EN_VENTA)
    url_boletos = models.URLField("URL de la boletera", max_length=500)
    imagen_url = models.URLField("imagen (URL)", max_length=500, blank=True)
    genero = models.CharField("género", max_length=60, blank=True)
    gira = models.CharField(max_length=150, blank=True)
    apertura_puertas = models.TimeField("apertura de puertas", null=True, blank=True)
    precio_desde = models.DecimalField(
        "precio desde", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Si lo dejas vacío y capturas precios por zona, se usa el más bajo.",
    )
    moneda = models.CharField(max_length=3, default="MXN")
    origen = models.CharField(max_length=20, choices=Origen.choices, default=Origen.MANUAL)
    id_ticketmaster = models.CharField("id de Ticketmaster", max_length=64, unique=True, null=True, blank=True)
    ids_agrupados = ArrayField(
        models.CharField(max_length=64), default=list, blank=True, verbose_name="ids agrupados",
        help_text="Todos los eventos de Ticketmaster que forman este concierto (abonos, repetidos).",
    )
    importado_en = models.DateTimeField("última importación", null=True, blank=True)
    creado_en = models.DateTimeField("creado", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado", auto_now=True)

    # Concierto.objects.proximos() además de los métodos normales (filter, get...).
    objects = ConciertoQuerySet.as_manager()

    class Meta:
        ordering = ["fecha_hora"]

    def __str__(self):
        return f"{self.titulo} · {timezone.localtime(self.fecha_hora):%d/%m/%Y}"

    @property
    def ciudad(self):
        return self.recinto.ciudad

    @property
    def ya_paso(self):
        return self.fecha_hora < timezone.now()

    def save(self, *args, **kwargs):
        self.id_ticketmaster = self.id_ticketmaster or None
        if not self.slug:
            # Ej. "los-cometas-del-sur-cdmx-2026-11-20". La fecha es la local, no la UTC.
            fecha_local = timezone.localtime(self.fecha_hora)
            self.slug = slug_unico(self, f"{self.artista.nombre} {self.recinto.ciudad.slug} {fecha_local:%Y-%m-%d}")
        super().save(*args, **kwargs)


class PrecioZona(models.Model):
    concierto = models.ForeignKey(Concierto, on_delete=models.CASCADE, related_name="precios")
    zona = models.CharField(max_length=80)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-precio"]
        verbose_name = "precio por zona"
        verbose_name_plural = "precios por zona"
        constraints = [models.UniqueConstraint(fields=["concierto", "zona"], name="zona_unica_por_concierto")]

    def __str__(self):
        return f"{self.zona}: ${self.precio}"
