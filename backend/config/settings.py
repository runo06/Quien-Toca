"""Configuración de Django para ¿Quién toca?

Todo lo secreto o lo que cambia entre desarrollo y producción sale de
variables de entorno; nada sensible vive en el código.
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def variable_requerida(nombre):
    valor = os.environ.get(nombre)
    if not valor:
        raise ImproperlyConfigured(f"Falta la variable de entorno {nombre}. Revisa tu archivo .env.")
    return valor


SECRET_KEY = variable_requerida("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",") if h.strip()]
# Render define esta variable con el dominio del servicio (quien-toca-api.onrender.com).
if render_host := os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(render_host)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # búsqueda sin acentos (unaccent) y campos de lista
    "rest_framework",
    "corsheaders",
    "conciertos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CORS debe ir antes de CommonMiddleware para agregar sus cabeceras a todas las respuestas.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if not DEBUG:
    # En producción WhiteNoise sirve los estáticos (CSS del panel) sin un servidor aparte.
    # Va justo después de SecurityMiddleware. En desarrollo los sirve runserver.
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Una sola variable con toda la conexión: postgres://usuario:clave@host:puerto/base.
# Es el mismo formato que entrega Neon, así producción no cambia este código.
# conn_health_checks: Neon suspende la base tras 5 minutos sin uso; antes de reusar
# una conexión se comprueba que siga viva.
DATABASES = {
    "default": dj_database_url.parse(
        variable_requerida("DATABASE_URL"), conn_max_age=600, conn_health_checks=True
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True  # se guarda en UTC y se muestra en la hora de México

STATIC_URL = "static/"
# collectstatic junta aquí los estáticos; WhiteNoise los sirve comprimidos y con
# nombres versionados (se pueden guardar en caché para siempre).
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TICKETMASTER_API_KEY = os.environ.get("TICKETMASTER_API_KEY", "")

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "conciertos.paginacion.Paginacion",
    "PAGE_SIZE": 20,
    "COERCE_DECIMAL_TO_STRING": False,  # precios como números en el JSON, no como texto
}

# Orígenes (dominios) del frontend que pueden llamar a la API desde el navegador.
# En desarrollo no hace falta: Vite reenvía /api al backend (mismo origen).
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGENES_PERMITIDOS", "").split(",") if o.strip()
]

if not DEBUG:
    # Render atiende HTTPS y pasa la petición a Django por HTTP; esta cabecera
    # le dice a Django que el visitante sí llegó por HTTPS.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    # La ruta de salud la llama Render por HTTP interno: no se redirige.
    SECURE_REDIRECT_EXEMPT = [r"^api/salud/$"]
    SESSION_COOKIE_SECURE = True  # las cookies del panel solo viajan por HTTPS
    CSRF_COOKIE_SECURE = True
    # HSTS: el navegador recuerda usar siempre HTTPS. Una hora para empezar;
    # súbelo (p. ej. a 31536000, un año) cuando todo funcione bien.
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SEGUNDOS", "3600"))
    # Subdominios y lista de precarga solo tienen sentido con un dominio propio,
    # no con quien-toca-api.onrender.com.
    SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

# Registra en la consola (los logs de Render) los errores 500 con su detalle.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["consola"], "level": "WARNING"},
    # Los 4xx (404, 400) son normales; solo interesan los errores del servidor.
    "loggers": {"django.request": {"handlers": ["consola"], "level": "ERROR", "propagate": False}},
}
