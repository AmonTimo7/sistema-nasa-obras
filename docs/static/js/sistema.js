/* Comportamentos pequenos e gerais. Nada de conta de dinheiro aqui: as
   regras moram no servidor (financeiro/regras.py). */
(function () {
  // barra de título ganha a linha fina quando o conteúdo rola por baixo
  var area = document.getElementById("conteudo");
  var topo = document.querySelector(".topo");
  if (area && topo) {
    area.addEventListener("scroll", function () { topo.classList.toggle("rolou", area.scrollTop > 8); }, { passive: true });
  }

  // linha de tabela clicável
  document.addEventListener("click", function (e) {
    var tr = e.target.closest("tr[data-href]");
    if (!tr || e.target.closest("a, button, input, select, form")) return;
    window.location = tr.getAttribute("data-href");
  });

  // abrir diálogo: <button data-dialogo="id"> ; o diálogo pode receber a ação do form
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-dialogo]");
    if (!b) return;
    var d = document.getElementById(b.getAttribute("data-dialogo"));
    if (!d) return;
    var form = d.querySelector("form");
    if (form && b.getAttribute("data-acao")) form.action = b.getAttribute("data-acao");
    var titulo = d.querySelector("[data-titulo]");
    if (titulo && b.getAttribute("data-texto")) titulo.textContent = b.getAttribute("data-texto");
    d.showModal();
  });
  document.addEventListener("click", function (e) {
    if (e.target.matches("[data-fechar]")) e.target.closest("dialog").close();
  });

  // prévia do valor da mão de obra (o servidor recalcula ao salvar)
  function numero(v) {
    if (!v) return 0;
    v = String(v).replace(/[R$\s]/g, "");
    if (v.indexOf(",") >= 0) v = v.replace(/\./g, "").replace(",", ".");
    var n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  }
  var brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  var form = document.querySelector("form[data-calculo]");
  if (form) {
    var campo = function (n) { return form.querySelector("[name=" + n + "]"); };
    var saida = document.getElementById("total-calculado");
    var diariasPorPessoa = JSON.parse((document.getElementById("diarias-prestadores") || {}).textContent || "{}");
    var atualizar = function () {
      if (!saida) return;
      var tipo = campo("tipo_mao_de_obra");
      var total = null;
      if (form.dataset.calculo === "mao" && tipo && ["diarias", "empreita", "mensal"].indexOf(tipo.value) >= 0) {
        total = numero(campo("diarias") && campo("diarias").value) * numero(campo("valor_diaria") && campo("valor_diaria").value)
          + numero(campo("adicional") && campo("adicional").value) - numero(campo("desconto") && campo("desconto").value);
      } else if (campo("valor") && campo("valor").value) {
        total = numero(campo("valor").value);
      } else if (campo("quantidade") && campo("valor_unitario") && campo("valor_unitario").value) {
        total = numero(campo("quantidade").value) * numero(campo("valor_unitario").value);
      }
      saida.textContent = total === null ? "—" : brl.format(total);
    };
    form.addEventListener("input", atualizar);
    var prest = campo("prestador");
    if (prest) prest.addEventListener("change", function () {
      var vd = campo("valor_diaria");
      if (vd && diariasPorPessoa[prest.value]) { vd.value = diariasPorPessoa[prest.value]; atualizar(); }
    });
    var forma = campo("forma_pagamento");
    var prazo = form.querySelectorAll("[data-a-prazo]");
    var mostrarPrazo = function () {
      var ap = forma && (forma.value === "boleto" || forma.value === "faturado");
      prazo.forEach(function (el) { el.style.display = ap ? "" : "none"; });
    };
    if (forma) { forma.addEventListener("change", mostrarPrazo); mostrarPrazo(); }
    var tipoMo = campo("tipo_mao_de_obra");
    var soDiarias = form.querySelectorAll("[data-so-calculado]");
    var mostrarTipo = function () {
      var calc = tipoMo && ["diarias", "empreita", "mensal"].indexOf(tipoMo.value) >= 0;
      soDiarias.forEach(function (el) { el.style.display = calc ? "" : "none"; });
    };
    if (tipoMo) { tipoMo.addEventListener("change", function () { mostrarTipo(); atualizar(); }); mostrarTipo(); }
    atualizar();
  }
})();
