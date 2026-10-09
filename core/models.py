from django.conf import settings
from django.db import models


class Perfil(models.Model):
    """Papel de cada usuário. O financeiro é fechado a quem não é sócio."""

    SOCIO = "socio"
    COMPRAS = "compras"
    OPERACAO = "operacao"
    JURIDICO = "juridico"
    PAPEIS = [
        (SOCIO, "Sócios / financeiro"),
        (COMPRAS, "Compras"),
        (OPERACAO, "Operação"),
        (JURIDICO, "Jurídico"),
    ]

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    papel = models.CharField(max_length=20, choices=PAPEIS, default=OPERACAO)
    precisa_trocar_senha = models.BooleanField(
        default=True,
        help_text="Senha de fábrica: o sistema não abre nenhuma tela antes da troca.",
    )

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self):
        return f"{self.usuario.get_username()} ({self.get_papel_display()})"


class RegistroAuditoria(models.Model):
    """Quem criou, alterou ou excluiu o quê. Nunca é apagado pelo sistema."""

    CRIOU = "criou"
    ALTEROU = "alterou"
    EXCLUIU = "excluiu"
    IMPORTOU = "importou"
    ACOES = [(CRIOU, "criou"), (ALTEROU, "alterou"), (EXCLUIU, "excluiu"), (IMPORTOU, "importou")]

    quando = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    acao = models.CharField(max_length=10, choices=ACOES)
    modelo = models.CharField(max_length=60)
    objeto_id = models.CharField(max_length=40, blank=True)
    descricao = models.CharField(max_length=300)
    mudancas = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-quando"]
        verbose_name = "registro de auditoria"
        verbose_name_plural = "auditoria"

    def __str__(self):
        return f"{self.quando:%d/%m/%Y %H:%M} {self.usuario} {self.acao} {self.descricao}"
