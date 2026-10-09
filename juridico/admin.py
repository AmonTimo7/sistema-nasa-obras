from django.contrib import admin

from .models import Prestador


@admin.register(Prestador)
class PrestadorAdmin(admin.ModelAdmin):
    list_display = ("nome", "funcao", "valor_diaria", "telefone", "ativo")
    search_fields = ("nome", "funcao")
    list_filter = ("ativo",)
