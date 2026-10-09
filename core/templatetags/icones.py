"""Ícones de traço fino no estilo SF Symbols, em SVG inline (sem fonte de ícone).

Uso: {% load icones %} {% icone "obra" %}. Cor = currentColor.
"""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

P = {
    "painel": '<rect x="3" y="3" width="7.5" height="9" rx="2"/><rect x="13.5" y="3" width="7.5" height="5.5" rx="2"/>'
              '<rect x="13.5" y="11.5" width="7.5" height="9.5" rx="2"/><rect x="3" y="15" width="7.5" height="6" rx="2"/>',
    "globo": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9s-1.3 6.5-3.8 9c-2.5-2.5-3.8-5.5-3.8-9S9.5 5.5 12 3z"/>',
    "lista": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1.2" fill="currentColor"/>'
             '<circle cx="4.5" cy="12" r="1.2" fill="currentColor"/><circle cx="4.5" cy="18" r="1.2" fill="currentColor"/>',
    "calendario": '<rect x="3" y="4.5" width="18" height="16.5" rx="3"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4"/>'
                  '<path d="M7.5 13.5h2M11 13.5h2M14.5 13.5h2M7.5 17h2M11 17h2"/>',
    "alerta": '<path d="M10.3 3.9 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9.5v4.5M12 17.2v.1"/>',
    "pessoas": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5"/>'
               '<circle cx="17" cy="9" r="2.6"/><path d="M16.5 14.6c2.6.2 4.4 1.9 5 4.9"/>',
    "regua": '<rect x="2.5" y="8" width="19" height="8" rx="1.5"/><path d="M6.5 8v3M10 8v4.5M13.5 8v3M17 8v4.5"/>',
    "cartao": '<rect x="2.5" y="5" width="19" height="14" rx="3"/><path d="M2.5 10h19M6 15h4"/>',
    "documento": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M8.5 13h7M8.5 17h5"/>',
    "grafico": '<path d="M4 20V10M10 20V4M16 20v-7M21 20H3"/>',
    "checklist": '<path d="m3.5 6.5 1.7 1.7L8.5 5M3.5 13.5l1.7 1.7 3.3-3.2M11.5 7h9M11.5 14h9M11.5 19.5h9"/>',
    "obra": '<path d="M3 21h18M5 21V11l7-5 7 5v10"/><path d="M9.5 21v-6h5v6"/>',
    "caixa": '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    "cracha": '<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="11" r="2.5"/><path d="M5.5 17c.6-2 1.9-3 3.5-3s2.9 1 3.5 3M14.5 10h4M14.5 13.5h3"/>',
    "pessoa": '<circle cx="12" cy="8" r="4"/><path d="M4.5 21c.8-4 3.7-6.5 7.5-6.5s6.7 2.5 7.5 6.5"/>',
    "mais": '<path d="M12 5v14M5 12h14"/>',
    "baixar": '<path d="M12 4v11M7 10.5l5 5 5-5M4.5 20h15"/>',
    "lapis": '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
    "lixeira": '<path d="M4 7h16M10 11v6M14 11v6M5.5 7l1 12.5A2 2 0 0 0 8.5 21h7a2 2 0 0 0 2-1.5l1-12.5M9 7V4.5h6V7"/>',
    "voltar": '<path d="m15 5-7 7 7 7"/>',
    "seta": '<path d="m9 5 7 7-7 7"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "capacete": '<path d="M3 17.5h18M4.5 17.5V15a7.5 7.5 0 0 1 15 0v2.5"/><path d="M10 7.8V5.5h4v2.3M12 7.5v4"/>',
    "clipe": '<path d="m20 11.5-8.5 8.5a5 5 0 0 1-7-7L13 4.5a3.3 3.3 0 0 1 4.7 4.7l-8.5 8.5a1.7 1.7 0 0 1-2.4-2.4L14.5 7.5"/>',
    "relogio": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "porcentagem": '<path d="M19 5 5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
    "caminhao": '<path d="M2.5 6.5h11v10h-11zM13.5 10h4l3 3.5v3h-7"/><circle cx="7" cy="17.5" r="2"/><circle cx="17" cy="17.5" r="2"/>',
    "chave": '<circle cx="8" cy="15" r="4.5"/><path d="m11.2 11.8 8.3-8.3M16.5 6.5l2.5 2.5M14 9l2 2"/>',
    "talheres": '<path d="M7 3v7a2 2 0 0 0 2 2v9M11 3v7a2 2 0 0 1-2 2M9 3v6M17 21V3c-2 1-3 3.5-3 7 0 1.5.8 2.5 3 2.5"/>',
    "xicara": '<path d="M4 9h12v5a6 6 0 0 1-6 6h0a6 6 0 0 1-6-6zM16 10.5h1.5a2.5 2.5 0 0 1 0 5H16M8 3.5v2.5M12 3.5v2.5"/>',
    "combustivel": '<path d="M4 21V5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v16M3 21h13M4 10h11"/><path d="M15 8h2a2 2 0 0 1 2 2v6.5a1.5 1.5 0 0 0 3 0V8l-3-3"/>',
    "sacola": '<path d="M5 8h14l-1 12.5H6z"/><path d="M9 10V7a3 3 0 0 1 6 0v3"/>',
    "escudo": '<path d="M12 3 4.5 6v6c0 4.5 3.2 8 7.5 9 4.3-1 7.5-4.5 7.5-9V6z"/><path d="m8.8 12.2 2.2 2.2 4.2-4.4"/>',
    "estorno": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "cubo": '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    "ferramenta": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3.5 17.5a1.4 1.4 0 0 0 2 2l5.8-5.8a4 4 0 0 0 5.4-5.4l-2.4 2.4-2-2z"/>',
    "sair": '<path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M9 16l-4-4 4-4M5 12h11"/>',
    "engrenagem": '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M21.5 12h-3M5.5 12h-3M18.7 5.3l-2.1 2.1M7.4 16.6l-2.1 2.1M18.7 18.7l-2.1-2.1M7.4 7.4 5.3 5.3"/>',
}

CATEGORIA = {
    1: ("pessoas", "ic-azul"), 2: ("caminhao", "ic-laranja"), 3: ("cubo", "ic-roxo"),
    4: ("chave", "ic-ciano"), 5: ("talheres", "ic-rosa"), 6: ("xicara", "ic-laranja"), 7: ("combustivel", "ic-vermelho"),
    8: ("sacola", "ic-verde"), 9: ("porcentagem", "ic-cinza"), 10: ("escudo", "ic-verde"), 11: ("estorno", "ic-cinza"),
}


@register.simple_tag
def icone(nome, classe="ic"):
    corpo = P.get(nome, P["lista"])
    return format_html(
        '<svg class="{}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>', classe, mark_safe(corpo))


@register.simple_tag
def icone_categoria(codigo, tamanho=""):
    nome, cor = CATEGORIA.get(int(codigo), ("lista", "ic-cinza"))
    return format_html('<span class="widget-ic {} {}">{}</span>', cor, tamanho, icone(nome, "ic"))
