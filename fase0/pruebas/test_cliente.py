from datetime import datetime, timezone

import pytest
import requests

from cliente_ticketmaster import ClienteTicketmaster, ErrorTicketmaster, formato_fecha


class RespuestaFalsa:
    def __init__(self, datos=None, estado=200):
        self._datos = datos or {}
        self.status_code = estado

    def json(self):
        return self._datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class SesionFalsa:
    """Imita requests.Session: devuelve respuestas preparadas y anota lo que se pidió."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.pedidos = []

    def get(self, url, params, timeout):
        self.pedidos.append(params)
        return self.respuestas.pop(0)


def pagina(ids, total_paginas, total):
    return RespuestaFalsa({
        "_embedded": {"events": [{"id": i} for i in ids]},
        "page": {"totalPages": total_paginas, "totalElements": total},
    })


def cliente(respuestas):
    return ClienteTicketmaster("clave-de-prueba", sesion=SesionFalsa(respuestas), pausa=0)


INICIO = datetime(2026, 11, 1, tzinfo=timezone.utc)
FIN = datetime(2026, 11, 30, tzinfo=timezone.utc)


def test_formato_fecha_sin_milisegundos_y_en_utc():
    assert formato_fecha(datetime(2026, 11, 1, 8, 30, 15, 999, tzinfo=timezone.utc)) == "2026-11-01T08:30:15Z"


def test_sin_clave_avisa():
    with pytest.raises(ErrorTicketmaster):
        ClienteTicketmaster("")


def test_recorre_todas_las_paginas():
    c = cliente([pagina(["a", "b"], 2, 3), pagina(["c"], 2, 3)])
    eventos, total = c.eventos_en_ventana(INICIO, FIN, countryCode="MX")
    assert [e["id"] for e in eventos] == ["a", "b", "c"]
    assert total == 3
    assert [p["page"] for p in c.sesion.pedidos] == [0, 1]
    assert c.sesion.pedidos[0]["apikey"] == "clave-de-prueba"
    assert c.sesion.pedidos[0]["countryCode"] == "MX"
    assert c.llamadas == 2


def test_ventana_vacia_hace_una_sola_llamada():
    c = cliente([RespuestaFalsa({"page": {"totalPages": 0, "totalElements": 0}})])
    assert c.eventos_en_ventana(INICIO, FIN) == ([], 0)
    assert c.llamadas == 1


def test_respeta_el_limite_de_1000_resultados():
    # 200 por página: solo se pueden pedir las páginas 0 a 4.
    c = cliente([pagina([f"e{i}"], 10, 2000) for i in range(10)])
    c.eventos_en_ventana(INICIO, FIN)
    assert [p["page"] for p in c.sesion.pedidos] == [0, 1, 2, 3, 4]


def test_clave_rechazada():
    c = cliente([RespuestaFalsa(estado=401)])
    with pytest.raises(ErrorTicketmaster):
        c.eventos_en_ventana(INICIO, FIN)


def test_por_meses_quita_repetidos_y_avisa_ventanas_cortadas():
    c = cliente([pagina(["a", "b"], 1, 2), pagina(["b", "c"], 1, 1500)])
    eventos, cortadas = c.eventos_por_meses(2)
    assert [e["id"] for e in eventos] == ["a", "b", "c"]
    assert len(cortadas) == 1
