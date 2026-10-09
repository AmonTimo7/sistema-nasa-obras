from django.urls import path

from . import views

app_name = "compras"

urlpatterns = [
    path("fornecedores/", views.fornecedores, name="fornecedores"),
    path("fornecedores/novo/", views.fornecedor_form, name="fornecedor_novo"),
    path("fornecedores/<int:pk>/", views.fornecedor, name="fornecedor"),
    path("fornecedores/<int:pk>/editar/", views.fornecedor_form, name="fornecedor_editar"),
]
