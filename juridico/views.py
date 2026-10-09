from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import Perfil
from core.permissoes import exige_papel
from financeiro.models import Obra
from financeiro.views import obra_atual

from .forms import PrestadorForm
from .models import Prestador


@exige_papel(Perfil.JURIDICO)
def prestadores(request):
    lista = Prestador.objects.all()
    termo = (request.GET.get("q") or "").strip()
    if termo:
        lista = lista.filter(Q(nome__icontains=termo) | Q(funcao__icontains=termo) | Q(cidade__icontains=termo))
    if request.GET.get("inativos") != "1":
        lista = lista.filter(ativo=True)
    return render(request, "juridico/prestadores.html", {
        "lista": lista, "q": termo, "obra": obra_atual(request), "obras": Obra.objects.all(),
        "inativos": request.GET.get("inativos") == "1",
    })


@exige_papel(Perfil.JURIDICO)
def prestador_form(request, pk=None):
    p = get_object_or_404(Prestador, pk=pk) if pk else None
    form = PrestadorForm(request.POST or None, instance=p)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"{obj.nome} salvo.")
        return redirect("financeiro:prestador", pk=obj.pk)
    return render(request, "financeiro/form_simples.html", {
        "form": form, "obra": obra_atual(request), "obras": Obra.objects.all(),
        "titulo": f"Editar {p.nome}" if p else "Novo prestador",
        "subtitulo": "Dados pessoais protegidos pela LGPD: só sócios e jurídico veem.",
        "voltar": reverse("juridico:prestadores"),
    })
