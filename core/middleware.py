import threading

from django.shortcuts import redirect
from django.urls import reverse

_local = threading.local()


def usuario_atual():
    """Usuário da requisição em andamento (para a auditoria), ou None."""
    return getattr(_local, "usuario", None)


class UsuarioAtualMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        _local.usuario = usuario if usuario is not None and usuario.is_authenticated else None
        try:
            return self.get_response(request)
        finally:
            _local.usuario = None


class TrocaDeSenhaObrigatoriaMiddleware:
    """Com senha de fábrica, só a tela de troca e o sair ficam abertos."""

    LIVRES = ("trocar_senha", "logout", "login")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            perfil = getattr(user, "perfil", None)
            if perfil is not None and perfil.precisa_trocar_senha:
                livres = {reverse(n) for n in self.LIVRES}
                if request.path not in livres and not request.path.startswith("/static/"):
                    return redirect("trocar_senha")
        return self.get_response(request)
