"""As contas que as telas mostram. Cada função diz o que mede e contra o quê.

Regra da casa: todo percentual declara o denominador na própria tela
("31% de R$ 11,7 mi"). Um número sem denominador muda de sentido sem
ninguém perceber.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from .models import ZERO, Categoria, ContaAPagar, Lancamento, Medicao, Obra, Subcategoria

DINHEIRO = Coalesce(Sum("valor"), ZERO)
MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro",
         "Outubro", "Novembro", "Dezembro"]


def pct(parte, todo):
    """Percentual com uma casa, ou None quando não há base (nunca 'infinito')."""
    if not todo:
        return None
    return (Decimal(parte) * 100 / Decimal(todo)).quantize(Decimal("0.1"))


def nome_mes(d, curto=False):
    if curto:
        return f"{MESES[d.month][:3]}/{str(d.year)[2:]}"
    return f"{MESES[d.month]} de {d.year}"


def proximo_mes(d):
    return date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def resumo_obra(obra, hoje=None):
    """Os números de cima do painel (a aba de resumo da planilha).

    - gasto: soma dos lançamentos; estornos entram negativos e abatem.
    - faturado: medições com NF emitida. recebido: as pagas.
    - caixa: recebido − gasto. É o dinheiro da obra hoje, não o lucro:
      lucro só existe quando a obra acaba e tudo foi faturado.
    - resultado_previsto: contrato − gasto. Quanto sobra se nada mais
      fosse gasto — serve para ver a margem encolhendo, não como promessa.
    - prazo_pct: dias corridos desde o início ÷ duração prevista (obra
      corre em dia corrido, sábado incluso).
    """
    hoje = hoje or date.today()
    lanc = obra.lancamentos.all()
    gasto = lanc.aggregate(t=DINHEIRO)["t"]
    medicoes = list(obra.medicoes.all())
    faturado = sum((m.valor for m in medicoes if m.data_emissao), ZERO)
    recebido = sum((m.valor_liquido for m in medicoes if m.data_pagamento), ZERO)
    a_receber = sum((m.valor_liquido for m in medicoes if m.data_emissao and not m.data_pagamento), ZERO)
    atrasadas = [m for m in medicoes if m.situacao(hoje) == "atrasada"]
    contrato = obra.valor_total

    prazo_pct = dias_passados = dias_total = dias_restantes = None
    if obra.data_inicio and obra.data_termino and obra.data_termino > obra.data_inicio:
        dias_total = (obra.data_termino - obra.data_inicio).days
        dias_passados = max(0, min(dias_total, (hoje - obra.data_inicio).days))
        dias_restantes = (obra.data_termino - hoje).days
        prazo_pct = pct(dias_passados, dias_total)

    mes_atual = hoje.replace(day=1)
    gasto_mes = lanc.filter(competencia=mes_atual).aggregate(t=DINHEIRO)["t"]
    gasto_mes_anterior = lanc.filter(competencia=(mes_atual - timedelta(days=1)).replace(day=1)).aggregate(t=DINHEIRO)["t"]

    return {
        "contrato": contrato,
        "aditivos": obra.valor_aditivos,
        "gasto": gasto,
        "gasto_pct": pct(gasto, contrato),
        "gasto_mes": gasto_mes,
        "gasto_mes_anterior": gasto_mes_anterior,
        "faturado": faturado,
        "faturado_pct": pct(faturado, contrato),
        "a_faturar": contrato - faturado,
        "recebido": recebido,
        "a_receber": a_receber,
        "medicoes_atrasadas": atrasadas,
        "caixa": recebido - gasto,
        "resultado_previsto": contrato - gasto,
        "margem_pct": pct(contrato - gasto, contrato),
        "prazo_pct": prazo_pct,
        "dias_passados": dias_passados,
        "dias_total": dias_total,
        "dias_restantes": dias_restantes,
        "dias_atraso": -dias_restantes if dias_restantes is not None and dias_restantes < 0 else 0,
        "lancamentos": lanc.count(),
    }


def pendencias(obra):
    """Lançamentos com algo faltando (comprovante, NF). Lista curta e acionável."""
    itens = []
    qs = obra.lancamentos.select_related("categoria", "prestador", "fornecedor").exclude(
        categoria__codigo__in=[Categoria.IMPOSTOS, Categoria.ESTORNOS])
    for l in qs:
        faltas = l.pendencias
        if faltas:
            itens.append((l, faltas))
    return itens


def gasto_por_mes(obra, categoria=None):
    """[(mês, total)], do início da obra até o último mês com gasto, meses vazios com zero."""
    qs = obra.lancamentos.all()
    if categoria:
        qs = qs.filter(categoria=categoria)
    linhas = dict(qs.values_list("competencia").annotate(t=DINHEIRO).order_by("competencia"))
    ini = obra.data_inicio.replace(day=1) if obra.data_inicio else (min(linhas) if linhas else None)
    if ini is None:
        return []
    fim = max(list(linhas) + [min(date.today(), obra.data_termino or date.today()).replace(day=1)])
    if linhas:
        ini = min(ini, min(linhas))
    meses = []
    atual = ini
    while atual <= fim and len(meses) < 60:
        meses.append((atual, linhas.get(atual, ZERO)))
        atual = proximo_mes(atual)
    return meses


def acumulado(obra):
    """Gasto acumulado e faturado acumulado, mês a mês (faturado entra no mês da NF)."""
    medicoes = [m for m in obra.medicoes.all() if m.data_emissao]
    gasto = faturado = ZERO
    saida = []
    for mes, valor in gasto_por_mes(obra):
        gasto += valor
        faturado += sum((m.valor for m in medicoes if m.data_emissao.replace(day=1) == mes), ZERO)
        saida.append({"mes": mes, "gasto": gasto, "faturado": faturado})
    return saida


def gasto_por_categoria(obra, competencia=None):
    """Todas as categorias, inclusive as zeradas: a lista também responde
    'quais categorias existem?'. Percentual sobre o gasto positivo."""
    filtro = Q(lancamentos__obra=obra)
    if competencia:
        filtro &= Q(lancamentos__competencia=competencia)
    cats = Categoria.objects.annotate(
        total=Coalesce(Sum("lancamentos__valor", filter=filtro), ZERO),
        qtd=Count("lancamentos", filter=filtro),
    )
    lista = sorted(cats, key=lambda c: (c.total <= 0, -c.total))
    positivo = sum((c.total for c in lista if c.total > 0), ZERO)
    maior = max((c.total for c in lista), default=ZERO) or Decimal("1")
    for c in lista:
        c.pct = pct(c.total, positivo) if c.total > 0 else None
        c.largura = float(max(c.total, ZERO) * 100 / maior) if maior > 0 else 0
    return lista


def maiores_favorecidos(obra, n=8):
    qs = obra.lancamentos.filter(valor__gt=0)
    prest = (qs.exclude(prestador=None).values("prestador__id", "prestador__nome")
             .annotate(total=DINHEIRO, qtd=Count("id")))
    forn = (qs.filter(prestador=None).exclude(fornecedor=None).values("fornecedor__id", "fornecedor__nome")
            .annotate(total=DINHEIRO, qtd=Count("id")))
    itens = [{"tipo": "prestador", "id": p["prestador__id"], "nome": p["prestador__nome"],
              "total": p["total"], "qtd": p["qtd"]} for p in prest]
    itens += [{"tipo": "fornecedor", "id": f["fornecedor__id"], "nome": f["fornecedor__nome"],
               "total": f["total"], "qtd": f["qtd"]} for f in forn]
    itens.sort(key=lambda x: x["total"], reverse=True)
    return itens[:n]


def contas_resumo(obra=None, hoje=None):
    """Contas em aberto por urgência. 'Na semana' = vence em até 7 dias."""
    hoje = hoje or date.today()
    qs = ContaAPagar.objects.filter(pago_em__isnull=True)
    if obra is not None:
        qs = qs.filter(obra=obra)
    vencidas = qs.filter(vencimento__lt=hoje)
    semana = qs.filter(vencimento__gte=hoje, vencimento__lte=hoje + timedelta(days=7))
    soma = lambda q: q.aggregate(t=DINHEIRO)["t"]  # noqa: E731
    return {
        "vencidas": vencidas.count(), "vencidas_valor": soma(vencidas),
        "semana": semana.count(), "semana_valor": soma(semana),
        "aberto": qs.count(), "aberto_valor": soma(qs),
    }


def proximas_contas(obra=None, n=6, hoje=None):
    hoje = hoje or date.today()
    qs = ContaAPagar.objects.filter(pago_em__isnull=True).select_related("fornecedor", "obra").order_by("vencimento")
    if obra is not None:
        qs = qs.filter(obra=obra)
    itens = list(qs[:n])
    for c in itens:
        c.sit = c.situacao(hoje)
    return itens


def lancamentos_filtrados(obra, params, categorias_permitidas=None):
    qs = (obra.lancamentos.select_related("categoria", "subcategoria", "prestador", "fornecedor")
          .prefetch_related("contas").order_by("-data", "-id"))
    if categorias_permitidas is not None:
        qs = qs.filter(categoria__codigo__in=categorias_permitidas)
    mes = params.get("mes")
    if mes:
        try:
            ano, m = mes.split("-")
            qs = qs.filter(competencia=date(int(ano), int(m), 1))
        except ValueError:
            pass
    for campo, filtro in (("categoria", "categoria__codigo"), ("subcategoria", "subcategoria_id"),
                          ("prestador", "prestador_id"), ("fornecedor", "fornecedor_id"),
                          ("responsavel", "responsavel_id"), ("empreita", "empreita_id")):
        valor = params.get(campo)
        if valor and str(valor).isdigit():
            qs = qs.filter(**{filtro: valor})
    if params.get("forma"):
        qs = qs.filter(forma_pagamento=params["forma"])
    if params.get("sem_comprovante"):
        qs = qs.filter(comprovante="", valor__gt=0).exclude(forma_pagamento__in=["boleto", "faturado"])
    termo = (params.get("q") or "").strip()
    for palavra in termo.split():
        qs = qs.filter(Q(descricao__icontains=palavra) | Q(prestador__nome__icontains=palavra)
                       | Q(fornecedor__nome__icontains=palavra) | Q(numero_nf__icontains=palavra)
                       | Q(observacao__icontains=palavra))
    return qs


def meses_da_obra(obra):
    return list(obra.lancamentos.values_list("competencia", flat=True).distinct().order_by("-competencia"))


def fechamento_do_mes(obra, competencia):
    """O bloco do mês da planilha: cada categoria, com seus grupos e linhas."""
    lancs = (obra.lancamentos.filter(competencia=competencia)
             .select_related("categoria", "subcategoria", "prestador", "fornecedor").order_by("data", "id"))
    por_cat = {}
    for l in lancs:
        cat = por_cat.setdefault(l.categoria.codigo, {"categoria": l.categoria, "grupos": {}, "total": ZERO})
        if l.categoria.codigo == Categoria.MAO_DE_OBRA and l.prestador_id:
            grupo = l.prestador.nome
        elif l.subcategoria_id:
            grupo = l.subcategoria.nome
        else:
            grupo = "Geral"
        g = cat["grupos"].setdefault(grupo, {"nome": grupo, "itens": [], "total": ZERO})
        g["itens"].append(l)
        g["total"] += l.valor
        cat["total"] += l.valor
    blocos = []
    for codigo in sorted(por_cat):
        c = por_cat[codigo]
        c["grupos"] = sorted(c["grupos"].values(), key=lambda g: -g["total"])
        blocos.append(c)
    return blocos, sum((b["total"] for b in blocos), ZERO)


def matriz_mes_categoria(obra):
    """A 'visão geral da obra' da planilha: categoria × mês, com totais."""
    meses = [m for m, _ in gasto_por_mes(obra)]
    dados = {}
    for comp, cod, t in (obra.lancamentos.values_list("competencia", "categoria__codigo").annotate(t=DINHEIRO)):
        dados[(cod, comp)] = t
    linhas = []
    for cat in Categoria.objects.all():
        valores = [dados.get((cat.codigo, m), ZERO) for m in meses]
        linhas.append({"categoria": cat, "valores": valores, "total": sum(valores, ZERO)})
    totais = [sum((l["valores"][i] for l in linhas), ZERO) for i in range(len(meses))]
    return {"meses": meses, "linhas": linhas, "totais": totais, "total": sum(totais, ZERO)}


def matriz_materiais(obra):
    """A 'visão geral de compras por materiais': material × mês."""
    meses = [m for m, _ in gasto_por_mes(obra)]
    dados = {}
    qs = obra.lancamentos.filter(categoria__codigo=Categoria.MATERIAIS)
    for comp, sub, t in qs.values_list("competencia", "subcategoria_id").annotate(t=DINHEIRO):
        dados[(sub, comp)] = t
    linhas = []
    for sub in list(Subcategoria.objects.filter(categoria__codigo=Categoria.MATERIAIS)) + [None]:
        sid = sub.pk if sub else None
        valores = [dados.get((sid, m), ZERO) for m in meses]
        total = sum(valores, ZERO)
        if sub is None and not total:
            continue
        linhas.append({"nome": sub.nome if sub else "Sem tipo", "id": sid, "valores": valores, "total": total})
    linhas.sort(key=lambda l: -l["total"])
    return {"meses": meses, "linhas": linhas}


def controle_por_quantidade(obra, nome_subcategoria, categoria=Categoria.MATERIAIS):
    """Controle de concreto (m³) ou de combustível (litros): quantidade, valor e preço médio."""
    qs = (obra.lancamentos.filter(categoria__codigo=categoria, subcategoria__nome__iexact=nome_subcategoria)
          .select_related("fornecedor").order_by("data"))
    itens = list(qs)
    qtd = sum((l.quantidade or ZERO for l in itens), ZERO)
    valor = sum((l.valor for l in itens), ZERO)
    com_qtd = sum((l.valor for l in itens if l.quantidade), ZERO)
    return {"itens": itens, "quantidade": qtd, "valor": valor,
            "preco_medio": (com_qtd / qtd).quantize(Decimal("0.01")) if qtd else None,
            "sem_quantidade": sum(1 for l in itens if not l.quantidade)}


def visao_geral(hoje=None):
    """Todas as obras lado a lado, com faturamento por nicho."""
    hoje = hoje or date.today()
    obras = []
    for o in Obra.objects.all():
        r = resumo_obra(o, hoje)
        obras.append({"obra": o, "r": r})
    nichos = {}
    for item in obras:
        n = nichos.setdefault(item["obra"].get_nicho_display(), {"faturado": ZERO, "gasto": ZERO, "contrato": ZERO})
        n["faturado"] += item["r"]["faturado"]
        n["gasto"] += item["r"]["gasto"]
        n["contrato"] += item["r"]["contrato"]
        n["saldo"] = n["faturado"] - n["gasto"]
    inicio_mes = hoje.replace(day=1)
    impostos_mes = Lancamento.objects.filter(categoria__codigo=Categoria.IMPOSTOS, competencia=inicio_mes).aggregate(t=DINHEIRO)["t"]
    faturado_mes = Medicao.objects.filter(data_emissao__gte=inicio_mes, data_emissao__lt=proximo_mes(inicio_mes)).aggregate(t=DINHEIRO)["t"]
    gasto_mes = Lancamento.objects.filter(competencia=inicio_mes).aggregate(t=DINHEIRO)["t"]
    return {"obras": obras, "nichos": nichos, "impostos_mes": impostos_mes, "faturado_mes": faturado_mes,
            "gasto_mes": gasto_mes}
