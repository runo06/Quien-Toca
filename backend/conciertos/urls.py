from django.urls import path

from . import views

urlpatterns = [
    path("salud/", views.salud, name="salud"),
    path("ciudades/", views.CiudadesView.as_view(), name="ciudades"),
    path("conciertos/", views.ConciertosView.as_view(), name="conciertos"),
    path("conciertos/<slug:slug>/", views.ConciertoDetalleView.as_view(), name="concierto-detalle"),
    path("artistas/", views.ArtistasView.as_view(), name="artistas"),
    path("artistas/<slug:slug>/", views.ArtistaDetalleView.as_view(), name="artista-detalle"),
    path("recintos/", views.RecintosView.as_view(), name="recintos"),
    path("recintos/<slug:slug>/", views.RecintoDetalleView.as_view(), name="recinto-detalle"),
]
