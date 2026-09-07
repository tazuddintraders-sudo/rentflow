/* RentFlow — payment portal: auto-fetch, due-month detection, verify, invoice */
(function () {
  const $ = s => document.querySelector(s);
  const state = { occupancyId: null, rent: 0, periods: [], info: null };

  const buildingSel = $("#buildingSelect");
  const flatSel = $("#flatSelect");
  const autoFetch = $("#autoFetch");
  const vacantNote = $("#vacantNote");
  const dueAlert = $("#dueAlert");
  const methodSection = $("#methodSection");
  const verifySection = $("#verifySection");
  const verifyBtn = $("#verifyBtn");
  const verifyResult = $("#verifyResult");
  const verifySpinner = $("#verifySpinner");
  const invoiceBlock = $("#invoiceBlock");
  const totalEl = $("#totalAmount");
  const generateBtn = $("#generateBtn");

  // ---- Stepper helpers ---------------------------------------------------
  function setStep(n) {
    document.querySelectorAll("#stepper .step").forEach(s => {
      const num = Number(s.dataset.step);
      s.classList.toggle("is-active", num === n);
      s.classList.toggle("is-done", num < n);
    });
  }
  function lockSection(sectionEl, locked) {
    sectionEl.style.opacity = locked ? ".55" : "1";
    sectionEl.style.pointerEvents = locked ? "none" : "auto";
  }
  lockSection(methodSection, true);
  lockSection(verifySection, true);

  // ---- Building -> flats --------------------------------------------------
  buildingSel?.addEventListener("change", async () => {
    flatSel.innerHTML = '<option value="">Loading…</option>';
    flatSel.disabled = true;
    if (!buildingSel.value) { resetFlat(); return; }
    try {
      const data = await RF.api(`/payments/api/building/${buildingSel.value}/flats/`);
      flatSel.innerHTML = '<option value="">— Select flat —</option>';
      data.flats.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.id;
        opt.textContent = `${f.flat_no} (${f.flat_type}) — ${f.status}`;
        opt.disabled = f.status === "Vacant";
        flatSel.appendChild(opt);
      });
      flatSel.disabled = false;
    } catch (e) {
      flatSel.innerHTML = '<option value="">Could not load flats</option>';
    }
  });

  function resetFlat() {
    flatSel.innerHTML = '<option value="">Select a building first</option>';
    flatSel.disabled = true;
    autoFetch.style.display = "none";
    vacantNote.style.display = "none";
    state.occupancyId = null; state.periods = [];
    lockSection(methodSection, true); lockSection(verifySection, true);
  }

  // ---- Flat -> occupant info ----------------------------------------------
  flatSel?.addEventListener("change", () => loadFlatInfo());
  $("#refreshInfo")?.addEventListener("click", loadFlatInfo);

  async function loadFlatInfo() {
    if (!flatSel.value) { resetFlat(); return; }
    setStep(1);
    const data = await RF.api(`/payments/api/flat/${flatSel.value}/info/`);
    if (!data.occupied) {
      autoFetch.style.display = "none";
      vacantNote.style.display = "flex";
      lockSection(methodSection, true); lockSection(verifySection, true);
      return;
    }
    vacantNote.style.display = "none";
    autoFetch.style.display = "block";
    state.occupancyId = data.occupancy_id;
    state.rent = data.rent;
    state.info = data;
    state.periods = data.due_periods;

    $("#afName").value = data.occupant.name;
    $("#afNid").value = `${data.occupant.id_type}: ${data.occupant.nid}`;
    $("#afEmail").value = data.occupant.email;
    $("#afPhone").value = data.occupant.phone;
    $("#afRent").value = RF.money(data.rent) + " / month";
    $("#invoiceEmail").value = data.occupant.email;

    renderDuePeriods(data.due_periods);
    updateTotal();
    lockSection(methodSection, false);
    lockSection(verifySection, false);
    verifyBtn.disabled = false;
    invoiceBlock.style.display = "none";
    setStep(2);
  }

  function renderDuePeriods(periods) {
    if (!periods.length) {
      dueAlert.style.display = "block";
      dueAlert.className = "mt-6 alert alert--success";
      dueAlert.innerHTML = `<svg><use href="#i-check-circle"/></svg>
        <div><b>All rent is up to date.</b> No unpaid periods for this tenancy.</div>`;
      return;
    }
    const overdue = periods.filter(p => p.status === "overdue");
    dueAlert.style.display = "flex";
    dueAlert.className = "due-alert";
    const warn = overdue.length
      ? `<h4>Rent due — ${overdue.length} month${overdue.length > 1 ? "s" : ""} overdue</h4>
         Select the month(s) you are collecting payment for:`
      : `<h4>Rent payment for the current period</h4>Select the month(s) to include on this invoice:`;
    dueAlert.innerHTML = `<svg><use href="#i-alert"/></svg><div>${warn}
      <div class="month-pick">
        ${periods.map((p, i) => `
          <label class="month-chip ${p.status === 'overdue' ? 'is-checked' : ''}">
            <input type="checkbox" name="period" value="${p.year}-${p.month}"
                   ${p.status === "overdue" ? "checked" : ""}>
            <span><b>${p.label}</b>
              <span class="muted"> · ${RF.money(p.rent)}
              ${p.status === "overdue" ? ` · <span style="color:var(--red-700);font-weight:700">${p.days_overdue}d late</span>` : ""}
              </span>
            </span>
          </label>`).join("")}
      </div></div>`;
    dueAlert.querySelectorAll("input").forEach(cb => cb.addEventListener("change", updateTotal));
  }

  function selectedPeriods() {
    return Array.from(dueAlert.querySelectorAll("input:checked")).map(cb => {
      const [y, m] = cb.value.split("-").map(Number);
      return { year: y, month: m };
    });
  }

  function updateTotal() {
    const sel = selectedPeriods();
    totalEl.textContent = RF.money(sel.length * state.rent);
  }

  // ---- Method details -----------------------------------------------------
  function methodDetails() {
    const method = document.querySelector("input[name=method]:checked")?.value;
    if (!method) return { method: null, details: {} };
    const d = {};
    if (method === "cash") {
      d.received_by = $("#cashReceivedBy").value.trim();
      d.received_date = $("#cashReceivedDate").value;
    } else if (method === "bank") {
      d.sender_bank = $("#bankSender").value;
      d.receiver_bank = $("#bankReceiver").value;
      d.txn_ref = $("#bankTxnRef").value.trim();
      d.transfer_date = $("#bankTransferDate").value;
      d.cheque_no = $("#bankCheque").value.trim();
    } else if (method === "bkash") {
      d.txn_id = $("#bkashTxnId").value.trim();
      d.sender_number = $("#bkashSender").value.trim();
      d.txn_datetime = $("#bkashDatetime").value;
    }
    return { method, details: d };
  }

  function readScreenshotFile() {
    const f = $("#bkashShot")?.files[0];
    if (!f) return Promise.resolve(null);
    return new Promise(res => {
      const r = new FileReader();
      r.onload = () => res(r.result);
      r.onerror = () => res(null);
      r.readAsDataURL(f);
    });
  }

  // ---- Verify -------------------------------------------------------------
  verifyBtn?.addEventListener("click", async () => {
    setStep(3);
    verifySpinner.style.display = "inline-block";
    verifyBtn.disabled = true;
    verifyResult.className = "verify-result verify-pending";
    verifyResult.textContent = "Checking…";
    const { method, details } = methodDetails();
    const screenshot = await readScreenshotFile();
    try {
      const payload = {
        occupancy_id: state.occupancyId,
        periods: selectedPeriods(),
        amount: selectedPeriods().length * state.rent,
        method, details,
      };
      const data = await RF.api("/payments/api/verify/", { method: "POST", body: payload });
      verifySpinner.style.display = "none";
      verifyBtn.disabled = false;
      verifyResult.className = "verify-result verify-ok";
      verifyResult.innerHTML = `<svg><use href="#i-check-circle"/></svg> ${data.message}`;
      invoiceBlock.style.display = "block";
      invoiceBlock.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (err) {
      verifySpinner.style.display = "none";
      verifyBtn.disabled = false;
      verifyResult.className = "verify-result";
      verifyResult.innerHTML =
        `<div class="alert alert--danger" style="margin:0">
           <svg><use href="#i-alert"/></svg>
           <div><b>Please fix the following:</b><ul class="verify-errors">
             ${(err.data.errors || [err.message]).map(e => `<li>${e}</li>`).join("")}
           </ul></div></div>`;
      invoiceBlock.style.display = "none";
    }
  });

  // ---- Generate -----------------------------------------------------------
  generateBtn?.addEventListener("click", async () => {
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner"></span> Generating…';
    const { method, details } = methodDetails();
    const screenshot = await readScreenshotFile();
    try {
      const payload = {
        occupancy_id: state.occupancyId,
        periods: selectedPeriods(),
        method, details,
        payment_date: $("#paymentDate").value,
        email: $("#invoiceEmail").value.trim(),
        send_email: $("#sendEmailCheck").checked,
        screenshot_data: screenshot,
      };
      const data = await RF.api("/payments/api/generate/", { method: "POST", body: payload });
      showSuccess(data);
    } catch (err) {
      toast("error", "Could not generate invoice", err.message);
    } finally {
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<svg><use href="#i-receipt"/></svg> Generate Invoice &amp; Send';
    }
  });

  function showSuccess(data) {
    const total = data.payments.reduce((a, p) => a + p.amount, 0);
    $("#successText").textContent =
      `${data.payments.length} invoice${data.payments.length > 1 ? "s" : ""} for ${state.info.occupant.name} — ${data.emailed ? "and emailed" : "saved (email not sent)"}.`;
    $("#successReceipt").innerHTML =
      `<div class="sr-row"><span class="muted">Invoice</span><b>${data.invoices.map(i => i.number).join(", ")}</b></div>
       <div class="sr-row"><span class="muted">Total</span><span>${RF.money(total)}</span></div>
       <div class="sr-row"><span class="muted">Next</span><span>History &amp; dashboard updated</span></div>`;
    const actions = $("#successActions");
    actions.innerHTML = `
      <a class="btn btn--ghost" href="${data.invoices[0].pdf_url}" target="_blank"><svg><use href="#i-printer"/></svg> Print / View</a>
      <a class="btn btn--soft" href="${data.invoices[0].pdf_url}" download><svg><use href="#i-download"/></svg> Download PDF</a>
      <a class="btn btn--primary" href="${data.redirect}"><svg><use href="#i-credit"/></svg> Go to history</a>`;
    $("#successModal").classList.add("is-open");
    document.body.style.overflow = "hidden";
  }

  // bKash file name
  $("#bkashShot")?.addEventListener("change", e => {
    $("#bkashShotName").textContent = e.target.files[0] ? e.target.files[0].name : "";
  });

  // ---- Preselect from URL (?building=&flat=) -------------------------------
  const params = new URLSearchParams(location.search);
  if (params.get("building")) {
    buildingSel.value = params.get("building");
    buildingSel.dispatchEvent(new Event("change"));
    if (params.get("flat")) {
      const wait = setInterval(() => {
        if (!flatSel.disabled) {
          clearInterval(wait);
          flatSel.value = params.get("flat");
          if (flatSel.value) flatSel.dispatchEvent(new Event("change"));
        }
      }, 120);
    }
  }
})();
