/* Gráficos do painel. Cores e fontes vêm dos tokens do CSS (DESIGN.md). */
(function () {
  var fonte = document.getElementById("dados-graficos");
  if (!fonte || !window.Chart) return;
  var d = JSON.parse(fonte.textContent);
  var css = getComputedStyle(document.documentElement);
  var tok = function (n) { return css.getPropertyValue(n).trim(); };

  var brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  var curto = function (v) {
    var a = Math.abs(v);
    if (a >= 1e6) return "R$ " + (v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mi";
    if (a >= 1e3) return "R$ " + (v / 1e3).toLocaleString("pt-BR", { maximumFractionDigits: 0 }) + " mil";
    return brl.format(v);
  };

  Chart.defaults.font.family = tok("--fonte");
  Chart.defaults.font.size = 13;
  Chart.defaults.color = tok("--tinta-2");

  var eixoY = {
    beginAtZero: true,
    border: { display: false },
    grid: { color: tok("--separador"), drawTicks: false },
    ticks: { padding: 8, maxTicksLimit: 5, callback: function (v) { return curto(v); } },
  };
  var eixoX = { grid: { display: false }, border: { color: tok("--separador") }, ticks: { padding: 6, maxRotation: 0, autoSkipPadding: 8 } };
  var dica = {
    backgroundColor: tok("--tinta"), titleColor: tok("--cartao-solido"), bodyColor: tok("--cartao-solido"),
    padding: 10, cornerRadius: 8, displayColors: false,
    callbacks: { label: function (c) { return (c.dataset.label ? c.dataset.label + ": " : "") + brl.format(c.parsed.y); } },
  };

  var mes = document.getElementById("grafico-mes");
  if (mes) {
    new Chart(mes, {
      type: "bar",
      data: { labels: d.meses, datasets: [{ data: d.gasto, backgroundColor: tok("--serie-1"),
        hoverBackgroundColor: tok("--acento-texto"), borderRadius: { topLeft: 6, topRight: 6 },
        borderSkipped: "bottom", maxBarThickness: 36 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: Object.assign({}, dica, {
          callbacks: { label: function (c) { return brl.format(c.parsed.y) + " — clique para abrir o mês"; } } }) },
        scales: { x: eixoX, y: eixoY },
        onHover: function (e, el) { e.native.target.style.cursor = el.length ? "pointer" : "default"; },
        onClick: function (e, el) {
          if (el.length) window.location = "/financeiro/mes/" + d.chaves[el[0].index] + "/";
        },
      },
    });
  }

  var acum = document.getElementById("grafico-acumulado");
  if (acum) {
    // Faturado anda em degrau: cada NF é um salto, não uma rampa.
    var linha = function (rotulo, dados, cor, degrau) {
      return { label: rotulo, data: dados, borderColor: cor, backgroundColor: cor, borderWidth: 2,
        pointRadius: 0, pointHoverRadius: 5, pointHoverBorderWidth: 2, pointHoverBorderColor: tok("--cartao-solido"),
        cubicInterpolationMode: "monotone", stepped: degrau ? "before" : false };
    };
    new Chart(acum, {
      type: "line",
      data: { labels: d.meses, datasets: [
        linha("Gasto", d.acum_gasto, tok("--serie-1")),
        linha("Faturado", d.acum_faturado, tok("--serie-2"), true),
      ] },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { display: false }, tooltip: Object.assign({}, dica, { displayColors: true, boxPadding: 4 }) },
        scales: { x: eixoX, y: eixoY },
      },
    });
  }
})();
