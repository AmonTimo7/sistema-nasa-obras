/* Login da demonstração estática: confere o hash de usuario:senha no navegador. */
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
