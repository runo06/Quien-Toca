from django.core.management.base import BaseCommand

from conciertos.importacion.descripciones import actualizar_pendientes


class Command(BaseCommand):
    help = "Busca en Wikipedia la descripción de los artistas nuevos (y la renueva cada 30 días)."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=150, help="artistas por corrida (150 por defecto)")

    def handle(self, *args, limite, **opciones):
        encontradas, sin_descripcion, errores = actualizar_pendientes(limite)
        self.stdout.write(self.style.SUCCESS(f"Con descripción: {encontradas}"))
        self.stdout.write(f"Sin artículo confiable: {sin_descripcion}")
        for error in errores:
            self.stderr.write(self.style.WARNING(error))
        if errores:
            self.stdout.write(f"Con error de conexión (se reintentan otra noche): {len(errores)}")
