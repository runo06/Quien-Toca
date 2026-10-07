from django.urls import path

from . import views

urlpatterns = [path("", views.SugerenciasView.as_view(), name="sugerencias")]
