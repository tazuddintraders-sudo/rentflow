/* RentFlow — reusable UI behaviours: sidebar, toasts, modal, slide-over */
(function () {
  // ---- Sidebar (mobile) ------------------------------------------------
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const menuToggle = document.getElementById("menuToggle");
  function closeSidebar() {
    sidebar && sidebar.classList.remove("is-open");
    backdrop && backdrop.classList.remove("is-open");
  }
  menuToggle && menuToggle.addEventListener("click", () => {
    sidebar.classList.toggle("is-open");
    backdrop.classList.toggle("is-open");
  });
  backdrop && backdrop.addEventListener("click", closeSidebar);

  // ---- Toasts -----------------------------------------------------------
  const stack = document.getElementById("toastStack");
  const ICONS = {
    success: '<svg><use href="#i-check-circle"/></svg>',
    error: '<svg><use href="#i-alert"/></svg>',
    warning: '<svg><use href="#i-alert"/></svg>',
    info: '<svg><use href="#i-check-circle"/></svg>',
  };
  window.toast = function (type, title, text, timeout = 4200) {
    if (!stack) return;
    const el = document.createElement("div");
    el.className = `toast toast--${type}`;
    el.innerHTML = `${ICONS[type] || ICONS.info}<div><strong></strong><span></span></div>`;
    el.querySelector("strong").textContent = title;
    el.querySelector("span").textContent = text || "";
    stack.appendChild(el);
    setTimeout(() => {
      el.classList.add("is-leaving");
      setTimeout(() => el.remove(), 260);
    }, timeout);
    return el;
  };

  // Django messages -> toasts
  (window.__django_messages || []).forEach(m => toast(m.type, m.title, m.text));

  // ---- Modal -------------------------------------------------------------
  const overlay = document.getElementById("modalOverlay");
  const box = document.getElementById("modalBox");
  const titleEl = document.getElementById("modalTitle");
  const bodyEl = document.getElementById("modalBody");
  const footEl = document.getElementById("modalFooter");
  let afterClose = null;

  function closeModal() {
    overlay.classList.remove("is-open");
    document.body.style.overflow = "";
    const fn = afterClose; afterClose = null;
    fn && fn();
  }
  document.getElementById("modalClose")?.addEventListener("click", closeModal);
  overlay?.addEventListener("click", e => { if (e.target === overlay) closeModal(); });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      if (overlay.classList.contains("is-open")) closeModal();
      const so = document.querySelector(".slide-over.is-open");
      so && closeSlideOver();
    }
  });

  window.openModal = function ({ title, body, footer, wide = false, onClose }) {
    titleEl.textContent = title || "Please confirm";
    bodyEl.innerHTML = body || "";
    footEl.innerHTML = footer || "";
    box.classList.toggle("modal--lg", wide);
    overlay.classList.add("is-open");
    document.body.style.overflow = "hidden";
    afterClose = onClose || null;
    return { body: bodyEl, footer: footEl, close: closeModal };
  };
  window.closeModal = closeModal;

  // Generic confirm modal used by data-confirm buttons / links
  document.addEventListener("click", async (e) => {
    const trigger = e.target.closest("[data-confirm]");
    if (!trigger) return;
    e.preventDefault();
    const message = trigger.getAttribute("data-confirm");
    const okLabel = trigger.getAttribute("data-ok-label") || "Confirm";
    const danger = trigger.hasAttribute("data-danger");
    const m = openModal({
      title: "Are you sure?",
      body: `<p class="muted" style="margin:0">${message}</p>`,
      footer: `
        <button class="btn btn--ghost" data-close-modal>Cancel</button>
        <button class="btn ${danger ? "btn--danger" : "btn--primary"}" id="confirmOk">${okLabel}</button>`,
    });
    m.footer.querySelector("[data-close-modal]").addEventListener("click", closeModal);
    m.footer.querySelector("#confirmOk").addEventListener("click", async (btn) => {
      const url = trigger.getAttribute("data-url") || trigger.getAttribute("href");
      const method = trigger.getAttribute("data-method") || "POST";
      if (url) {
        try {
          const data = await RF.api(url, { method, body: trigger.getAttribute("data-body") ? JSON.parse(trigger.dataset.body) : {} });
          closeModal();
          if (data.ok !== false) {
            toast("success", "Done", data.message || "Action completed.");
            setTimeout(() => {
              if (trigger.dataset.refresh !== "false") location.reload();
            }, 650);
          }
        } catch (err) {
          toast("error", "Action failed", err.message);
        }
      } else {
        closeModal();
        trigger.closest("form")?.requestSubmit();
      }
    });
  });

  // ---- Slide-over (payment details) -------------------------------------
  window.openSlideOver = function (html) {
    let so = document.getElementById("slideOver");
    if (!so) {
      so = document.createElement("aside");
      so.id = "slideOver";
      so.className = "slide-over";
      so.innerHTML = `
        <div class="slide-over__head">
          <h3 id="soTitle">Details</h3>
          <button class="modal-close" id="soClose"><svg><use href="#i-x"/></svg></button>
        </div>
        <div class="slide-over__body" id="soBody"></div>
        <div class="slide-over__foot" id="soFoot"></div>`;
      document.body.appendChild(so);
      document.getElementById("soClose").addEventListener("click", closeSlideOver);
    }
    document.getElementById("soBody").innerHTML = html;
    so.classList.add("is-open");
    document.body.style.overflow = "hidden";
    return { body: document.getElementById("soBody"), foot: document.getElementById("soFoot") };
  };
  window.closeSlideOver = function () {
    const so = document.getElementById("slideOver");
    so && so.classList.remove("is-open");
    document.body.style.overflow = "";
  };
})();
