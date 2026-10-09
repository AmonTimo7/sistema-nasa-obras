"""As regras que a planilha deixava na mão de quem digitava.

Cada função diz o que garante. As telas e o admin chamam estas funções; nada
de conta escondida em template ou JavaScript.
"""
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from .models import (
    ZERO,
    Categoria,
    ContaAPagar,
    ItemChecklist,
    Lancamento,
    Medicao,
    ModeloChecklist,
)

CENTAVO = Decimal("0.01")
TIPOS_CALCULADOS = ("diarias", "empreita", "mensal")


def arredondar(valor):
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def primeiro_dia(d):
    return d.replace(day=1)


def somar_meses(d, meses, dia=None):
    """Mesmo dia N meses depois; dia 31 em mês de 30 vira o último dia."""
    ano = d.year + (d.month - 1 + meses) // 12
    mes = (d.month - 1 + meses) % 12 + 1
    dia = dia or d.day
    for tentativa in (dia, 30, 29, 28):
        try:
            return date(ano, mes, min(dia, tentativa))
        except ValueError:
            continue
    return date(ano, mes, 28)


# ---------------------------------------------------------------------------
# Parcelas: repartir e somar de volta precisam fechar no centavo
# ---------------------------------------------------------------------------

def dividir(valor, partes):
    """R$ 100 em 3 -> 33,33 + 33,33 + 33,34. A sobra vai na última parcela,
    então somar as parcelas devolve exatamente o valor (sem float)."""
    valor = arredondar(valor)
    partes = max(1, int(partes))
    base = (valor / partes).quantize(CENTAVO, rounding="ROUND_DOWN")
    lista = [base] * partes
    lista[-1] = valor - base * (partes - 1)
    return lista


# ---------------------------------------------------------------------------
# Mão de obra
# ---------------------------------------------------------------------------

def valor_mao_de_obra(diarias, valor_diaria, adicional, desconto):
    """Diárias × valor da diária + empreita/tarefa − vales descontados."""
    bruto = Decimal(diarias or 0) * Decimal(valor_diaria or 0) + Decimal(adicional or 0)
    return arredondar(bruto - Decimal(desconto or 0))


def saldo_de_vales(prestador, obra=None, ignorar=None):
    """Quanto foi adiantado ao prestador e ainda não descontado.

    Vale = lançamento de mão de obra do tipo "adiantamento". É descontado no
    campo `desconto` dos pagamentos seguintes. Na planilha isso vivia escrito
    na descrição ("VALE 280 - DESC. 140 + 140 NA OUTRA SEMANA").
    """
    qs = Lancamento.objects.filter(prestador=prestador, categoria__codigo=Categoria.MAO_DE_OBRA)
    if obra is not None:
        qs = qs.filter(obra=obra)
    if ignorar is not None and ignorar.pk:
        qs = qs.exclude(pk=ignorar.pk)
    vales = qs.filter(tipo_mao_de_obra="adiantamento").aggregate(t=Coalesce(Sum("valor"), ZERO))["t"]
    descontado = qs.aggregate(t=Coalesce(Sum("desconto"), ZERO))["t"]
    return vales - descontado


# ---------------------------------------------------------------------------
# Lançamento: preparar antes de gravar, efeitos depois de gravar
# ---------------------------------------------------------------------------

def preparar_lancamento(l):
    """Completa e normaliza um lançamento antes de salvar. Devolve a lista
    de erros (texto) que impedem salvar."""
    erros = []
    cod = l.categoria.codigo if l.categoria_id else None
    if l.data and not l.competencia:
        l.competencia = primeiro_dia(l.data)
    elif l.competencia:
        l.competencia = primeiro_dia(l.competencia)

    if cod == Categoria.MAO_DE_OBRA:
        if not l.prestador_id:
            erros.append("Mão de obra precisa do prestador.")
        if not l.tipo_mao_de_obra:
            l.tipo_mao_de_obra = "diarias"
        if l.tipo_mao_de_obra in TIPOS_CALCULADOS:
            if l.tipo_mao_de_obra == "diarias" and not l.valor_diaria and l.prestador_id:
                l.valor_diaria = l.prestador.valor_diaria
            l.valor = valor_mao_de_obra(l.diarias, l.valor_diaria, l.adicional, l.desconto)
        if l.desconto and l.prestador_id:
            disponivel = saldo_de_vales(l.prestador, l.obra, ignorar=l)
            if l.desconto > disponivel:
                erros.append(f"Desconto de R$ {l.desconto} maior que os vales em aberto (R$ {disponivel}).")
        if l.tipo_mao_de_obra == "diarias" and not l.diarias:
            erros.append("Informe quantas diárias.")
    elif l.empreita_id and l.quantidade and l.empreita.preco_unitario and not l.valor:
        bruto = arredondar(l.quantidade * l.empreita.preco_unitario)
        l.retencao = arredondar(bruto * l.empreita.retencao_pct / 100)
        l.valor = bruto - l.retencao - (l.desconto or ZERO)
    elif l.quantidade and l.valor_unitario and not l.valor:
        l.valor = arredondar(l.quantidade * l.valor_unitario)

    if cod == Categoria.ESTORNOS:
        if l.valor is not None:
            l.valor = -abs(l.valor)
    elif l.valor is not None and l.valor <= 0:
        erros.append("O valor precisa ser maior que zero. Devolução de dinheiro vai em “Estornos e créditos”.")

    if l.valor is None:
        erros.append("Informe o valor.")
    if cod in (Categoria.MATERIAIS, Categoria.LOCACOES, Categoria.SERVICOS, Categoria.COMBUSTIVEL,
               Categoria.DIVERSAS) and not l.fornecedor_id and not l.empreita_id:
        erros.append("Informe o fornecedor.")
    if l.a_prazo:
        l.parcelas = max(1, l.parcelas or 1)
        if not l.primeiro_vencimento and l.data:
            l.primeiro_vencimento = l.data + timedelta(days=30)
    else:
        l.parcelas = 1
        l.primeiro_vencimento = None
    if l.pk and _parcela_paga(l):
        antigo = Lancamento.objects.get(pk=l.pk)
        if antigo.valor != l.valor or antigo.parcelas != l.parcelas or antigo.forma_pagamento != l.forma_pagamento:
            erros.append("Já existe parcela paga desta compra: valor, parcelas e forma não podem mudar.")
    return erros


def _parcela_paga(l):
    return l.contas.filter(pago_em__isnull=False).exists()


def avisos_lancamento(l, hoje=None):
    """Não impedem salvar, mas a tela mostra e pede confirmação."""
    avisos = []
    if l.obra_id and l.data:
        o = l.obra
        if o.data_inicio and l.data < o.data_inicio - timedelta(days=60):
            avisos.append(f"Data {l.data:%d/%m/%Y} bem antes do início da obra ({o.data_inicio:%d/%m/%Y}).")
        if o.data_termino:
            fim = somar_meses(o.data_termino, o.meses_garantia)
            if l.data > fim:
                avisos.append(f"Data {l.data:%d/%m/%Y} depois do fim da garantia ({fim:%d/%m/%Y}).")
    hoje = hoje or date.today()
    if l.data and l.data > hoje + timedelta(days=1) and not l.a_prazo:
        avisos.append(f"Data no futuro ({l.data:%d/%m/%Y}).")
    parecidos = lancamentos_parecidos(l)
    if parecidos:
        p = parecidos[0]
        avisos.append(f"Parece repetido: já existe {p.favorecido} de R$ {p.valor} em {p.data:%d/%m/%Y}.")
    return avisos


def lancamentos_parecidos(l):
    """Mesmo favorecido, mesmo valor, até 3 dias de distância: provável duplicidade
    (caso visto na planilha: um pagamento feito duas vezes e estornado depois)."""
    if not (l.obra_id and l.data and l.valor):
        return []
    filtro = Q()
    if l.prestador_id:
        filtro = Q(prestador_id=l.prestador_id)
    elif l.fornecedor_id:
        filtro = Q(fornecedor_id=l.fornecedor_id)
    else:
        return []
    qs = (Lancamento.objects.filter(filtro, obra_id=l.obra_id, valor=l.valor,
                                    data__range=(l.data - timedelta(days=3), l.data + timedelta(days=3)))
          .exclude(categoria__codigo=Categoria.ESTORNOS))
    if l.pk:
        qs = qs.exclude(pk=l.pk)
    return list(qs[:3])


@transaction.atomic
def sincronizar_contas(l):
    """Compra a prazo gera as contas a pagar (uma por parcela). Se deixou de
    ser a prazo, as contas ainda não pagas somem."""
    if l.categoria.codigo == Categoria.ESTORNOS or not l.a_prazo:
        l.contas.filter(pago_em__isnull=True).delete()
        return
    if _parcela_paga(l):
        return
    l.contas.all().delete()
    valores = dividir(l.valor, l.parcelas)
    primeiro = l.primeiro_vencimento or (l.data + timedelta(days=30))
    for i, v in enumerate(valores):
        ContaAPagar.objects.create(
            obra=l.obra, fornecedor=l.fornecedor or (l.empreita.fornecedor if l.empreita_id else None),
            descricao=(l.descricao or (l.subcategoria.nome if l.subcategoria_id else l.categoria.nome))[:200],
            vencimento=somar_meses(primeiro, i), valor=v,
            parcela=f"{i + 1}/{len(valores)}" if len(valores) > 1 else "", lancamento=l,
        )


def status_pagamento(l):
    """'pago', 'a pagar' ou 'parcial' — compra a prazo depende das contas."""
    if not l.a_prazo:
        return "pago"
    contas = list(l.contas.all())
    if not contas:
        return "a pagar"
    pagas = sum(1 for c in contas if c.paga)
    if pagas == len(contas):
        return "pago"
    return "parcial" if pagas else "a pagar"


# ---------------------------------------------------------------------------
# Medições e imposto sobre NF
# ---------------------------------------------------------------------------

def preparar_medicao(m):
    erros = []
    obra = m.obra
    if not m.valor and m.percentual:
        m.valor = arredondar(obra.valor_total * m.percentual / 100)
    if m.valor and obra.valor_total and not m.percentual:
        m.percentual = (m.valor * 100 / obra.valor_total).quantize(CENTAVO)
    if not m.valor:
        erros.append("Informe o valor ou o percentual da medição.")
        return erros
    if m.retencao_pct is None:
        m.retencao_pct = obra.retencao_padrao
    m.valor_retencao = arredondar(m.valor * (m.retencao_pct or ZERO) / 100)
    outras = obra.medicoes.exclude(pk=m.pk).aggregate(t=Coalesce(Sum("valor"), ZERO))["t"]
    if obra.valor_total and outras + m.valor > obra.valor_total + CENTAVO:
        erros.append(
            f"As medições passariam do valor do contrato: já há R$ {outras} medidos e o contrato "
            f"(com aditivos) é R$ {obra.valor_total}. Lance um aditivo antes."
        )
    if m.data_pagamento and not m.data_emissao:
        m.data_emissao = m.data_pagamento
    if m.data_emissao and not m.vencimento:
        m.vencimento = m.data_emissao + timedelta(days=30)
    return erros


@transaction.atomic
def sincronizar_imposto(m):
    """NF emitida gera o lançamento de imposto (alíquota da obra × valor bruto).
    Sem emissão ou sem alíquota, o imposto gerado some."""
    aliquota = m.obra.aliquota_imposto or ZERO
    if not m.data_emissao or not aliquota:
        m.impostos.all().delete()
        return None
    valor = arredondar(m.valor * aliquota / 100)
    cat = Categoria.objects.get(codigo=Categoria.IMPOSTOS)
    lanc = m.impostos.first() or Lancamento(obra=m.obra, categoria=cat, medicao=m)
    lanc.data = m.data_emissao
    lanc.competencia = primeiro_dia(m.data_emissao)
    lanc.valor = valor
    lanc.forma_pagamento = "transferencia"
    lanc.descricao = f"Imposto {aliquota}% sobre a NF {m.numero_nf or ''} ({m.descricao})".replace("  ", " ")
    lanc.save()
    return lanc


# ---------------------------------------------------------------------------
# Locação mensal
# ---------------------------------------------------------------------------

def gerar_contas_de_locacao(loc, ate=None):
    """Cria a conta de cada mês da locação até `ate` (padrão: 40 dias à frente).
    A restrição única (locação, vencimento) impede conta em dobro."""
    if not loc.ativa:
        return 0
    ate = ate or (date.today() + timedelta(days=40))
    if loc.fim:
        ate = min(ate, loc.fim)
    # primeiro vencimento: o dia combinado no mês do início, ou no seguinte
    deslocamento = 0 if somar_meses(loc.inicio, 0, loc.dia_vencimento) >= loc.inicio else 1
    criadas = 0
    for n in range(120):
        vencimento = somar_meses(loc.inicio, deslocamento + n, loc.dia_vencimento)
        if vencimento > ate:
            break
        _, nova = ContaAPagar.objects.get_or_create(
            locacao=loc, vencimento=vencimento,
            defaults={"obra": loc.obra, "fornecedor": loc.fornecedor, "valor": loc.valor_mensal,
                      "descricao": f"{loc.descricao} — {vencimento:%m/%Y}"[:200]},
        )
        criadas += int(nova)
    return criadas


def gerar_todas_as_locacoes():
    from .models import LocacaoRecorrente

    return sum(gerar_contas_de_locacao(l) for l in LocacaoRecorrente.objects.filter(ativa=True))


@transaction.atomic
def pagar_conta(conta, quando=None, conta_bancaria=None, comprovante=None, usuario=None):
    """Marca a conta como paga. Conta de locação mensal vira gasto da obra
    nesse momento (a de compra a prazo já era gasto desde a compra)."""
    conta.pago_em = quando or date.today()
    if conta_bancaria:
        conta.conta_bancaria = conta_bancaria
    if comprovante:
        conta.comprovante = comprovante
    conta.save()
    if conta.locacao_id and conta.obra_id:
        loc = conta.locacao
        cat = Categoria.objects.get(codigo=Categoria.LOCACOES)
        Lancamento.objects.update_or_create(
            conta_origem=conta,
            defaults={"obra": conta.obra, "categoria": cat,
                "subcategoria": loc.subcategoria, "fornecedor": loc.fornecedor, "data": conta.pago_em,
                "competencia": primeiro_dia(conta.vencimento), "descricao": conta.descricao,
                "valor": conta.valor, "forma_pagamento": loc.forma_pagamento if loc.forma_pagamento != "boleto" else "pix",
                "conta_bancaria": conta.conta_bancaria, "responsavel": loc.responsavel,
                "periodo_inicio": conta.vencimento, "comprovante": conta.comprovante, "criado_por": usuario,
            },
        )
    return conta


@transaction.atomic
def desfazer_pagamento(conta):
    conta.pago_em = None
    conta.save(update_fields=["pago_em"])
    if conta.locacao_id:
        Lancamento.objects.filter(conta_origem=conta).delete()


# ---------------------------------------------------------------------------
# Empreita
# ---------------------------------------------------------------------------

def resumo_empreita(e):
    pagos = e.pagamentos.all()
    pago = pagos.aggregate(t=Coalesce(Sum("valor"), ZERO))["t"]
    retido = pagos.aggregate(t=Coalesce(Sum("retencao"), ZERO))["t"]
    medido = pagos.aggregate(t=Coalesce(Sum("quantidade"), ZERO))["t"]
    contratado = e.valor_contratado or arredondar(e.quantidade_prevista * e.preco_unitario)
    executado = (pago + retido)
    return {
        "contratado": contratado,
        "pago": pago,
        "retido": retido,
        "medido": medido,
        "saldo": contratado - executado,
        "pct": (executado * 100 / contratado).quantize(Decimal("0.1")) if contratado else None,
        "pct_medido": (medido * 100 / e.quantidade_prevista).quantize(Decimal("0.1")) if e.quantidade_prevista else None,
    }


def preparar_empreita(e):
    if not e.valor_contratado and e.quantidade_prevista and e.preco_unitario:
        e.valor_contratado = arredondar(e.quantidade_prevista * e.preco_unitario)
    erros = []
    if not e.fornecedor_id and not e.prestador_id:
        erros.append("Informe quem executa: fornecedor ou prestador.")
    if not e.valor_contratado:
        erros.append("Informe o valor contratado (ou quantidade × preço unitário).")
    return erros


# ---------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------

def criar_checklist(obra):
    if obra.checklist.exists():
        return 0
    itens = [ItemChecklist(obra=obra, grupo=m.grupo, ordem=m.ordem, nome=m.nome)
             for m in ModeloChecklist.objects.filter(ativo=True)]
    ItemChecklist.objects.bulk_create(itens)
    return len(itens)
