"""Quem entra onde. A conferência é na ROTA, não no template.

Esconder o botão não protege o endereço digitado na barra.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Perfil

# Categorias de lançamento que cada perfil pode ver e lançar (None = todas).
# Compras lança o que compra; o resto do financeiro é fechado.
CATEGORIAS_POR_PAPEL = {
    Perfil.SOCIO: None,
    Perfil.COMPRAS: [3, 4, 6, 7, 8],
    Perfil.OPERACAO: [],
    Perfil.JURIDICO: [],
}


def papel_de(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return Perfil.SOCIO
    perfil = getattr(user, "perfil", None)
    return perfil.papel if perfil else None


def categorias_permitidas(user):
    return CATEGORIAS_POR_PAPEL.get(papel_de(user), [])


def exige_papel(*papeis):
    """Libera a view só para os papéis listados (sócio entra em tudo)."""

    def decorador(view):
        @login_required
        @wraps(view)
        def embrulho(request, *args, **kwargs):
            papel = papel_de(request.user)
            if papel != Perfil.SOCIO and papel not in papeis:
                raise PermissionDenied("Seu perfil não tem acesso a esta área.")
            return view(request, *args, **kwargs)

        return embrulho

    return decorador


so_financeiro = exige_papel(Perfil.SOCIO)
