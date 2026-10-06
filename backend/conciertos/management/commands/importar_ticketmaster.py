from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from conciertos.importacion.cliente import ClienteTicketmaster, ErrorTicketmaster
from conciertos.importacion.importador import Importador
from conciertos.models import Ciudad

MOTIVOS = {
    "complemento": "Complementos (VIP, estacionamiento, meet & greet)",
    "prueba": "Eventos de prueba de Ticketmaster",
    "fuera_de_ciudades": "Fuera de nuestras ciudades",
    "sin_artista": "Sin artista",
    "sin_recinto": "Sin recinto",
    "sin_coordenadas": "Recinto sin coordenadas",
    "sin_fecha": "Sin fecha",
    "sin_enlace": "Sin enlace a la boletera",
}


class Command(BaseCommand):
    help = "Importa los conciertos de música de Ticketmaster en las ciudades registradas."

    def add_arguments(self, parser):
        parser.add_argument("--meses", type=int, default=12, help="meses hacia adelante (12 por defecto)")

    def handle(self, *args, meses, verbosity, **opciones):
        if not Ciudad.objects.exists():
            raise CommandError("No hay ciudades registradas. Corre primero: python manage.py migrate")

        try:
            cliente = ClienteTicketmaster(settings.TICKETMASTER_API_KEY)
            eventos, cortadas = cliente.eventos_por_meses(meses, countryCode="MX", classificationName="music")
        except ErrorTicketmaster as error:
            raise CommandError(str(error))
        for ventana in cortadas:
            self.stderr.write(self.style.WARNING(f"La ventana {ventana} pasó de 1,000 resultados; faltan eventos."))

        resumen = Importador().importar(eventos)

        self.stdout.write(f"Eventos recibidos: {len(eventos)} ({cliente.llamadas} llamadas a la API)")
        self.stdout.write(self.style.SUCCESS(f"Creados: {resumen.creados}"))
        self.stdout.write(f"Actualizados: {resumen.actualizados}")
        self.stdout.write(f"Sin cambios: {resumen.sin_cambios}")
        self.stdout.write(f"Agrupados con otro evento (abonos, repetidos): {resumen.agrupados}")
        self.stdout.write(f"Descartados: {sum(resumen.descartados.values())}")
        for motivo, cantidad in resumen.descartados.most_common():
            self.stdout.write(f"  {MOTIVOS.get(motivo, motivo)}: {cantidad}")
        if verbosity >= 2:
            # Con -v 2 se listan los descartados (menos los de otras ciudades, que son muchos).
            for motivo, nombre in resumen.nombres_descartados:
                if motivo != "fuera_de_ciudades":
                    self.stdout.write(f"    [{motivo}] {nombre}")

        if resumen.errores:
            for error in resumen.errores:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError(f"{len(resumen.errores)} eventos no se pudieron guardar.")
