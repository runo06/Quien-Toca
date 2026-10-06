from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/cuentas/", include("cuentas.urls")),
    path("api/resenas/", include("resenas.urls")),
    path("api/", include("conciertos.urls")),
]
