from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from .models import Perfil
from .permissoes import papel_de


@login_required
def inicio(request):
    """Cada perfil cai na tela que usa."""
    papel = papel_de(request.user)
    if papel == Perfil.SOCIO:
        return redirect("financeiro:painel")
    if papel == Perfil.COMPRAS:
        return redirect("financeiro:lancamentos")
    if papel == Perfil.JURIDICO:
        return redirect("juridico:prestadores")
    return redirect("financeiro:checklist")


@login_required
def trocar_senha(request):
    perfil = getattr(request.user, "perfil", None)
    obrigatoria = bool(perfil and perfil.precisa_trocar_senha)
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        if perfil:
            perfil.precisa_trocar_senha = False
            perfil.save(update_fields=["precisa_trocar_senha"])
        messages.success(request, "Senha trocada.")
        return redirect("inicio")
    return render(request, "core/trocar_senha.html", {"form": form, "obrigatoria": obrigatoria})
