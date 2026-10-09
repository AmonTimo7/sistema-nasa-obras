from django.db import models

from core.texto import chave, limpar


class Fornecedor(models.Model):
    RECORRENTE = "recorrente"
    COTACAO = "cotacao"
    TIPOS = [(RECORRENTE, "Recorrente"), (COTACAO, "Cotação")]

    nome = models.CharField(max_length=160)
    chave = models.CharField(max_length=160, unique=True, editable=False)
    tipo = models.CharField(max_length=12, choices=TIPOS, default=COTACAO,
                            help_text="Recorrente: compra direta com preço combinado. Cotação: pede orçamento.")
    cnpj = models.CharField("CNPJ / CPF", max_length=20, blank=True)
    telefone = models.CharField("telefone / WhatsApp", max_length=40, blank=True)
    contato = models.CharField("pessoa de contato", max_length=120, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    chave_pix = models.CharField("chave PIX", max_length=120, blank=True)
    ramo = models.CharField(max_length=80, blank=True, help_text="Ex.: madeira, concreto, locação de equipamento.")
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "fornecedor"
        verbose_name_plural = "fornecedores"

    def __str__(self):
        return self.nome

    def clean(self):
        from django.core.exceptions import ValidationError

        if Fornecedor.objects.exclude(pk=self.pk).filter(chave=chave(self.nome)).exists():
            raise ValidationError({"nome": "Já existe um fornecedor com esse nome."})

    def save(self, *args, **kwargs):
        self.nome = limpar(self.nome)
        self.chave = chave(self.nome)
        super().save(*args, **kwargs)
