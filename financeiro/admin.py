from django.contrib import admin

from . import models as m


@admin.register(m.Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "situacao", "valor_contrato", "data_inicio", "data_termino")
    list_filter = ("situacao", "nicho")


@admin.register(m.Subcategoria)
class SubcategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "unidade", "ativa")
    list_filter = ("categoria", "ativa")
    list_editable = ("unidade", "ativa")


@admin.register(m.ModeloChecklist)
class ModeloChecklistAdmin(admin.ModelAdmin):
    list_display = ("grupo", "ordem", "nome", "ativo")
    list_editable = ("ordem", "ativo")
    list_filter = ("grupo",)


@admin.register(m.Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ("data", "obra", "categoria", "prestador", "fornecedor", "valor", "forma_pagamento")
    list_filter = ("obra", "categoria", "forma_pagamento")
    search_fields = ("descricao", "prestador__nome", "fornecedor__nome", "numero_nf")
    date_hierarchy = "data"
    raw_id_fields = ("prestador", "fornecedor", "estorno_de", "empreita", "medicao", "conta_origem")


for modelo in (m.ContaBancaria, m.Responsavel, m.Categoria, m.Aditivo, m.Medicao, m.Empreita,
               m.LocacaoRecorrente, m.ContaAPagar, m.ItemChecklist):
    admin.site.register(modelo)
