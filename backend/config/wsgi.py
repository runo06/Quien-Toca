"""Punto de entrada WSGI: lo usará el servidor de producción en la fase 3."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
