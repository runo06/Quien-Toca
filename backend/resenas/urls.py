from django.urls import path

from . import views

urlpatterns = [
    path("", views.ResenasView.as_view(), name="resenas"),
    path("mias/", views.MisResenasView.as_view(), name="mis-resenas"),
    path("<int:pk>/", views.ResenaDetalleView.as_view(), name="resena"),
    path("<int:pk>/util/", views.MeSirvioView.as_view(), name="resena-util"),
    path("<int:pk>/reportar/", views.ReportarView.as_view(), name="resena-reportar"),
]
