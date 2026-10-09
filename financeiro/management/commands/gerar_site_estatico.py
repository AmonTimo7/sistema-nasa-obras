"""Gera a demonstração estática (GitHub Pages) a partir do sistema rodando.

Percorre as telas como um sócio logado, grava cada uma como HTML e troca os
links para caminhos relativos ao site publicado. O que depende de servidor
(salvar, filtrar, pagar, baixar) vira um aviso na tela.

Rode num banco DESCARTÁVEL só com dados fictícios (ver publicar_demo.ps1):

    SQLITE_PATH=/tmp/demo.sqlite3 python manage.py migrate
    SQLITE_PATH=/tmp/demo.sqlite3 python manage.py dados_exemplo
    SQLITE_PATH=/tmp/demo.sqlite3 python manage.py gerar_site_estatico --saida docs --base /repo/
"""
import hashlib
import html
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test import Client

from compras.models import Fornecedor
from core.models import Perfil

PREFIXOS = ("/financeiro/", "/compras/", "/juridico/")
# Ações e arquivos: não existem num site estático.
FORA = re.compile(r"exportar|/arquivo/|/excluir/|/pagar/|/desfazer/|/lancamentos/\d+/editar/|[?&]pagina=")
ATRIBUTO = re.compile(r'(href|src|data-href|action|data-acao)="([^"]*)"')


def canonico(link):
    """Formulário aberto com parâmetro (?prestador=, ?estorno_de=) vira o formulário simples."""
    partes = urlsplit(link)
    if re.search(r"/(novo|nova)/(\d+/)?$", partes.path) and partes.query:
        return partes.path
    return link


def caminho_de_saida(url):
    """'/financeiro/relatorios/?aba=concreto' -> 'financeiro/relatorios/q-aba-concreto/'"""
    partes = urlsplit(url)
    caminho = partes.path.strip("/")
    if partes.query:
        slug = "-".join(f"{k}-{v}" for k, v in sorted(parse_qsl(partes.query)))
        slug = re.sub(r"[^a-zA-Z0-9-]+", "-", slug).strip("-").lower()
        caminho = f"{caminho}/q-{slug}" if caminho else f"q-{slug}"
    return f"{caminho}/" if caminho else ""


class Command(BaseCommand):
    help = "Gera a demonstração estática do sistema (para o GitHub Pages)."

    def add_arguments(self, parser):
        parser.add_argument("--saida", default="docs")
        parser.add_argument("--base", default="/", help="Caminho do site publicado, ex.: /sistema-nasa-obras/")
        parser.add_argument("--repositorio", default="")
        parser.add_argument("--limite", type=int, default=1500)
        parser.add_argument("--usuario", default="", help="Login da demonstração (com --senha).")
        parser.add_argument("--senha", default="")

    def handle(self, *args, **o):
        if not Fornecedor.objects.filter(nome__startswith="[DEMO]").exists():
            raise CommandError("Sem dados de demonstração. Rode antes: manage.py dados_exemplo")
        if Fornecedor.objects.exclude(nome__startswith="[DEMO]").exists():
            raise CommandError("Este banco tem dados que não são de demonstração. Use um banco descartável "
                               "(SQLITE_PATH) só com o dados_exemplo.")
        base = "/" + o["base"].strip("/") + "/" if o["base"].strip("/") else "/"
        saida = Path(o["saida"])

        User = get_user_model()
        user, _ = User.objects.get_or_create(username="visitante", defaults={"first_name": "Visitante"})
        user.perfil.papel = Perfil.SOCIO
        user.perfil.precisa_trocar_senha = False
        user.perfil.save()
        cliente = Client(HTTP_HOST="127.0.0.1")
        cliente.force_login(user)

        from financeiro.models import Lancamento

        meses = {f"/financeiro/mes/{d.year}/{d.month}/" for d in
                 Lancamento.objects.values_list("competencia", flat=True).distinct()}

        def segue(link):
            if not link.startswith(PREFIXOS) or FORA.search(link):
                return False
            if link.startswith("/financeiro/mes/") and link != "/financeiro/mes/" and link not in meses:
                return False  # "mês anterior" andaria para trás sem fim
            return True

        paginas = {}
        fila = ["/financeiro/"]
        vistos = set(fila)
        while fila and len(paginas) < o["limite"]:
            url = fila.pop(0)
            r = cliente.get(url)
            if r.status_code != 200 or "text/html" not in r.get("Content-Type", ""):
                continue
            texto = r.content.decode("utf-8")
            paginas[url] = texto
            for _, valor in ATRIBUTO.findall(texto):
                link = canonico(html.unescape(valor).split("#")[0])
                if segue(link) and link not in vistos:
                    vistos.add(link)
                    fila.append(link)
        if saida.exists():
            shutil.rmtree(saida)
        saida.mkdir(parents=True)

        def trocar(m):
            attr, valor = m.group(1), m.group(2)
            link = canonico(html.unescape(valor))
            if link.startswith("/static/"):
                return f'{attr}="{base}{link.split("?")[0].lstrip("/")}"'
            if link in ("/", ""):
                return f'{attr}="{base}financeiro/"'
            if link.startswith("/"):
                if link in paginas:
                    return f'{attr}="{base}{caminho_de_saida(link)}"'
                return f'{attr}="#demo"'
            return m.group(0)

        repo = o["repositorio"]
        faixa = (
            '<div class="demo-faixa" role="note"><span class="pilula pilula-azul"><i></i>Demonstração</span>'
            "<span>Dados fictícios · só leitura</span>"
            + (f'<a href="{repo}" target="_blank" rel="noopener">código no GitHub</a>' if repo else "")
            + f'</div><script>window.DEMO_BASE="{base}";</script><script src="{base}static/js/demo.js"></script>'
        )
        porta = ""
        if o["usuario"] and o["senha"]:
            # Login feito no navegador (o Pages não tem servidor): barra quem chega
            # pelo link, mas não é segurança de verdade. No código vai só o hash.
            porta = (f'<script>try{{if(localStorage.getItem("nasa-demo")!=="ok")location.replace("{base}")}}'
                     f'catch(e){{location.replace("{base}")}}</script>')
            digest = hashlib.sha256(f'{o["usuario"].strip().lower()}:{o["senha"]}'.encode()).hexdigest()
        for url, texto in paginas.items():
            if porta:
                texto = texto.replace("<head>", "<head>" + porta, 1)
            texto = re.sub(r'<script src="/static/vendor/htmx\.min\.js[^"]*"[^>]*></script>', "", texto)
            texto = re.sub(r"\s(hx-[a-z-]+)='[^']*'", "", texto)
            texto = re.sub(r'<input type="hidden" name="csrfmiddlewaretoken"[^>]*>', "", texto)
            texto = ATRIBUTO.sub(trocar, texto)
            texto = texto.replace("</body>", faixa + "</body>")
            destino = saida / caminho_de_saida(url) / "index.html"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(texto, encoding="utf-8")

        estatico = saida / "static"
        for pasta in ("css", "js", "vendor"):
            shutil.copytree(Path(settings.BASE_DIR) / "static" / pasta, estatico / pasta)
        painel = estatico / "js" / "painel.js"
        painel.write_text(painel.read_text(encoding="utf-8").replace('"/financeiro/mes/"', f'"{base}financeiro/mes/"'),
                          encoding="utf-8")
        (estatico / "js" / "demo.js").write_text(DEMO_JS, encoding="utf-8")
        with open(estatico / "css" / "sistema.css", "a", encoding="utf-8") as css:
            css.write(DEMO_CSS)
        if porta:
            anonimo = Client(HTTP_HOST="127.0.0.1").get("/entrar/").content.decode("utf-8")
            anonimo = re.sub(r'<script src="/static/vendor/htmx[^"]*"[^>]*></script>', "", anonimo)
            anonimo = re.sub(r'<input type="hidden" name="csrfmiddlewaretoken"[^>]*>', "", anonimo)
            anonimo = re.sub(r"\s(hx-[a-z-]+)='[^']*'", "", anonimo)
            anonimo = ATRIBUTO.sub(trocar, anonimo)
            anonimo = anonimo.replace('<form method="post">', '<form method="post" id="entrar-demo">')
            anonimo = anonimo.replace(
                "</body>",
                f'<script>window.DEMO={{base:"{base}",chave:"{digest}"}};</script>'
                f'<script src="{base}static/js/entrar.js"></script></body>')
            (saida / "index.html").write_text(anonimo, encoding="utf-8")
            (estatico / "js" / "entrar.js").write_text(ENTRAR_JS, encoding="utf-8")
        else:
            (saida / "index.html").write_text(
                f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={base}financeiro/">'
                f'<title>Nasa Obras — demonstração</title><a href="{base}financeiro/">Abrir a demonstração</a>',
                encoding="utf-8")
        (saida / "404.html").write_text(
            f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="2; url={base}financeiro/">'
            f'<title>Não encontrado</title><p style="font-family:sans-serif">Esta tela não existe na demonstração. '
            f'Voltando ao painel…</p>', encoding="utf-8")
        (saida / ".nojekyll").write_text("", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"{len(paginas)} telas gravadas em {saida}/ (base {base})."))


DEMO_JS = """/* Demonstração estática: o que precisa de servidor mostra um aviso. */
(function () {
  function aviso() {
    var caixa = document.querySelector(".mensagens");
    if (!caixa) { caixa = document.createElement("div"); caixa.className = "mensagens"; document.body.appendChild(caixa); }
    var m = document.createElement("div");
    m.className = "mensagem";
    m.textContent = "Esta é uma demonstração estática: salvar, filtrar, pagar e baixar funcionam no sistema instalado.";
    caixa.appendChild(m);
    setTimeout(function () { m.remove(); }, 6000);
  }
  document.addEventListener("submit", function (e) {
    if (e.target.closest(".rodape")) {  // botão Sair
      e.preventDefault();
      try { localStorage.removeItem("nasa-demo"); } catch (x) {}
      window.location = window.DEMO_BASE || "./";
      return;
    }
    e.preventDefault(); aviso(); var d = e.target.closest("dialog"); if (d) d.close(); }, true);
  document.addEventListener("click", function (e) {
    var a = e.target.closest('a[href="#demo"]');
    if (a) { e.preventDefault(); aviso(); }
  }, true);
  document.addEventListener("change", function (e) {
    if (e.target.closest("form") && e.target.matches("select, input")) {
      if (e.target.closest(".seletor-obra")) return;
      if (e.target.closest("form[method=post], .filtros, .checklist-item")) aviso();
    }
  });
})();
"""

ENTRAR_JS = """/* Login da demonstração estática: confere o hash de usuario:senha no navegador. */
(function () {
  var form = document.getElementById("entrar-demo");
  if (!form) return;
  try { if (localStorage.getItem("nasa-demo") === "ok") { location.replace(DEMO.base + "financeiro/"); return; } } catch (e) {}
  function erro(texto) {
    var p = form.parentNode.querySelector(".erro-demo");
    if (!p) { p = document.createElement("p"); p.className = "negativo rotulo erro-demo"; p.style.margin = "14px 0 0"; form.parentNode.insertBefore(p, form); }
    p.textContent = texto;
  }
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var u = (form.username.value || "").trim().toLowerCase();
    var s = form.password.value || "";
    if (!window.crypto || !crypto.subtle) { erro("Abra pelo endereço https para entrar."); return; }
    crypto.subtle.digest("SHA-256", new TextEncoder().encode(u + ":" + s)).then(function (buf) {
      var hex = Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
      if (hex === DEMO.chave) {
        try { localStorage.setItem("nasa-demo", "ok"); } catch (x) {}
        location.replace(DEMO.base + "financeiro/");
      } else {
        erro("Usuário ou senha não conferem.");
        form.password.value = "";
        form.password.focus();
      }
    });
  });
})();
"""

DEMO_CSS = """
/* faixa da demonstração (só no site estático) */
.demo-faixa {
  position: fixed; left: 50%; bottom: var(--e-4); transform: translateX(-50%); z-index: 40;
  display: flex; gap: var(--e-3); align-items: center; padding: 6px var(--e-4) 6px 6px;
  border-radius: 999px; font-size: var(--t-rotulo); white-space: nowrap;
  background: var(--cartao); border: .5px solid var(--borda-luz); box-shadow: 0 10px 40px rgba(0,0,0,.18);
  -webkit-backdrop-filter: var(--desfoque); backdrop-filter: var(--desfoque);
}
@media (max-width: 760px) { .demo-faixa { bottom: var(--e-2); max-width: calc(100vw - 32px); } }
"""
