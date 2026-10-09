from django import forms

from financeiro.forms import CampoDinheiro, FormBase

from .models import Prestador


class PrestadorForm(FormBase):
    valor_diaria = CampoDinheiro(label="Valor da diária (R$)", required=False)

    class Meta:
        model = Prestador
        fields = ["nome", "funcao", "valor_diaria", "telefone", "documento", "endereco", "cidade", "chave_pix",
                  "titular_conta", "link_pasta", "ativo", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 2})}

    def clean_valor_diaria(self):
        return self.cleaned_data.get("valor_diaria") or 0
