from decimal import Decimal

from django import forms

from compras.models import Fornecedor
from core.texto import chave, dinheiro, limpar
from juridico.models import Prestador

from . import regras
from .models import (
    Aditivo,
    Categoria,
    ContaAPagar,
    ContaBancaria,
    Empreita,
    ItemChecklist,
    Lancamento,
    LocacaoRecorrente,
    Medicao,
    Obra,
    Responsavel,
    Subcategoria,
)

DATA = forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})


class CampoDinheiro(forms.CharField):
    """Aceita '1.234,56', '1234,56' e '1234.56'. Recusa o que não der certeza."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", forms.TextInput(attrs={"inputmode": "decimal", "placeholder": "0,00"}))
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, Decimal):
            return f"{value:.2f}".replace(".", ",")
        return value

    def to_python(self, value):
        value = super().to_python(value)
        if value in ("", None):
            return None
        numero = dinheiro(value)
        if numero is None:
            raise forms.ValidationError("Valor não entendido. Use, por exemplo, 1.234,56.")
        return numero


class CampoNumero(forms.DecimalField):
    """Quantidade e diárias do jeito brasileiro: '22,5', '1.500,75', '4.5'."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", forms.TextInput(attrs={"inputmode": "decimal"}))
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, Decimal):
            texto = format(value.normalize(), "f")
            return texto.replace(".", ",")
        return value

    def to_python(self, value):
        if isinstance(value, str):
            v = value.strip()
            if "," in v:
                v = v.replace(".", "").replace(",", ".")
            value = v
        return super().to_python(value)


class FormBase(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in list(self.fields.items()):
            if isinstance(campo, forms.DecimalField) and not isinstance(campo, CampoNumero):
                self.fields[nome] = CampoNumero(
                    label=campo.label, required=campo.required, help_text=campo.help_text,
                    max_digits=campo.max_digits, decimal_places=campo.decimal_places, initial=campo.initial)
        for campo in self.fields.values():
            if isinstance(campo, forms.ModelChoiceField):
                campo.empty_label = "Selecione…"
            elif isinstance(campo, forms.TypedChoiceField) and campo.choices and campo.choices[0][0] == "":
                campo.choices = [("", "Selecione…")] + list(campo.choices)[1:]
            w = campo.widget
            if isinstance(w, forms.CheckboxInput):
                continue
            if isinstance(w, forms.DateInput):
                w.format = "%Y-%m-%d"
                w.input_type = "date"
            w.attrs.setdefault("class", "campo")


def _fornecedor_por_nome(nome):
    nome = limpar(nome)
    if not nome:
        return None
    return Fornecedor.objects.filter(chave=__import__("core.texto", fromlist=["chave"]).chave(nome)).first() \
        or Fornecedor.objects.create(nome=nome)


def _devolver(form, dados, inst):
    """O ModelForm copia o cleaned_data na instância DEPOIS do clean(); sem
    isto, o valor que as regras calcularam seria trocado pelo campo vazio."""
    for nome in form.fields:
        if nome in ("fornecedor_nome", "confirmar") or isinstance(form.fields[nome], forms.FileField):
            continue
        if hasattr(inst, nome):
            dados[nome] = getattr(inst, nome)


# Campos que cada categoria mostra, além dos comuns.
CAMPOS_POR_CATEGORIA = {
    Categoria.MAO_DE_OBRA: ["prestador", "tipo_mao_de_obra", "diarias", "valor_diaria", "adicional", "desconto",
                            "nf_emitida"],
    Categoria.SERVICOS: ["subcategoria", "fornecedor_nome", "empreita", "quantidade", "unidade", "numero_nf",
                         "nf_emitida", "retencao"],
    Categoria.MATERIAIS: ["subcategoria", "fornecedor_nome", "numero_nf", "quantidade", "unidade", "valor_unitario"],
    Categoria.LOCACOES: ["subcategoria", "fornecedor_nome", "periodo_inicio", "periodo_fim", "contrato_numero",
                         "quantidade", "unidade", "valor_unitario", "numero_nf"],
    Categoria.REFEICOES_SOCIOS: ["fornecedor_nome", "numero_nf"],
    Categoria.REFEICOES_OBRA: ["subcategoria", "fornecedor_nome", "quantidade", "unidade", "numero_nf"],
    Categoria.COMBUSTIVEL: ["subcategoria", "fornecedor_nome", "quantidade", "unidade", "numero_nf"],
    Categoria.DIVERSAS: ["subcategoria", "fornecedor_nome", "numero_nf"],
    Categoria.IMPOSTOS: ["numero_nf"],
    Categoria.GARANTIA: ["prestador", "fornecedor_nome", "numero_nf"],
    Categoria.ESTORNOS: ["estorno_de", "prestador", "fornecedor_nome"],
}
COMUNS = ["data", "descricao", "valor", "forma_pagamento", "conta_bancaria", "parcelas", "primeiro_vencimento",
          "responsavel", "comprovante", "arquivo_nf", "observacao"]
DINHEIRO = ["valor", "valor_diaria", "adicional", "desconto", "valor_unitario", "retencao"]


class LancamentoForm(FormBase):
    fornecedor_nome = forms.CharField(label="Fornecedor", required=False,
                                      widget=forms.TextInput(attrs={"list": "lista-fornecedores", "autocomplete": "off"}),
                                      help_text="Digite: se não existir, é cadastrado.")
    confirmar = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Lancamento
        fields = sorted({c for cs in CAMPOS_POR_CATEGORIA.values() for c in cs if c != "fornecedor_nome"} | set(COMUNS))
        widgets = {
            "data": DATA, "primeiro_vencimento": DATA, "periodo_inicio": DATA, "periodo_fim": DATA,
            "observacao": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {"descricao": "Descrição / finalidade", "conta_bancaria": "Pago pela conta"}

    def __init__(self, *args, categoria=None, obra=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.categoria = categoria
        self.obra = obra
        for nome in DINHEIRO:
            if nome in self.fields:
                antigo = self.fields[nome]
                self.fields[nome] = CampoDinheiro(label=antigo.label, required=False, help_text=antigo.help_text)
        for nome, casas in (("quantidade", 2), ("diarias", 1)):
            if nome in self.fields:
                antigo = self.fields[nome]
                self.fields[nome] = CampoNumero(label=antigo.label, required=False, decimal_places=casas,
                                                max_digits=12, help_text=antigo.help_text)
        visiveis = set(COMUNS) | set(CAMPOS_POR_CATEGORIA.get(categoria.codigo, [])) | {"confirmar"}
        for nome in list(self.fields):
            if nome not in visiveis:
                del self.fields[nome]
        if "subcategoria" in self.fields:
            self.fields["subcategoria"].queryset = Subcategoria.objects.filter(categoria=categoria, ativa=True)
            self.fields["subcategoria"].label = "Tipo"
        if "prestador" in self.fields:
            self.fields["prestador"].queryset = Prestador.objects.filter(ativo=True)
        if "empreita" in self.fields:
            self.fields["empreita"].queryset = Empreita.objects.filter(obra=obra, encerrada=False)
            self.fields["empreita"].help_text = "Pagamento de uma empreita contratada: informe a metragem medida."
        if "estorno_de" in self.fields:
            self.fields["estorno_de"].queryset = (Lancamento.objects.filter(obra=obra).exclude(categoria=categoria)
                                                  .select_related("prestador", "fornecedor")[:300])
            self.fields["estorno_de"].label = "Estorno de qual pagamento"
        self.fields["conta_bancaria"].queryset = ContaBancaria.objects.filter(ativa=True)
        self.fields["responsavel"].queryset = Responsavel.objects.filter(ativo=True)
        self.fields["valor"].required = False
        if "tipo_mao_de_obra" in self.fields:
            from .models import TIPOS_MAO_DE_OBRA
            self.fields["tipo_mao_de_obra"].choices = TIPOS_MAO_DE_OBRA
            self.fields["tipo_mao_de_obra"].required = True
            if not self.instance.pk:
                self.initial.setdefault("tipo_mao_de_obra", "diarias")
            self.fields["prestador"].required = True
        if categoria.codigo == Categoria.MAO_DE_OBRA:
            self.fields["valor"].help_text = "Diárias e empreita: calculado sozinho. Vale: digite o valor."
        if self.instance.pk and self.instance.fornecedor_id and "fornecedor_nome" in self.fields:
            self.fields["fornecedor_nome"].initial = self.instance.fornecedor.nome
        self.fields["parcelas"].help_text = "Boleto ou faturado: vira conta a pagar em parcelas."
        self.fields["primeiro_vencimento"].help_text = "Em branco: 30 dias depois da compra."

    def ordem(self):
        """Campos na ordem da tela: o específico da categoria primeiro."""
        especificos = [n for n in CAMPOS_POR_CATEGORIA.get(self.categoria.codigo, []) if n in self.fields]
        return especificos, [n for n in COMUNS if n in self.fields]

    def clean(self):
        dados = super().clean()
        if self.errors:
            return dados
        inst = self.instance
        inst.obra = self.obra
        inst.categoria = self.categoria
        for campo in DINHEIRO:
            if campo in self.fields:
                v = dados.get(campo)
                setattr(inst, campo, v if v is not None else (None if campo in ("valor", "valor_unitario") else Decimal("0")))
        for campo, valor in dados.items():
            if campo in DINHEIRO or campo in ("fornecedor_nome", "confirmar", "comprovante", "arquivo_nf"):
                continue
            if hasattr(inst, campo):
                setattr(inst, campo, valor)
        if "fornecedor_nome" in self.fields:
            nome = limpar(dados.get("fornecedor_nome"))
            inst.fornecedor = _fornecedor_por_nome(nome) if nome else None
        if inst.empreita_id and not inst.fornecedor_id and inst.empreita.fornecedor_id:
            inst.fornecedor = inst.empreita.fornecedor
        if inst.empreita_id and inst.empreita.prestador_id and not inst.prestador_id:
            inst.prestador = inst.empreita.prestador
        if inst.estorno_de_id and not inst.valor:
            inst.valor = inst.estorno_de.valor
        inst.competencia = None
        for erro in regras.preparar_lancamento(inst):
            self.add_error(None, erro)
        self.avisos = [] if self.errors else regras.avisos_lancamento(inst)
        _devolver(self, dados, inst)
        return dados


class EscolhaCategoriaForm(forms.Form):
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.all())


class MedicaoForm(FormBase):
    valor = CampoDinheiro(label="Valor bruto (R$)", required=False,
                          help_text="Em branco com % preenchido: o sistema calcula.")

    class Meta:
        model = Medicao
        fields = ["descricao", "percentual", "valor", "retencao_pct", "numero_nf", "data_emissao", "vencimento",
                  "data_pagamento", "arquivo_nf"]
        widgets = {"data_emissao": DATA, "vencimento": DATA, "data_pagamento": DATA}

    def __init__(self, *args, obra=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.obra = obra
        if not self.instance.pk and obra:
            self.fields["retencao_pct"].initial = obra.retencao_padrao

    def clean(self):
        dados = super().clean()
        if self.errors:
            return dados
        m = self.instance
        m.obra = self.obra
        for k, v in dados.items():
            if k != "arquivo_nf":
                setattr(m, k, v)
        for erro in regras.preparar_medicao(m):
            self.add_error(None, erro)
        _devolver(self, dados, m)
        return dados


class AditivoForm(FormBase):
    valor = CampoDinheiro(label="Valor (R$)")

    class Meta:
        model = Aditivo
        fields = ["descricao", "valor", "data"]
        widgets = {"data": DATA}


class ObraForm(FormBase):
    valor_contrato = CampoDinheiro(label="Valor do contrato (R$)")

    class Meta:
        model = Obra
        fields = ["nome", "cliente", "numero_contrato", "escopo", "nicho", "situacao", "endereco", "cidade",
                  "valor_contrato", "data_inicio", "data_termino", "meses_garantia", "aliquota_imposto",
                  "retencao_padrao"]
        widgets = {"data_inicio": DATA, "data_termino": DATA}

    def clean(self):
        dados = super().clean()
        ini, fim = dados.get("data_inicio"), dados.get("data_termino")
        if ini and fim and fim <= ini:
            self.add_error("data_termino", "O término precisa ser depois do início.")
        return dados


class EmpreitaForm(FormBase):
    fornecedor_nome = forms.CharField(label="Empresa contratada", required=False,
                                      widget=forms.TextInput(attrs={"list": "lista-fornecedores", "autocomplete": "off"}))
    preco_unitario = CampoDinheiro(label="Preço unitário (R$)", required=False)
    valor_contratado = CampoDinheiro(label="Valor contratado (R$)", required=False,
                                     help_text="Em branco: quantidade × preço unitário.")

    class Meta:
        model = Empreita
        fields = ["descricao", "prestador", "fornecedor_nome", "unidade", "quantidade_prevista", "preco_unitario",
                  "valor_contratado", "retencao_pct", "data_inicio", "encerrada", "contrato"]
        widgets = {"data_inicio": DATA}

    def __init__(self, *args, obra=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.obra = obra
        self.fields["prestador"].required = False
        self.fields["prestador"].help_text = "Ou um autônomo, em vez de empresa."
        if self.instance.pk and self.instance.fornecedor_id:
            self.fields["fornecedor_nome"].initial = self.instance.fornecedor.nome

    def clean(self):
        dados = super().clean()
        if self.errors:
            return dados
        e = self.instance
        e.obra = self.obra
        for k in ("descricao", "prestador", "unidade", "quantidade_prevista", "retencao_pct", "data_inicio", "encerrada"):
            setattr(e, k, dados.get(k))
        e.preco_unitario = dados.get("preco_unitario") or Decimal("0")
        e.valor_contratado = dados.get("valor_contratado") or Decimal("0")
        nome = dados.get("fornecedor_nome")
        e.fornecedor = _fornecedor_por_nome(nome) if nome else None
        for erro in regras.preparar_empreita(e):
            self.add_error(None, erro)
        _devolver(self, dados, e)
        return dados


class ContaForm(FormBase):
    fornecedor_nome = forms.CharField(label="Fornecedor",
                                      widget=forms.TextInput(attrs={"list": "lista-fornecedores", "autocomplete": "off"}))
    valor = CampoDinheiro(label="Valor (R$)")

    class Meta:
        model = ContaAPagar
        fields = ["obra", "fornecedor_nome", "descricao", "vencimento", "valor", "boleto"]
        widgets = {"vencimento": DATA}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["obra"].required = False
        self.fields["obra"].help_text = "Em branco: conta da empresa, fora de obra."
        if self.instance.pk:
            self.fields["fornecedor_nome"].initial = self.instance.fornecedor.nome

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.fornecedor = _fornecedor_por_nome(self.cleaned_data["fornecedor_nome"])
        if commit:
            obj.save()
        return obj


class PagarContaForm(forms.Form):
    pago_em = forms.DateField(label="Pago em", widget=DATA)
    conta_bancaria = forms.ModelChoiceField(label="Pela conta", queryset=ContaBancaria.objects.filter(ativa=True), empty_label="Selecione…",
                                            required=False)
    comprovante = forms.FileField(required=False)


class LocacaoForm(FormBase):
    fornecedor_nome = forms.CharField(label="Fornecedor",
                                      widget=forms.TextInput(attrs={"list": "lista-fornecedores", "autocomplete": "off"}))
    valor_mensal = CampoDinheiro(label="Valor mensal (R$)")

    class Meta:
        model = LocacaoRecorrente
        fields = ["descricao", "subcategoria", "fornecedor_nome", "contrato_numero", "inicio", "fim",
                  "dia_vencimento", "valor_mensal", "forma_pagamento", "responsavel", "ativa"]
        widgets = {"inicio": DATA, "fim": DATA}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subcategoria"].queryset = Subcategoria.objects.filter(categoria__codigo=Categoria.LOCACOES)
        self.fields["subcategoria"].label = "Tipo"
        if self.instance.pk:
            self.fields["fornecedor_nome"].initial = self.instance.fornecedor.nome

    def clean_dia_vencimento(self):
        dia = self.cleaned_data["dia_vencimento"]
        if not 1 <= dia <= 31:
            raise forms.ValidationError("Dia entre 1 e 31.")
        return dia

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.fornecedor = _fornecedor_por_nome(self.cleaned_data["fornecedor_nome"])
        if commit:
            obj.save()
        return obj


class ItemChecklistForm(FormBase):
    class Meta:
        model = ItemChecklist
        fields = ["situacao", "prazo", "link", "arquivo"]
        widgets = {"prazo": DATA}
