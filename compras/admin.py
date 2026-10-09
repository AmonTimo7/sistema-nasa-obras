from django.contrib import admin

from .models import Fornecedor


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "ramo", "telefone", "ativo")
    search_fields = ("nome", "ramo")
    list_filter = ("tipo", "ativo")
