from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("registro/", views.RegistroView.as_view(), name="registro"),
    path("entrar/", views.EntrarView.as_view(), name="entrar"),
    # Cambia un refresh por un access nuevo (y un refresh nuevo: el viejo queda anulado).
    path("renovar/", TokenRefreshView.as_view(), name="renovar"),
    path("salir/", views.SalirView.as_view(), name="salir"),
    path("yo/", views.YoView.as_view(), name="yo"),
]
