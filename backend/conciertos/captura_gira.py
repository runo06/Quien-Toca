"""Pantalla del panel para capturar una gira: los datos comunes una vez y una fila por fecha."""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget, AdminTimeWidget, AutocompleteSelect
from django.db import transaction
from django.forms import formset_factory
from django.urls import reverse
from django.utils.html import format_html

from .models import Artista, Concierto, Recinto


class GiraForm(forms.Form):
    """Lo que comparten todas las fechas."""

    artista = forms.ModelChoiceField(
        Artista.objects.all(), widget=AutocompleteSelect(Concierto._meta.get_field("artista"), admin.site)
    )
    gira = forms.CharField(label="nombre de la gira", max_length=150, required=False)
    url_boletos = forms.URLField(
        label="URL de la boletera", max_length=500, help_text="La misma para todas, salvo que una fecha diga otra."
    )
    imagen_url = forms.URLField(label="imagen (URL)", max_length=500, required=False)
    genero = forms.CharField(label="género", max_length=60, required=False)


class FechaForm(forms.Form):
    """Una fecha de la gira. Las filas vacías se ignoran."""

    recinto = forms.ModelChoiceField(
        Recinto.objects.select_related("ciudad"),
        widget=AutocompleteSelect(Concierto._meta.get_field("recinto"), admin.site),
    )
    fecha = forms.DateField(widget=AdminDateWidget)
    hora = forms.TimeField(required=False, widget=AdminTimeWidget, help_text="Vacía = por confirmar.")
    url_boletos = forms.URLField(label="otra URL", max_length=500, required=False)
    precio_desde = forms.DecimalField(label="precio desde", max_digits=10, decimal_places=2, required=False, min_value=0)


class FechasBase(forms.BaseFormSet):
    default_error_messages = {"too_few_forms": "Llena al menos una fecha."}

    def clean(self):
        if any(self.errors):
            return
        vistas = set()
        for formulario in self.forms:
            datos = formulario.cleaned_data
            if not datos or datos.get("DELETE"):
                continue
            clave = (datos["recinto"].ciudad_id, datos["fecha"])
            if clave in vistas:
                formulario.add_error("fecha", "Esta ciudad y día ya están en otra fila.")
            vistas.add(clave)


FechasFormSet = formset_factory(FechaForm, formset=FechasBase, extra=6, min_num=1, validate_min=True)


def momento(fecha, hora):
    """El día y la hora en la zona de México (sin hora: medianoche, marcada por confirmar)."""
    return datetime.combine(fecha, hora or time(0), tzinfo=ZoneInfo(settings.TIME_ZONE))


def concierto_existente(artista, recinto, fecha):
    """El concierto del mismo artista, ciudad y día, si ya está (para no duplicarlo)."""
    return Concierto.objects.filter(artista=artista, recinto__ciudad=recinto.ciudad, fecha_hora__date=fecha).first()


@transaction.atomic
def crear_gira(comunes, filas):
    """Crea un concierto por fila, todos o ninguno.

    comunes: artista, gira, url_boletos, imagen_url, genero.
    filas: recinto, fecha, hora (o None), url_boletos (o vacío) y precio_desde (o None).
    """
    artista = comunes["artista"]
    return [
        Concierto.objects.create(
            titulo=artista.nombre,
            artista=artista,
            gira=comunes.get("gira", ""),
            genero=comunes.get("genero") or artista.genero,
            imagen_url=comunes.get("imagen_url", ""),
            recinto=fila["recinto"],
            fecha_hora=momento(fila["fecha"], fila.get("hora")),
            hora_por_confirmar=fila.get("hora") is None,
            url_boletos=fila.get("url_boletos") or comunes["url_boletos"],
            precio_desde=fila.get("precio_desde"),
            origen=Concierto.Origen.MANUAL,
        )
        for fila in filas
    ]


# --- Para la pantalla del panel (formularios de Django) ---

def revisar_duplicados(artista, formset):
    """Marca las filas que ya existen. Devuelve True si no hay ninguna."""
    sin_duplicados = True
    for formulario in formset.forms:
        datos = formulario.cleaned_data
        if not datos:
            continue
        if existente := concierto_existente(artista, datos["recinto"], datos["fecha"]):
            url = reverse("admin:conciertos_concierto_change", args=[existente.pk])
            formulario.add_error("fecha", format_html('Ya existe: <a href="{}">{}</a>', url, existente))
            sin_duplicados = False
    return sin_duplicados


def crear_conciertos(gira, formset):
    return crear_gira(gira.cleaned_data, [f.cleaned_data for f in formset.forms if f.cleaned_data])
