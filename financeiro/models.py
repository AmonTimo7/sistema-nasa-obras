"""Modelo de dados da obra.

Espelha as abas da planilha de controle da obra, mas sem fórmula para
quebrar: todo total é calculado pelo sistema a partir das linhas. As regras
(o que acontece quando se salva) moram em `regras.py`.
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum

ZERO = Decimal("0.00")


def caminho_arquivo(instancia, nome):
    hoje = date.today()
    return f"{instancia._meta.model_name}/{hoje:%Y/%m}/{nome}"


class ContaBancaria(models.Model):
    """De onde sai o dinheiro: 'PAGO PIX CAIXA', 'PIX NUBANK'..."""

    nome = models.CharField(max_length=60, unique=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "conta bancária"
        verbose_name_plural = "contas bancárias"

    def __str__(self):
        return self.nome


class Responsavel(models.Model):
    """Quem comprou ou pagou (a coluna COMPRADOR da planilha)."""

    nome = models.CharField(max_length=80, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "responsável"
        verbose_name_plural = "responsáveis"

    def __str__(self):
        return self.nome


class Obra(models.Model):
    PLANEJADA = "planejada"
    ANDAMENTO = "andamento"
    GARANTIA = "garantia"
    CONCLUIDA = "concluida"
    SITUACOES = [(PLANEJADA, "Planejada"), (ANDAMENTO, "Em andamento"),
                 (GARANTIA, "Em garantia"), (CONCLUIDA, "Concluída")]
    NICHOS = [("obras", "Obras"), ("manutencao", "Manutenção predial"), ("reforma", "Reforma"),
              ("instalacoes", "Instalações")]

    nome = models.CharField(max_length=160)
    cliente = models.CharField(max_length=120, blank=True)
    numero_contrato = models.CharField("nº do contrato", max_length=60, blank=True)
    escopo = models.CharField(max_length=200, blank=True)
    nicho = models.CharField(max_length=20, choices=NICHOS, default="obras")
    endereco = models.CharField("endereço", max_length=200, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    valor_contrato = models.DecimalField("valor do contrato", max_digits=14, decimal_places=2, default=ZERO)
    data_inicio = models.DateField("início", null=True, blank=True)
    data_termino = models.DateField("término previsto", null=True, blank=True)
    meses_garantia = models.PositiveSmallIntegerField("garantia (meses)", default=12)
    aliquota_imposto = models.DecimalField(
        "imposto sobre NF (%)", max_digits=5, decimal_places=2, default=ZERO,
        help_text="Ao emitir uma NF de medição, o sistema lança este imposto sozinho.",
    )
    retencao_padrao = models.DecimalField(
        "retenção na NF (%)", max_digits=5, decimal_places=2, default=ZERO,
        help_text="Retenção que o cliente desconta de cada medição.",
    )
    situacao = models.CharField(max_length=12, choices=SITUACOES, default=ANDAMENTO)

    class Meta:
        ordering = ["situacao", "nome"]
        verbose_name = "obra"

    def __str__(self):
        return self.nome

    @property
    def ativa(self):
        return self.situacao in (self.PLANEJADA, self.ANDAMENTO, self.GARANTIA)

    @property
    def valor_aditivos(self):
        return self.aditivos.aggregate(t=Sum("valor"))["t"] or ZERO

    @property
    def valor_total(self):
        return self.valor_contrato + self.valor_aditivos


class Aditivo(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="aditivos")
    descricao = models.CharField("descrição", max_length=200)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    data = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["data", "id"]

    def __str__(self):
        return self.descricao


class Categoria(models.Model):
    """As categorias da planilha, fixas. Criadas pela migração inicial."""

    MAO_DE_OBRA = 1
    SERVICOS = 2
    MATERIAIS = 3
    LOCACOES = 4
    REFEICOES_SOCIOS = 5
    REFEICOES_OBRA = 6
    COMBUSTIVEL = 7
    DIVERSAS = 8
    IMPOSTOS = 9
    GARANTIA = 10
    ESTORNOS = 11

    codigo = models.PositiveSmallIntegerField(unique=True)
    nome = models.CharField(max_length=60)
    descricao = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return self.nome


class Subcategoria(models.Model):
    """O bloco dentro da categoria: CONCRETO, AREIA, CONTÊINER, GERADOR..."""

    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="subcategorias")
    nome = models.CharField(max_length=80)
    unidade = models.CharField(max_length=10, blank=True, help_text="Unidade sugerida: m³, t, sc, diária...")
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["categoria__codigo", "nome"]
        unique_together = [("categoria", "nome")]

    def __str__(self):
        return self.nome


FORMAS_PAGAMENTO = [
    ("pix", "PIX"),
    ("boleto", "Boleto"),
    ("debito", "Cartão de débito"),
    ("credito", "Cartão de crédito"),
    ("dinheiro", "Dinheiro"),
    ("saque", "Saque"),
    ("transferencia", "Transferência"),
    ("faturado", "Faturado (conta do fornecedor)"),
]
FORMAS_A_PRAZO = ("boleto", "faturado")

UNIDADES = [("", "—"), ("un", "un"), ("m³", "m³"), ("m²", "m²"), ("m", "m"), ("t", "t"), ("kg", "kg"),
            ("sc", "saco"), ("L", "litro"), ("h", "hora"), ("diária", "diária"), ("mês", "mês"), ("vb", "verba")]

TIPOS_MAO_DE_OBRA = [
    ("diarias", "Diárias"),
    ("empreita", "Empreita / tarefa"),
    ("adiantamento", "Adiantamento / vale"),
    ("passagem", "Passagem"),
    ("gratificacao", "Gratificação"),
    ("mensal", "Pagamento mensal"),
]


class Empreita(models.Model):
    """Serviço contratado por preço: global, por m², por metro...

    Na planilha era uma aba por empreiteiro: valor contratado, metragem medida a cada
    pagamento, retenção. O saldo sai das medições lançadas.
    """

    UNIDADES = [("global", "Preço global"), ("m²", "por m²"), ("m", "por metro"), ("m³", "por m³"),
                ("un", "por unidade"), ("diária", "por diária")]

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="empreitas")
    descricao = models.CharField("serviço", max_length=200)
    fornecedor = models.ForeignKey("compras.Fornecedor", null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="empreitas")
    prestador = models.ForeignKey("juridico.Prestador", null=True, blank=True, on_delete=models.PROTECT,
                                  related_name="empreitas")
    unidade = models.CharField(max_length=10, choices=UNIDADES, default="global")
    quantidade_prevista = models.DecimalField("quantidade contratada", max_digits=12, decimal_places=2, default=ZERO)
    preco_unitario = models.DecimalField("preço unitário", max_digits=12, decimal_places=2, default=ZERO)
    valor_contratado = models.DecimalField("valor contratado", max_digits=14, decimal_places=2, default=ZERO)
    retencao_pct = models.DecimalField("retenção (%)", max_digits=5, decimal_places=2, default=ZERO)
    data_inicio = models.DateField("início", null=True, blank=True)
    encerrada = models.BooleanField(default=False)
    contrato = models.FileField(upload_to=caminho_arquivo, blank=True)

    class Meta:
        ordering = ["encerrada", "-data_inicio", "id"]
        verbose_name = "empreita"

    def __str__(self):
        return self.descricao

    @property
    def contratado_por(self):
        return self.prestador or self.fornecedor


class Lancamento(models.Model):
    """Uma saída (ou um estorno) de dinheiro da obra. A linha da planilha."""

    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name="lancamentos")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="lancamentos")
    subcategoria = models.ForeignKey(Subcategoria, null=True, blank=True, on_delete=models.PROTECT,
                                     related_name="lancamentos")
    data = models.DateField()
    competencia = models.DateField("mês", db_index=True, help_text="Primeiro dia do mês do gasto.")
    descricao = models.CharField("descrição", max_length=300, blank=True)

    prestador = models.ForeignKey("juridico.Prestador", null=True, blank=True, on_delete=models.PROTECT,
                                  related_name="lancamentos")
    fornecedor = models.ForeignKey("compras.Fornecedor", null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="lancamentos")
    empreita = models.ForeignKey(Empreita, null=True, blank=True, on_delete=models.PROTECT, related_name="pagamentos")

    # mão de obra
    tipo_mao_de_obra = models.CharField("tipo", max_length=14, choices=TIPOS_MAO_DE_OBRA, blank=True)
    diarias = models.DecimalField("diárias", max_digits=6, decimal_places=1, default=ZERO)
    valor_diaria = models.DecimalField("valor da diária", max_digits=10, decimal_places=2, default=ZERO)
    adicional = models.DecimalField("empreita / tarefa", max_digits=12, decimal_places=2, default=ZERO)
    desconto = models.DecimalField("desconto de vales", max_digits=12, decimal_places=2, default=ZERO,
                                   help_text="Vale, passagem ou marmita adiantados antes e descontados aqui.")

    # compra / locação
    numero_nf = models.CharField("nº NF", max_length=60, blank=True)
    quantidade = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unidade = models.CharField(max_length=10, choices=UNIDADES, blank=True)
    valor_unitario = models.DecimalField("valor unitário", max_digits=12, decimal_places=2, null=True, blank=True)
    periodo_inicio = models.DateField("locação de", null=True, blank=True)
    periodo_fim = models.DateField("até", null=True, blank=True)
    contrato_numero = models.CharField("nº do contrato", max_length=60, blank=True)
    retencao = models.DecimalField("retenção", max_digits=12, decimal_places=2, default=ZERO)

    valor = models.DecimalField(max_digits=14, decimal_places=2,
                                help_text="Valor pago. Na mão de obra é calculado; no estorno fica negativo.")
    forma_pagamento = models.CharField("forma de pagamento", max_length=14, choices=FORMAS_PAGAMENTO, default="pix")
    conta_bancaria = models.ForeignKey(ContaBancaria, null=True, blank=True, on_delete=models.PROTECT)
    parcelas = models.PositiveSmallIntegerField(default=1)
    primeiro_vencimento = models.DateField("1º vencimento", null=True, blank=True)
    responsavel = models.ForeignKey(Responsavel, null=True, blank=True, on_delete=models.PROTECT,
                                    verbose_name="comprador / responsável")
    nf_emitida = models.BooleanField("prestador emitiu NF", default=False)

    comprovante = models.FileField(upload_to=caminho_arquivo, blank=True)
    arquivo_nf = models.FileField("arquivo da NF", upload_to=caminho_arquivo, blank=True)
    observacao = models.TextField("observação", blank=True)

    medicao = models.ForeignKey("Medicao", null=True, blank=True, on_delete=models.CASCADE,
                                related_name="impostos", help_text="Imposto gerado por esta NF de medição.")
    estorno_de = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="estornos")
    conta_origem = models.OneToOneField("ContaAPagar", null=True, blank=True, on_delete=models.CASCADE,
                                        related_name="gasto", help_text="Conta de locação mensal que, paga, virou este gasto.")

    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data", "-id"]
        verbose_name = "lançamento"
        indexes = [models.Index(fields=["obra", "competencia", "categoria"])]

    def __str__(self):
        return f"{self.data:%d/%m/%Y} · {self.favorecido} · R$ {self.valor}"

    @property
    def favorecido(self):
        alvo = self.prestador or self.fornecedor
        return str(alvo) if alvo else (self.descricao or self.categoria.nome)

    @property
    def a_prazo(self):
        return self.forma_pagamento in FORMAS_A_PRAZO

    @property
    def pendencias(self):
        """O que falta neste lançamento (a lista 'a conferir')."""
        faltas = []
        if self.valor > 0 and not self.comprovante and not self.a_prazo:
            faltas.append("sem comprovante")
        if self.categoria.codigo == Categoria.MATERIAIS and not self.numero_nf and not self.arquivo_nf:
            faltas.append("sem NF")
        if self.categoria.codigo == Categoria.SERVICOS and not self.arquivo_nf and not self.nf_emitida:
            faltas.append("sem NF do serviço")
        return faltas


class Medicao(models.Model):
    """Aba NF DE ENTRADA: o que se fatura ao cliente."""

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="medicoes")
    descricao = models.CharField("descrição", max_length=120, help_text="Ex.: Entrada, Medição 01.")
    percentual = models.DecimalField("% do contrato", max_digits=5, decimal_places=2, null=True, blank=True)
    valor = models.DecimalField("valor bruto", max_digits=14, decimal_places=2,
                                help_text="Em branco com % preenchido: o sistema calcula.")
    retencao_pct = models.DecimalField("retenção (%)", max_digits=5, decimal_places=2, default=ZERO)
    valor_retencao = models.DecimalField("valor retido", max_digits=14, decimal_places=2, default=ZERO)
    numero_nf = models.CharField("nº NF", max_length=40, blank=True)
    data_emissao = models.DateField("emissão da NF", null=True, blank=True)
    vencimento = models.DateField(null=True, blank=True)
    data_pagamento = models.DateField("pago em", null=True, blank=True)
    arquivo_nf = models.FileField("arquivo da NF", upload_to=caminho_arquivo, blank=True)

    class Meta:
        ordering = ["data_emissao", "id"]
        verbose_name = "medição"
        verbose_name_plural = "medições"

    def __str__(self):
        return self.descricao

    @property
    def valor_liquido(self):
        return self.valor - (self.valor_retencao or ZERO)

    def situacao(self, hoje=None):
        hoje = hoje or date.today()
        if self.data_pagamento:
            return "paga"
        if not self.data_emissao:
            return "prevista"
        if self.vencimento and self.vencimento < hoje:
            return "atrasada"
        return "aguardando"


class LocacaoRecorrente(models.Model):
    """Aluguel mensal (contêiner, kit, gerador). Gera a conta de cada mês."""

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="locacoes")
    fornecedor = models.ForeignKey("compras.Fornecedor", on_delete=models.PROTECT, related_name="locacoes")
    subcategoria = models.ForeignKey(Subcategoria, null=True, blank=True, on_delete=models.PROTECT)
    descricao = models.CharField("o que é", max_length=200)
    contrato_numero = models.CharField("nº do contrato", max_length=60, blank=True)
    inicio = models.DateField("início")
    fim = models.DateField("fim previsto", null=True, blank=True)
    dia_vencimento = models.PositiveSmallIntegerField("dia do vencimento")
    valor_mensal = models.DecimalField("valor mensal", max_digits=12, decimal_places=2)
    forma_pagamento = models.CharField(max_length=14, choices=FORMAS_PAGAMENTO, default="boleto")
    responsavel = models.ForeignKey(Responsavel, null=True, blank=True, on_delete=models.PROTECT)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["-ativa", "dia_vencimento", "id"]
        verbose_name = "locação mensal"
        verbose_name_plural = "locações mensais"

    def __str__(self):
        return f"{self.descricao} · {self.fornecedor}"


class ContaAPagar(models.Model):
    """Aba CONTROLE - BOLETOS. Vem de compra a prazo, de locação mensal ou avulsa."""

    obra = models.ForeignKey(Obra, null=True, blank=True, on_delete=models.CASCADE, related_name="contas")
    fornecedor = models.ForeignKey("compras.Fornecedor", on_delete=models.PROTECT, related_name="contas")
    descricao = models.CharField("produto / serviço", max_length=200)
    vencimento = models.DateField(db_index=True)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    parcela = models.CharField(max_length=10, blank=True, help_text="Ex.: 1/2")
    lancamento = models.ForeignKey(Lancamento, null=True, blank=True, on_delete=models.CASCADE,
                                   related_name="contas", help_text="A compra que gerou esta conta.")
    locacao = models.ForeignKey(LocacaoRecorrente, null=True, blank=True, on_delete=models.CASCADE,
                                related_name="contas")
    pago_em = models.DateField(null=True, blank=True)
    conta_bancaria = models.ForeignKey(ContaBancaria, null=True, blank=True, on_delete=models.PROTECT)
    boleto = models.FileField(upload_to=caminho_arquivo, blank=True)
    comprovante = models.FileField(upload_to=caminho_arquivo, blank=True)

    class Meta:
        ordering = ["vencimento", "id"]
        verbose_name = "conta a pagar"
        verbose_name_plural = "contas a pagar"
        constraints = [models.UniqueConstraint(fields=["locacao", "vencimento"], name="uma_conta_por_mes_de_locacao")]

    def __str__(self):
        return f"{self.fornecedor} · {self.descricao} · R$ {self.valor}"

    @property
    def paga(self):
        return self.pago_em is not None

    def situacao(self, hoje=None):
        if self.paga:
            return "paga"
        hoje = hoje or date.today()
        if self.vencimento < hoje:
            return "vencida"
        if self.vencimento == hoje:
            return "hoje"
        if (self.vencimento - hoje).days <= 7:
            return "semana"
        return "aberta"


class ModeloChecklist(models.Model):
    """O 'setlist' padrão. Toda obra nova nasce com estes itens."""

    grupo = models.CharField(max_length=60)
    ordem = models.PositiveSmallIntegerField(default=0)
    nome = models.CharField(max_length=160)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["grupo", "ordem"]
        verbose_name = "item do checklist padrão"
        verbose_name_plural = "checklist padrão"

    def __str__(self):
        return f"{self.grupo}: {self.nome}"


class ItemChecklist(models.Model):
    PENDENTE = "pendente"
    ANDAMENTO = "andamento"
    FEITO = "feito"
    NAO_APLICA = "nao_aplica"
    SITUACOES = [(PENDENTE, "Pendente"), (ANDAMENTO, "Em andamento"), (FEITO, "Feito"),
                 (NAO_APLICA, "Não se aplica")]

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="checklist")
    grupo = models.CharField(max_length=60)
    ordem = models.PositiveSmallIntegerField(default=0)
    nome = models.CharField(max_length=160)
    situacao = models.CharField(max_length=12, choices=SITUACOES, default=PENDENTE)
    link = models.CharField(max_length=300, blank=True)
    arquivo = models.FileField(upload_to=caminho_arquivo, blank=True)
    prazo = models.DateField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["grupo", "ordem", "id"]
        verbose_name = "item do checklist"
        verbose_name_plural = "checklist da obra"

    def __str__(self):
        return f"{self.grupo}: {self.nome}"
