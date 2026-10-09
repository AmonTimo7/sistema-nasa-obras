from decimal import Decimal

from django import template

from core.texto import brl as _brl

register = template.Library()

MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
         "Setembro", "Outubro", "Novembro", "Dezembro"]


@register.filter
def brl(valor):
    return _brl(valor) if valor is not None and valor != "" else "—"


@register.filter
def brl_curto(valor):
    """11700000 -> 'R$ 11,7 mi'; 48075 -> 'R$ 48,1 mil'. Para cartão grande."""
    if valor is None:
        return "—"
    v = Decimal(valor)
    sinal = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000:
        texto = f"{a / 1_000_000:.2f}".rstrip("0").rstrip(".") + " mi"
    elif a >= 100_000:
        texto = f"{a / 1_000:.0f} mil"
    elif a >= 10_000:
        texto = f"{a / 1_000:.1f}".rstrip("0").rstrip(".") + " mil"
    else:
        return _brl(v)
    return f"{sinal}R$ {texto.replace('.', ',')}"


@register.filter
def mes(d):
    return f"{MESES[d.month]}/{d.year}" if d else "—"


@register.filter
def mes_curto(d):
    return f"{MESES[d.month][:3].lower()}/{d.year % 100:02d}" if d else "—"


@register.filter
def pct(valor):
    if valor is None:
        return "—"
    return f"{valor}".replace(".", ",") + "%"


@register.filter
def largura(valor):
    """Percentual para CSS width, limitado a 0–100."""
    if valor is None:
        return 0
    return max(0, min(100, float(valor)))
