from django.urls import path

from . import views

app_name = "juridico"

urlpatterns = [
    path("prestadores/", views.prestadores, name="prestadores"),
    path("prestadores/novo/", views.prestador_form, name="prestador_novo"),
    path("prestadores/<int:pk>/editar/", views.prestador_form, name="prestador_editar"),
]
