from django.urls import path

from . import views

urlpatterns = [
    path("artistas/<slug:slug>/seguir/", views.SeguirArtistaView.as_view(), name="seguir-artista"),
    path("conciertos/<slug:slug>/guardar/", views.GuardarConciertoView.as_view(), name="guardar-concierto"),
    path("mis-conciertos/", views.MisConciertosView.as_view(), name="mis-conciertos"),
]
