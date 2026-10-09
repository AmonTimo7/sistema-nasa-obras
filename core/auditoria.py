"""Log de quem criou, alterou ou excluiu.

Cada modelo que precisa de rastro chama `registrar(Modelo)` no `ready()` do
app. A importação da planilha grava em lote (sem sinais) e deixa UM registro
próprio dizendo o que fez, em vez de mil linhas iguais.
"""
from datetime import date, datetime
from decimal import Decimal

from django.db.models.signals import post_delete, post_save, pre_save

from .middleware import usuario_atual
from .models import RegistroAuditoria


def _serializavel(valor):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if hasattr(valor, "name") and hasattr(valor, "storage"):  # anexo: guarda só o nome
        return valor.name or ""
    if valor is not None and not isinstance(valor, (str, int, float, bool)):
        return str(valor)
    return valor


def _foto(instancia):
    dados = {}
    for campo in instancia._meta.concrete_fields:
        dados[campo.attname] = _serializavel(getattr(instancia, campo.attname))
    return dados


def anotar(acao, modelo, descricao, objeto_id="", mudancas=None, usuario=None):
    RegistroAuditoria.objects.create(
        usuario=usuario or usuario_atual(),
        acao=acao,
        modelo=modelo,
        objeto_id=str(objeto_id),
        descricao=descricao[:300],
        mudancas=mudancas or {},
    )


def _antes(sender, instance, **kwargs):
    if instance.pk:
        anterior = sender.objects.filter(pk=instance.pk).first()
        instance._auditoria_antes = _foto(anterior) if anterior else None
    else:
        instance._auditoria_antes = None


def _depois(sender, instance, created, **kwargs):
    nome = sender._meta.verbose_name
    if created:
        anotar(RegistroAuditoria.CRIOU, nome, str(instance), instance.pk)
        return
    antes = getattr(instance, "_auditoria_antes", None) or {}
    agora = _foto(instance)
    mudancas = {k: [antes.get(k), v] for k, v in agora.items() if antes.get(k) != v}
    if mudancas:
        anotar(RegistroAuditoria.ALTEROU, nome, str(instance), instance.pk, mudancas)


def _apagou(sender, instance, **kwargs):
    anotar(RegistroAuditoria.EXCLUIU, sender._meta.verbose_name, str(instance), instance.pk, _foto(instance))


def registrar(modelo):
    uid = f"auditoria-{modelo._meta.label}"
    pre_save.connect(_antes, sender=modelo, dispatch_uid=uid + "-pre")
    post_save.connect(_depois, sender=modelo, dispatch_uid=uid + "-post")
    post_delete.connect(_apagou, sender=modelo, dispatch_uid=uid + "-del")
