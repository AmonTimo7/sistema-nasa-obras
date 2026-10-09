import time
from datetime import date

from django.conf import settings

from .models import Perfil
from .permissoes import papel_de


def perfil(request):
    papel = papel_de(request.user)
    contexto = {
        "papel": papel,
        "ve_financeiro": papel == Perfil.SOCIO,
        "ve_compras": papel in (Perfil.SOCIO, Perfil.COMPRAS),
        "ve_juridico": papel in (Perfil.SOCIO, Perfil.JURIDICO),
        "lanca": papel in (Perfil.SOCIO, Perfil.COMPRAS),
        # em desenvolvimento o navegador não pode guardar CSS/JS velho; em
        # produção o ManifestStaticFilesStorage já põe o hash no nome
        "v": str(int(time.time())) if settings.DEBUG else "",
    }
    if papel == Perfil.SOCIO:
        from financeiro.models import ContaAPagar

        contexto["n_vencidas"] = ContaAPagar.objects.filter(pago_em__isnull=True, vencimento__lt=date.today()).count()
    return contexto
