"""Limpeza de texto e dinheiro vindos da planilha ou de formulário."""
import re
import unicodedata
from decimal import Decimal, InvalidOperation


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def limpar(texto):
    """Tira espaço duro, espaço duplicado e bordas. None vira ''."""
    if texto is None:
        return ""
    texto = str(texto).replace("\xa0", " ")
    return re.sub(r"\s+", " ", texto).strip()


def chave(texto):
    """Forma de comparar nomes: 'Paranáferros ' e 'PARANAFERROS' são o mesmo."""
    t = sem_acento(limpar(texto)).upper()
    t = re.sub(r"[^A-Z0-9& ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def dinheiro(valor):
    """Converte o que a planilha guarda como valor em Decimal, ou None.

    Aceita número, 'R$ 1.234,56', '1234,56', '1234.56', '1.089' (milhar) e o
    erro de digitação real '3,000,00' (vírgula como milhar e como decimal).
    Devolve None quando não dá para ter certeza -- um buraco marcado é melhor
    que um número plausível errado.
    """
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float, Decimal)):
        try:
            return Decimal(str(valor)).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None
    t = limpar(valor).upper().replace("R$", "").replace("$", "").replace(" ", "")
    if not t or not re.fullmatch(r"-?[\d.,]+", t):
        return None
    negativo = t.startswith("-")
    t = t.lstrip("-")
    separadores = [c for c in t if c in ".,"]
    if not separadores:
        inteiro, decimal = t, ""
    else:
        ultimo = max(t.rfind(","), t.rfind("."))
        cauda = t[ultimo + 1:]
        if len(cauda) in (1, 2):
            inteiro, decimal = t[:ultimo], cauda
        elif len(cauda) == 3 and len(separadores) >= 1:
            inteiro, decimal = t, ""
        else:
            return None
        inteiro = inteiro.replace(".", "").replace(",", "")
    if not inteiro.isdigit():
        return None
    numero = Decimal(f"{inteiro}.{decimal or '0'}").quantize(Decimal("0.01"))
    return -numero if negativo else numero


def brl(valor, casas=2):
    """1234.5 -> 'R$ 1.234,50'."""
    if valor is None:
        return "—"
    numero = f"{abs(Decimal(valor)):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {numero}" if Decimal(valor) < 0 else f"R$ {numero}"
