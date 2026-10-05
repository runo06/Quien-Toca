"""Cliente mínimo de la API Discovery de Ticketmaster.

Hace solo dos cosas: pedir páginas de eventos y recorrer una búsqueda completa
respetando los límites de la API (5 llamadas por segundo, 5,000 al día y no
más allá del resultado 1,000 de una misma búsqueda).
"""
import time
from datetime import datetime, timedelta, timezone

import requests

URL_EVENTOS = "https://app.ticketmaster.com/discovery/v2/events.json"
TAMANO_PAGINA = 200          # el máximo que acepta la API por página
LIMITE_PROFUNDIDAD = 1000    # la API exige que tamaño × página sea menor a 1,000
PAUSA_ENTRE_LLAMADAS = 0.25  # 4 llamadas por segundo, debajo del límite de 5
DIAS_POR_VENTANA = 30


class ErrorTicketmaster(Exception):
    """Un problema que el usuario puede corregir (clave mala, límite agotado)."""


def formato_fecha(momento):
    """La API pide fechas UTC sin milisegundos: 2026-10-04T00:00:00Z."""
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ClienteTicketmaster:
    def __init__(self, clave, sesion=None, pausa=PAUSA_ENTRE_LLAMADAS):
        if not clave:
            raise ErrorTicketmaster(
                "Falta la clave. Copia .env.example como .env y escribe tu TICKETMASTER_API_KEY."
            )
        self.clave = clave
        # La sesión se puede reemplazar en las pruebas por una falsa que no usa la red.
        self.sesion = sesion or requests.Session()
        self.pausa = pausa
        self.llamadas = 0

    def _pedir(self, parametros, reintentos=3):
        parametros = {**parametros, "apikey": self.clave}
        for intento in range(reintentos):
            time.sleep(self.pausa)
            respuesta = self.sesion.get(URL_EVENTOS, params=parametros, timeout=30)
            self.llamadas += 1
            if respuesta.status_code == 429:
                # Demasiadas llamadas seguidas: esperamos cada vez más y reintentamos.
                time.sleep(2 ** intento)
                continue
            if respuesta.status_code == 401:
                raise ErrorTicketmaster("La API rechazó la clave (401). Revisa TICKETMASTER_API_KEY.")
            respuesta.raise_for_status()
            return respuesta.json()
        raise ErrorTicketmaster("La API siguió respondiendo 429 (límite de llamadas). Intenta más tarde.")

    def eventos_en_ventana(self, inicio, fin, **filtros):
        """Recorre todas las páginas de una búsqueda entre dos fechas.

        Devuelve (eventos, total_reportado). Si el total supera 1,000, la API
        no deja ver el resto: quien llama debe partir la ventana en otras más chicas.
        """
        eventos, pagina, total = [], 0, 0
        while True:
            datos = self._pedir({
                **filtros,
                "startDateTime": formato_fecha(inicio),
                "endDateTime": formato_fecha(fin),
                "size": TAMANO_PAGINA,
                "page": pagina,
                "sort": "date,asc",
            })
            eventos += datos.get("_embedded", {}).get("events", [])
            info_pagina = datos.get("page", {})
            total = info_pagina.get("totalElements", 0)
            pagina += 1
            if pagina >= info_pagina.get("totalPages", 0) or pagina * TAMANO_PAGINA >= LIMITE_PROFUNDIDAD:
                break
        return eventos, total

    def eventos_por_meses(self, meses, **filtros):
        """Consulta en ventanas de 30 días para no chocar con el límite de 1,000 por búsqueda.

        Devuelve (eventos_sin_repetir, ventanas_cortadas).
        """
        ahora = datetime.now(timezone.utc).replace(microsecond=0)
        vistos, cortadas = {}, []
        for i in range(meses):
            inicio = ahora + timedelta(days=DIAS_POR_VENTANA * i)
            fin = inicio + timedelta(days=DIAS_POR_VENTANA) - timedelta(seconds=1)
            eventos, total = self.eventos_en_ventana(inicio, fin, **filtros)
            if total > LIMITE_PROFUNDIDAD:
                cortadas.append(f"{inicio:%Y-%m-%d} a {fin:%Y-%m-%d} ({total} eventos)")
            for evento in eventos:
                vistos.setdefault(evento["id"], evento)
        return list(vistos.values()), cortadas
