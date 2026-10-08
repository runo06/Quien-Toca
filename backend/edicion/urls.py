from django.urls import path

from . import views

urlpatterns = [
    path("", views.ResumenView.as_view(), name="edicion"),
    path("artistas/", views.ArtistasView.as_view(), name="edicion-artistas"),
    path("recintos/", views.RecintosView.as_view(), name="edicion-recintos"),
    path("giras/", views.GiraView.as_view(), name="edicion-gira"),
    path("conciertos/<slug:slug>/", views.ConciertoView.as_view(), name="edicion-concierto"),
    path("sugerencias/", views.SugerenciasView.as_view(), name="edicion-sugerencias"),
    path("sugerencias/<int:pk>/aprobar/", views.RevisarSugerenciaView.as_view(), {"accion": "aprobar"}),
    path("sugerencias/<int:pk>/rechazar/", views.RevisarSugerenciaView.as_view(), {"accion": "rechazar"}),
    path("reportes/", views.ReportesView.as_view(), name="edicion-reportes"),
    path("reportes/<int:pk>/aceptar/", views.RevisarReporteView.as_view(), {"accion": "aceptar"}),
    path("reportes/<int:pk>/descartar/", views.RevisarReporteView.as_view(), {"accion": "descartar"}),
]
