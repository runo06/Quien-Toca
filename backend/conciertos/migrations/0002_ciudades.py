"""Migración de datos: crea las 5 ciudades del proyecto.

Al ser una migración, las ciudades existen en cualquier base nueva (local,
de pruebas o Neon) sin capturarlas a mano.
"""
from django.db import migrations

# (nombre, slug, latitud, longitud, radio_km, predeterminada)
CIUDADES = [
    ("Ciudad de México", "cdmx", 19.4326, -99.1332, 30, True),
    ("Guadalajara", "guadalajara", 20.6597, -103.3496, 25, False),
    ("Monterrey", "monterrey", 25.6866, -100.3161, 25, False),
    ("Puebla", "puebla", 19.0414, -98.2063, 20, False),
    ("Tlaxcala", "tlaxcala", 19.3139, -98.2404, 15, False),
]


def crear_ciudades(apps, schema_editor):
    # apps.get_model da el modelo tal como era en esta migración, no el actual.
    Ciudad = apps.get_model("conciertos", "Ciudad")
    for nombre, slug, latitud, longitud, radio_km, predeterminada in CIUDADES:
        Ciudad.objects.update_or_create(
            slug=slug,
            defaults={
                "nombre": nombre,
                "latitud": latitud,
                "longitud": longitud,
                "radio_km": radio_km,
                "es_predeterminada": predeterminada,
            },
        )


def borrar_ciudades(apps, schema_editor):
    Ciudad = apps.get_model("conciertos", "Ciudad")
    Ciudad.objects.filter(slug__in=[c[1] for c in CIUDADES]).delete()


class Migration(migrations.Migration):
    dependencies = [("conciertos", "0001_initial")]

    operations = [migrations.RunPython(crear_ciudades, borrar_ciudades)]
