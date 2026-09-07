/* RentFlow — global behaviours (auto-initialised) */
(function () {
  // File input: show selected file name
  document.querySelectorAll('input[type=file]').forEach(input => {
    input.addEventListener("change", () => {
      const label = input.closest("label, .field");
      const out = document.querySelector(`[data-file-name-for="${input.id}"]`);
      if (out && input.files.length) out.textContent = input.files[0].name;
    });
  });

  // Month chips: visual state
  document.addEventListener("change", e => {
    const chip = e.target.closest(".month-chip");
    if (chip) chip.classList.toggle("is-checked", e.target.checked);
    const rc = e.target.closest(".radio-card input");
    if (rc) { /* CSS handles */ }
  });

  // Method radio -> toggle panels
  document.querySelectorAll("[data-method-toggle]").forEach(radio => {
    radio.addEventListener("change", () => {
      const group = radio.closest("[data-method-group]") || document;
      group.querySelectorAll(".method-panel").forEach(p =>
        p.classList.toggle("is-active", p.dataset.panel === radio.value));
    });
  });

  // Smooth scroll for in-page anchors
  document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(a => {
    a.addEventListener("click", e => {
      const t = document.querySelector(a.getAttribute("href"));
      if (t) { e.preventDefault(); t.scrollIntoView({ behavior: "smooth", block: "start" }); }
    });
  });
})();
