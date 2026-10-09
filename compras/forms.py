from django import forms

from financeiro.forms import FormBase

from .models import Fornecedor


class FornecedorForm(FormBase):
    class Meta:
        model = Fornecedor
        fields = ["nome", "tipo", "ramo", "cnpj", "telefone", "contato", "cidade", "chave_pix", "ativo", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 2})}
