# ¿Quién toca?

Cartelera de próximos conciertos por ciudad, con enlace a la boletera oficial
y reseñas de quienes ya asistieron. La app no vende boletos.

Nombre técnico: `quien-toca`.

## Fase 0: comprobar los datos

Un script que descarga los conciertos de música de México desde la API
Discovery de Ticketmaster y mide cuántos hay en Puebla, Tlaxcala, Ciudad de
México, Guadalajara y Monterrey, y qué campos traen.

Requisitos: Docker Desktop abierto y una clave de la API (ver `.env.example`).

Desde la raíz del repositorio, en PowerShell:

```powershell
# 1. Construir la imagen
docker build -t quien-toca-fase0 fase0

# 2. Correr las pruebas (no necesitan clave ni internet)
docker run --rm quien-toca-fase0 python -m pytest pruebas -v

# 3. Explorar los datos (necesita .env con la clave)
docker run --rm --env-file .env -v "${PWD}/fase0/muestras:/app/muestras" quien-toca-fase0
```

El JSON crudo queda en `fase0/muestras/`, que no se sube a Git.
