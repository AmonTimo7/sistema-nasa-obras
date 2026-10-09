from django.contrib import messages
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import Perfil
from core.permissoes import categorias_permitidas, exige_papel
from financeiro.models import ZERO, Obra
from financeiro.views import obra_atual

from .forms import FornecedorForm
from .models import Fornecedor


def _base(request, **extra):
    extra.update({"obra": obra_atual(request), "obras": Obra.objects.all()})
    return extra


@exige_papel(Perfil.COMPRAS)
def fornecedores(request):
    lista = (Fornecedor.objects
             .annotate(total=Coalesce(Sum("lancamentos__valor", filter=Q(lancamentos__valor__gt=0)), ZERO),
                       qtd=Count("lancamentos"), ultima=Max("lancamentos__data"))
             .order_by("-total", "nome"))
    termo = (request.GET.get("q") or "").strip()
    if termo:
        lista = lista.filter(Q(nome__icontains=termo) | Q(ramo__icontains=termo) | Q(cidade__icontains=termo))
    tipo = request.GET.get("tipo")
    if tipo in (Fornecedor.RECORRENTE, Fornecedor.COTACAO):
        lista = lista.filter(tipo=tipo)
    return render(request, "compras/fornecedores.html", _base(request, lista=lista, q=termo, tipo=tipo))


@exige_papel(Perfil.COMPRAS)
def fornecedor(request, pk):
    f = get_object_or_404(Fornecedor, pk=pk)
    permitidas = categorias_permitidas(request.user)
    compras = f.lancamentos.select_related("categoria", "subcategoria", "obra").order_by("-data", "-id")
    if permitidas is not None:
        compras = compras.filter(categoria__codigo__in=permitidas)
    total = compras.filter(valor__gt=0).aggregate(t=Coalesce(Sum("valor"), ZERO))["t"]
    return render(request, "compras/fornecedor.html", _base(
        request, f=f, compras=compras[:300], total=total, qtd=compras.count(),
        contas=f.contas.filter(pago_em__isnull=True).order_by("vencimento") if permitidas is None else []))


@exige_papel(Perfil.COMPRAS)
def fornecedor_form(request, pk=None):
    f = get_object_or_404(Fornecedor, pk=pk) if pk else None
    form = FornecedorForm(request.POST or None, instance=f)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"{obj.nome} salvo.")
        return redirect("compras:fornecedor", pk=obj.pk)
    return render(request, "financeiro/form_simples.html", _base(
        request, form=form, titulo=f"Editar {f.nome}" if f else "Novo fornecedor",
        subtitulo="Recorrente: compra direta, preço combinado. Cotação: pede orçamento antes.",
        voltar=reverse("compras:fornecedores")))
