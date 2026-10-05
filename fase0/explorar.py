"""Fase 0: ¿alcanzan los datos de Ticketmaster para ¿Quién toca?

Descarga los conciertos de música de todo México de los próximos meses, los
reparte entre las cinco ciudades del proyecto y mide qué campos vienen llenos.

Uso dentro del contenedor:
    python explorar.py               # próximos 12 meses
    python explorar.py --meses 6
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import analizar
from cliente_ticketmaster import ClienteTicketmaster, ErrorTicketmaster

LIMITE_DIARIO = 5000


def titulo(texto):
    print(f"\n{'=' * 72}\n{texto}\n{'=' * 72}")


def guardar(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def porcentaje(parte, total):
    return f"{100 * parte / total:.0f}%" if total else "0%"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--meses", type=int, default=12, help="meses hacia adelante (12 por defecto)")
    parser.add_argument("--muestras", type=Path, default=Path("muestras"), help="carpeta para el JSON crudo")
    args = parser.parse_args()

    try:
        cliente = ClienteTicketmaster(os.environ.get("TICKETMASTER_API_KEY"))
        # Pedimos todo México y repartimos nosotros por ciudad: así vemos cómo
        # escribe Ticketmaster cada ciudad (Zapopan, CDMX, etc.) en vez de adivinarlo.
        todos, cortadas = cliente.eventos_por_meses(
            args.meses, countryCode="MX", classificationName="music", locale="*"
        )
    except ErrorTicketmaster as error:
        sys.exit(f"Error: {error}")

    guardar(args.muestras / "eventos_mx.json", todos)
    nuestros = [e for e in todos if analizar.ciudad_de_evento(e)]

    titulo("1. Consulta")
    print(f"Conciertos de música en México, próximos {args.meses} meses: {len(todos)}")
    print(f"Llamadas usadas: {cliente.llamadas} de {LIMITE_DIARIO} diarias")
    for ventana in cortadas:
        print(f"AVISO: la ventana {ventana} pasó de 1,000 resultados; faltan eventos.")

    titulo("2. Conciertos por ciudad (zona metropolitana)")
    conteo = analizar.contar_por_ciudad(todos)
    nombres = analizar.nombres_reportados(todos)
    for ciudad in [*analizar.CIUDADES, analizar.OTRAS]:
        print(f"{ciudad:<20} {conteo[ciudad]:>5}")
        for nombre, n in nombres[ciudad].most_common(6):
            print(f"      como '{nombre}': {n}")

    titulo(f"3. Cobertura de campos ({len(nuestros)} eventos de las 5 ciudades)")
    for ruta, descripcion, _, pct in analizar.cobertura(nuestros):
        print(f"{pct:5.0f}%  {descripcion:<34} {ruta}")

    titulo("4. Detalles")
    precios = Counter(
        (rango.get("type"), rango.get("currency")) for e in nuestros for rango in e.get("priceRanges") or []
    )
    print("Tipos de precio (tipo, moneda):", dict(precios) or "ninguno")
    print("Estados:", dict(Counter(analizar.obtener(e, "dates.status.code") for e in nuestros)))
    generos = Counter(analizar.obtener(e, "classifications.0.genre.name") for e in nuestros)
    print("Géneros más comunes:", generos.most_common(10))

    imagenes = analizar.resumen_imagenes(nuestros)
    print(f"Imágenes por proporción: {dict(imagenes['proporciones'])}")
    print(f"Ancho máximo de imagen: {imagenes['ancho_maximo']} px")
    print(f"Eventos con alguna imagen que pide atribución: {imagenes['con_atribucion']}")

    puertas = sum(analizar.menciona_puertas(e) for e in nuestros)
    gira = sum(analizar.menciona_gira(e) for e in nuestros)
    print(f"Mencionan apertura de puertas en info/avisos: {puertas} ({porcentaje(puertas, len(nuestros))})")
    print(f"Tienen 'tour' o 'gira' en el nombre: {gira} ({porcentaje(gira, len(nuestros))})")

    complementos = analizar.posibles_complementos(nuestros)
    print(f"\nPosibles complementos (estacionamiento, VIP...): {len(complementos)}")
    for evento in complementos[:5]:
        print(f"   - {evento['name']}")

    duplicados = analizar.posibles_duplicados(nuestros)
    print(f"\nGrupos con mismo artista, recinto y día: {len(duplicados)}")
    for grupo in duplicados[:3]:
        print("   - " + " | ".join(e["name"] for e in grupo))

    titulo("5. Ejemplo completo de un evento (el que trae más campos)")
    ejemplo = analizar.elegir_ejemplo(nuestros or todos)
    if ejemplo:
        guardar(args.muestras / "ejemplo_evento.json", ejemplo)
        print(json.dumps(ejemplo, ensure_ascii=False, indent=2))
    else:
        print("No llegó ningún evento.")

    titulo("6. Resumen")
    print(f"Llamadas usadas: {cliente.llamadas} ({cliente.llamadas / LIMITE_DIARIO:.1%} del límite diario)")
    print(f"JSON crudo guardado en {args.muestras / 'eventos_mx.json'}")


if __name__ == "__main__":
    main()
