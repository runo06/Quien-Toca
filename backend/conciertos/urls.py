from django.urls import path

from . import views

urlpatterns = [
    path("salud/", views.salud, name="salud"),
    path("ciudades/", views.CiudadesView.as_view(), name="ciudades"),
    path("conciertos/", views.ConciertosView.as_view(), name="conciertos"),
    path("conciertos/<slug:slug>/", views.ConciertoDetalleView.as_view(), name="concierto-detalle"),
]
