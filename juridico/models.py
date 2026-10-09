from decimal import Decimal

from django.db import models

from core.texto import chave, limpar


class Prestador(models.Model):
    """Pessoa que presta serviço autônomo na obra (pedreiro, ajudante...).

    Tem dado pessoal (chave PIX, documento, endereço): LGPD. Só sócios e
    jurídico veem o cadastro inteiro.
    """

    nome = models.CharField(max_length=160)
    chave = models.CharField(max_length=160, unique=True, editable=False)
    funcao = models.CharField("função", max_length=80, blank=True)
    valor_diaria = models.DecimalField(
        "valor da diária", max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Sugerido ao lançar diárias. Pode mudar em cada pagamento.",
    )
    telefone = models.CharField(max_length=40, blank=True)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    documento = models.CharField("RG / CPF / CNPJ", max_length=40, blank=True)
    chave_pix = models.CharField("chave PIX", max_length=120, blank=True)
    titular_conta = models.CharField("titular da conta", max_length=160, blank=True,
                                     help_text="Se o PIX for de outra pessoa ou empresa.")
    link_pasta = models.CharField("link da pasta", max_length=300, blank=True)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "prestador"
        verbose_name_plural = "prestadores"

    def __str__(self):
        return self.nome

    def clean(self):
        from django.core.exceptions import ValidationError

        k = chave(self.nome)
        if Prestador.objects.exclude(pk=self.pk).filter(chave=k).exists():
            raise ValidationError({"nome": "Já existe um prestador com esse nome."})

    def save(self, *args, **kwargs):
        self.nome = limpar(self.nome)
        self.chave = chave(self.nome)
        super().save(*args, **kwargs)
