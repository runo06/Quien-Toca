import analizar


def evento(nombre="Concierto", ciudad=None, latitud=None, longitud=None, **extra):
    """Arma un evento mínimo con la misma forma que los de la API."""
    recinto = {"id": "V1", "name": "Recinto"}
    if ciudad:
        recinto["city"] = {"name": ciudad}
    if latitud is not None:
        recinto["location"] = {"latitude": str(latitud), "longitude": str(longitud)}
    return {"id": nombre, "name": nombre, "_embedded": {"venues": [recinto]}, **extra}


def test_normalizar_quita_acentos_signos_y_mayusculas():
    assert analizar.normalizar("Ciudad de México") == "ciudad de mexico"
    assert analizar.normalizar("México, D.F.") == "mexico d f"
    assert analizar.normalizar(None) == ""


def test_obtener_recorre_diccionarios_y_listas():
    dato = {"priceRanges": [{"min": 0, "currency": "MXN"}]}
    assert analizar.obtener(dato, "priceRanges.0.currency") == "MXN"
    assert analizar.obtener(dato, "priceRanges.1.min") is None
    assert analizar.obtener(dato, "images.0.url") is None


def test_tiene_cuenta_el_cero_pero_no_lo_vacio():
    assert analizar.tiene({"min": 0}, "min")
    assert not analizar.tiene({"info": ""}, "info")
    assert not analizar.tiene({"images": []}, "images")


def test_ciudad_por_coordenadas_incluye_municipio_vecino():
    estadio_en_zapopan = evento(ciudad="Zapopan", latitud=20.6817, longitud=-103.4627)
    assert analizar.ciudad_de_evento(estadio_en_zapopan) == "Guadalajara"


def test_ciudad_por_coordenadas_elige_la_mas_cercana():
    assert analizar.ciudad_de_evento(evento(latitud=19.3139, longitud=-98.2404)) == "Tlaxcala"
    assert analizar.ciudad_de_evento(evento(latitud=19.0500, longitud=-98.2200)) == "Puebla"


def test_ciudad_fuera_de_las_cinco():
    merida = evento(ciudad="Mérida", latitud=20.97, longitud=-89.62)
    assert analizar.ciudad_de_evento(merida) is None


def test_sin_coordenadas_usa_el_nombre():
    assert analizar.ciudad_de_evento(evento(ciudad="San Pedro Garza García")) == "Monterrey"
    assert analizar.ciudad_de_evento(evento(ciudad="Mexico City")) == "Ciudad de México"
    assert analizar.ciudad_de_evento(evento(ciudad="Querétaro")) is None


def test_contar_por_ciudad_muestra_ceros():
    conteo = analizar.contar_por_ciudad([evento(ciudad="Puebla"), evento(ciudad="León")])
    assert conteo["Puebla"] == 1
    assert conteo["Tlaxcala"] == 0
    assert conteo[analizar.OTRAS] == 1


def test_cobertura_calcula_porcentajes():
    eventos = [evento("A", url="https://x"), evento("B")]
    resultado = analizar.cobertura(eventos, campos=[("url", "Enlace")])
    assert resultado == [("url", "Enlace", 1, 50.0)]


def test_cobertura_sin_eventos_no_divide_entre_cero():
    assert analizar.cobertura([], campos=[("url", "Enlace")]) == [("url", "Enlace", 0, 0.0)]


def test_detecta_complementos():
    eventos = [evento("Estacionamiento - Arena CDMX"), evento("Paquete VIP Banda X"), evento("Banda X")]
    assert [e["name"] for e in analizar.posibles_complementos(eventos)] == [
        "Estacionamiento - Arena CDMX",
        "Paquete VIP Banda X",
    ]


def test_posibles_duplicados_agrupa_por_artista_recinto_y_dia():
    artista = {"attractions": [{"id": "A1"}]}
    fecha = {"start": {"localDate": "2026-11-20"}}
    uno = evento("Uno", dates=fecha)
    dos = evento("Dos", dates=fecha)
    otro_dia = evento("Tres", dates={"start": {"localDate": "2026-11-21"}})
    for e in (uno, dos, otro_dia):
        e["_embedded"].update(artista)
    assert analizar.posibles_duplicados([uno, dos, otro_dia]) == [[uno, dos]]


def test_menciona_puertas_y_gira():
    assert analizar.menciona_puertas(evento(pleaseNote="Apertura de puertas 19:00"))
    assert not analizar.menciona_puertas(evento())
    assert analizar.menciona_gira(evento("Banda X World Tour 2026"))
    assert not analizar.menciona_gira(evento("Banda X en concierto"))


def test_resumen_imagenes():
    eventos = [evento(images=[{"ratio": "16_9", "width": 1024, "attribution": "Foto: X"}, {"ratio": "3_2", "width": 640}])]
    resumen = analizar.resumen_imagenes(eventos)
    assert resumen["proporciones"] == {"16_9": 1, "3_2": 1}
    assert resumen["con_atribucion"] == 1
    assert resumen["ancho_maximo"] == 1024


def test_elegir_ejemplo_toma_el_mas_completo():
    pobre = evento("Pobre")
    rico = evento("Rico", url="https://x", info="Algo", images=[{"url": "https://img"}])
    assert analizar.elegir_ejemplo([pobre, rico]) is rico
    assert analizar.elegir_ejemplo([]) is None
