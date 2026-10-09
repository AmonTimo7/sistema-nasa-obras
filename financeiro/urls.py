from django.urls import path

from . import views

app_name = "financeiro"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("visao-geral/", views.visao_geral, name="visao_geral"),
    path("obras/", views.obras, name="obras"),
    path("obras/nova/", views.obra_form, name="obra_nova"),
    path("obras/<int:pk>/editar/", views.obra_form, name="obra_editar"),

    path("lancamentos/", views.lancamentos, name="lancamentos"),
    path("lancamentos/exportar.xlsx", views.exportar_lancamentos, name="exportar"),
    path("lancamentos/novo/", views.lancamento_escolher, name="lancamento_escolher"),
    path("lancamentos/novo/<int:codigo>/", views.lancamento_form, name="lancamento_novo"),
    path("lancamentos/<int:pk>/", views.lancamento_detalhe, name="lancamento"),
    path("lancamentos/<int:pk>/editar/", views.lancamento_form, name="lancamento_editar"),
    path("lancamentos/<int:pk>/excluir/", views.lancamento_excluir, name="lancamento_excluir"),
    path("pendencias/", views.pendencias, name="pendencias"),
    path("mes/", views.fechamento, name="fechamento"),
    path("mes/<int:ano>/<int:mes>/", views.fechamento, name="fechamento_mes"),

    path("mao-de-obra/", views.mao_de_obra, name="mao_de_obra"),
    path("prestadores/<int:pk>/", views.prestador_detalhe, name="prestador"),
    path("empreitas/", views.empreitas, name="empreitas"),
    path("empreitas/nova/", views.empreita_form, name="empreita_nova"),
    path("empreitas/<int:pk>/", views.empreita_detalhe, name="empreita"),
    path("empreitas/<int:pk>/editar/", views.empreita_form, name="empreita_editar"),

    path("contas/", views.contas, name="contas"),
    path("contas/nova/", views.conta_form, name="conta_nova"),
    path("contas/<int:pk>/", views.conta_form, name="conta_editar"),
    path("contas/<int:pk>/pagar/", views.conta_pagar, name="conta_pagar"),
    path("contas/<int:pk>/desfazer/", views.conta_desfazer, name="conta_desfazer"),
    path("locacoes/nova/", views.locacao_form, name="locacao_nova"),
    path("locacoes/<int:pk>/", views.locacao_form, name="locacao_editar"),

    path("contrato/", views.contrato, name="contrato"),
    path("medicoes/nova/", views.medicao_form, name="medicao_nova"),
    path("medicoes/<int:pk>/", views.medicao_form, name="medicao_editar"),
    path("medicoes/<int:pk>/excluir/", views.medicao_excluir, name="medicao_excluir"),
    path("aditivos/novo/", views.aditivo_form, name="aditivo_novo"),
    path("aditivos/<int:pk>/", views.aditivo_form, name="aditivo_editar"),

    path("relatorios/", views.relatorios, name="relatorios"),
    path("checklist/", views.checklist, name="checklist"),
    path("checklist/<int:pk>/", views.checklist_item, name="checklist_item"),
    path("responsaveis/", views.responsaveis, name="responsaveis"),
    path("arquivo/<str:modelo>/<int:pk>/<str:campo>/", views.arquivo, name="arquivo"),
]
