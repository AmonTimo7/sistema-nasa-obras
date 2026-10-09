from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "financeiro"
    verbose_name = "Financeiro"

    def ready(self):
        from core.auditoria import registrar

        from . import models as m

        for modelo in (m.Obra, m.Aditivo, m.Lancamento, m.Medicao, m.ContaAPagar, m.LocacaoRecorrente, m.Empreita):
            registrar(modelo)
