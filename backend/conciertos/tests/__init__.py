import copy
import json
from pathlib import Path

_RUTA_EVENTOS = Path(__file__).parent / "datos" / "eventos_ticketmaster.json"
_EVENTOS = json.loads(_RUTA_EVENTOS.read_text(encoding="utf-8"))


def cargar_eventos():
    """Una copia nueva de los eventos de ejemplo: cada prueba puede modificarla sin afectar a otras.

    Orden: 0 CDMX completo, 1 Zapopan sin hora, 2 Monterrey cancelado con precio,
    3 complemento VIP, 4 Mérida (fuera), 5 sin atracciones (el artista sale del título).
    """
    return copy.deepcopy(_EVENTOS)
