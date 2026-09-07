/* RentFlow — dependency-free charts rendered as inline SVG / CSS.
   Public API (auto-init from data attributes, or call directly):
     RF.donut(el, {segments:[{label,value,color}], center:{big,small}})
     RF.barChart(el, {bars:[{label, value, current, tip}]})
     RF.gauge(el, {value: 0-100, label})
*/
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const COLORS = {
    green: "#219653", amber: "#d49b24", red: "#d65353",
    navy: "#1c3c64", orange: "#e87d32", gray: "#cfd6e0",
  };

  function el(tag, attrs, parent) {
    const node = document.createElementNS(NS, tag);
    for (const k in attrs) node.setAttribute(k, attrs[k]);
    parent && parent.appendChild(node);
    return node;
  }

  // --------------------------------------------------------------- Donut
  function donut(container, opts) {
    const segs = opts.segments.filter(s => s.value > 0);
    const total = segs.reduce((a, s) => a + s.value, 0) || 1;
    const size = 168, stroke = 22, r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;

    const wrap = document.createElement("div");
    wrap.className = "donut-wrap";
    wrap.innerHTML = `
      <div class="donut">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
          <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none"
                  stroke="#eef1f5" stroke-width="${stroke}"/>
          <g class="segments"></g>
        </svg>
        <div class="donut-center">
          <div><b>${opts.center.big}</b><br><span>${opts.center.small}</span></div>
        </div>
      </div>
      <div class="legend"></div>`;
    const g = wrap.querySelector(".segments");
    const legend = wrap.querySelector(".legend");

    let offset = 0;
    segs.forEach((s, i) => {
      const frac = s.value / total;
      const len = frac * c;
      const circle = el("circle", {
        class: "donut-seg",
        cx: size / 2, cy: size / 2, r, fill: "none",
        stroke: s.color, "stroke-width": stroke,
        "stroke-dasharray": `0 ${c}`,
        "stroke-dashoffset": -offset,
        transform: `rotate(-90 ${size/2} ${size/2})`,
      }, g);
      requestAnimationFrame(() => setTimeout(() => {
        circle.setAttribute("stroke-dasharray", `${Math.max(len - 2, 0)} ${c}`);
      }, 120 + i * 130));
      offset += len;

      const row = document.createElement("div");
      row.className = "legend__row";
      row.innerHTML = `<span class="legend__dot" style="background:${s.color}"></span>
        <span class="legend__label">${s.label}</span>
        <span class="legend__value">${s.value}</span>`;
      legend.appendChild(row);
    });

    container.innerHTML = "";
    container.appendChild(wrap);
  }

  // ------------------------------------------------------------ Bar chart
  function barChart(container, opts) {
    const bars = opts.bars;
    const max = Math.max(...bars.map(b => b.value), 1);
    const chart = document.createElement("div");
    chart.className = "bar-chart";
    bars.forEach((b, i) => {
      const col = document.createElement("div");
      col.className = "bar-col";
      const pct = Math.round((b.value / max) * 100);
      col.innerHTML = `
        <div class="bar ${b.current ? "bar--current" : ""}" style="height:0%">
          <span class="bar__tip">${b.tip || RF.money(b.value)}</span>
        </div>
        <span class="bar-label">${b.label}</span>`;
      chart.appendChild(col);
      requestAnimationFrame(() => setTimeout(() => {
        col.querySelector(".bar").style.height = Math.max(pct, 2) + "%";
      }, 150 + i * 90));
    });
    container.innerHTML = "";
    container.appendChild(chart);
  }

  // --------------------------------------------------------------- Gauge
  function gauge(container, opts) {
    const value = Math.max(0, Math.min(100, opts.value || 0));
    const w = 150, h = 92, sw = 14;
    const cx = w / 2, cy = h - 12, r = 58;
    const arc = Math.PI * r; // half-circle length
    const svg = el("svg", { class: "gauge", width: w, height: h, viewBox: `0 0 ${w} ${h}` });
    el("defs", {}, svg);
    const grad = `
      <defs><linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#1c3c64"/><stop offset="100%" stop-color="#e87d32"/>
      </linearGradient></defs>`;
    svg.insertAdjacentHTML("beforeend", grad);
    el("path", {
      class: "gauge-track", d: `M ${cx-r} ${cy} A ${r} ${r} 0 0 1 ${cx+r} ${cy}`,
      fill: "none", stroke: "#eef1f5", "stroke-width": sw, "stroke-linecap": "round",
    }, svg);
    const fill = el("path", {
      class: "gauge-fill", d: `M ${cx-r} ${cy} A ${r} ${r} 0 0 1 ${cx+r} ${cy}`,
      fill: "none", stroke: "url(#gaugeGrad)", "stroke-width": sw,
      "stroke-linecap": "round", "stroke-dasharray": `0 ${arc}`,
    }, svg);
    const txt = el("text", { x: cx, y: cy - 14, "text-anchor": "middle", "font-size": 22, fill: "#0e2547" }, svg);
    txt.textContent = value + "%";
    const lbl = el("text", { x: cx, y: cy + 4, "text-anchor": "middle", "font-size": 10, fill: "#6f798a", "font-weight": "400" }, svg);
    lbl.textContent = opts.label || "occupied";
    container.innerHTML = "";
    container.appendChild(svg);
    requestAnimationFrame(() => setTimeout(() => {
      fill.setAttribute("stroke-dasharray", `${(value / 100) * arc} ${arc}`);
    }, 200));
  }

  RF.donut = donut;
  RF.barChart = barChart;
  RF.gauge = gauge;
  RF.CHART_COLORS = COLORS;

  // Auto-init from JSON in <script type="application/json" data-chart="donut">
  document.querySelectorAll("script[data-chart]").forEach(tag => {
    const target = document.getElementById(tag.dataset.target);
    if (!target) return;
    try {
      const opts = JSON.parse(tag.textContent);
      ({ donut, barChart, gauge })[tag.dataset.chart](target, opts);
    } catch (e) { console.warn("chart init failed", e); }
  });
})();
