/* Demonstração estática: o que precisa de servidor mostra um aviso. */
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
  document.addEventListener("submit", function (e) { e.preventDefault(); aviso(); var d = e.target.closest("dialog"); if (d) d.close(); }, true);
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
