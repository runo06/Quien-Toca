# Imagen base: Python 3.13 en una Debian reducida ("slim").
FROM python:3.13-slim

# No crear archivos .pyc, mostrar la salida al momento y escribir acentos sin errores.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

# Primero solo las dependencias: Docker guarda esta capa en caché y no
# reinstala nada mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Después el código, que cambia seguido.
COPY . .

CMD ["python", "explorar.py"]
