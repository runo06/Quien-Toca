# ¿Quién toca?

Cartelera de próximos conciertos por ciudad, con enlace a la boletera oficial
y reseñas de quienes ya asistieron. La app no vende boletos.

Nombre técnico: `quien-toca`.

## Correr el proyecto

Requisitos: Docker Desktop abierto.

```powershell
# 1. Variables de entorno: copia la plantilla y llena los valores vacíos
copy .env.example .env

# 2. Levantar base de datos, backend y frontend (aplica las migraciones al arrancar)
docker compose up

# 3. En otra terminal: crear tu usuario del panel de administración
docker compose exec backend python manage.py createsuperuser
```

| Qué | Dirección |
|---|---|
| Página | http://localhost:5173 (o el puerto de `PUERTO_FRONTEND`) |
| API | http://localhost:8000/api/conciertos/ (o el de `PUERTO_BACKEND`) |
| Panel | http://localhost:8000/admin |

### API

| Endpoint | Parámetros |
|---|---|
| `GET /api/ciudades/` | — |
| `GET /api/conciertos/` | `ciudad`, `q`, `desde`, `hasta` (AAAA-MM-DD), `orden` (`fecha` o `precio`), `pagina` |
| `GET /api/conciertos/<slug>/` | — |

### Importar conciertos de Ticketmaster

```powershell
docker compose exec backend python manage.py importar_ticketmaster
docker compose exec backend python manage.py importar_ticketmaster -v 2   # lista los descartados
```

No duplica: si el concierto ya existe lo actualiza, y nunca borra los que ya
pasaron. Los conciertos capturados a mano no se tocan.

### Pruebas

```powershell
docker compose run --rm backend python manage.py test
```

### Comandos útiles de Docker

| Comando | Qué hace |
|---|---|
| `docker compose up -d` | Levanta en segundo plano |
| `docker compose logs -f backend` | Muestra los logs del backend |
| `docker compose down` | Detiene y borra los contenedores (los datos se quedan en el volumen) |
| `docker compose down -v` | Igual, pero **borra también la base de datos** |
| `docker compose build` | Reconstruye la imagen tras cambiar `requirements.txt` |

## Estructura

```
backend/
├── config/              configuración de Django
└── conciertos/
    ├── models.py        Ciudad, Recinto, Artista, Concierto, PrecioZona
    ├── admin.py         panel de administración
    ├── views.py         API REST (serializers.py, urls.py, paginacion.py)
    ├── importacion/     cliente de Ticketmaster, traducción e importador
    └── tests/           pruebas con respuestas de ejemplo (sin llamar a la API)
frontend/src/
├── App.jsx              rutas
├── api.js               llamadas al backend
├── contexto/            ciudades compartidas
├── hooks/               usarPeticion, usarCartelera
├── paginas/             Inicio, Concierto, No encontrada
├── componentes/         Boleto, SelectorCiudad, Taquilla, Cartel...
├── utilidades/          fechas, rangos, textos
└── estilos/base.css     tokens y estilos del prototipo
fase0/                   exploración inicial de los datos (ver docs/fase0-hallazgos.md)
docs/diseno/             prototipo visual
```
