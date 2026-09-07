/* RentFlow — payment row click -> slide-over with full details + actions */
(function () {
  const STATUS_COLORS = { paid: "paid", pending: "pending", overdue: "overdue" };

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function openPayment(id) {
    const p = await RF.api(`/payments/api/payment/${id}/`);
    const d = p.details || {};
    let methodRows = "";
    if (p.method === "cash") {
      methodRows = `
        <dt>Received by</dt><dd>${esc(d.received_by) || "—"}</dd>
        <dt>Received on</dt><dd>${esc(d.received_date) || "—"}</dd>`;
    } else if (p.method === "bank") {
      methodRows = `
        <dt>Sender bank</dt><dd>${esc(d.sender_bank)}</dd>
        <dt>Receiver bank</dt><dd>${esc(d.receiver_bank)}</dd>
        <dt>Transaction ref</dt><dd>${esc(d.txn_ref)}</dd>
        <dt>Transfer date</dt><dd>${esc(d.transfer_date)}</dd>
        <dt>Cheque no.</dt><dd>${esc(d.cheque_no) || "—"}</dd>`;
    } else {
      methodRows = `
        <dt>Transaction ID</dt><dd>${esc(d.txn_id)}</dd>
        <dt>Sender number</dt><dd>${esc(d.sender_number)}</dd>
        <dt>Date &amp; time</dt><dd>${esc(d.txn_datetime) || "—"}</dd>`;
    }

    const so = openSlideOver("");
    so.body.innerHTML = `
      <div class="spread mb-2">
        <span class="badge badge--${STATUS_COLORS[p.status] || 'plain'}">${esc(p.status_display)}</span>
        <span class="muted small mono">${esc(p.invoice_number)}</span>
      </div>
      <div class="detail-amount">৳${Number(p.amount).toLocaleString("en-IN")}</div>
      <div class="muted small">${esc(p.month)} · paid ${esc(p.payment_date)}</div>

      <div class="divider"></div>
      <h4 style="font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-500);margin-bottom:10px">Occupant</h4>
      <div class="occupant-line mb-2">
        <span class="avatar">${RF.initial(p.occupant.name)}</span>
        <div>
          <a class="cell-strong" href="${p.occupant.url}">${esc(p.occupant.name)}</a>
          <div class="cell-sub">${esc(p.flat)}</div>
        </div>
      </div>
      <dl class="kv">
        <dt>Phone</dt><dd>${esc(p.occupant.phone)}</dd>
        <dt>Email</dt><dd>${esc(p.occupant.email) || "—"}</dd>
        <dt>NID / ID</dt><dd>${esc(p.occupant.nid) || "—"}</dd>
      </dl>

      <div class="divider"></div>
      <h4 style="font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-500);margin-bottom:10px">
        ${esc(p.method_display)} details
      </h4>
      <dl class="kv">${methodRows}</dl>
      ${p.screenshot_url ? `<a href="${p.screenshot_url}" target="_blank"><img class="shot-preview" src="${p.screenshot_url}" alt="Transaction screenshot"></a>` : ""}

      <div class="divider"></div>
      <dl class="kv">
        <dt>Due date</dt><dd>${esc(p.due_date)}</dd>
        <dt>Recorded by</dt><dd>${esc(p.recorded_by)}</dd>
        <dt>Invoice</dt><dd>${p.has_invoice ? (p.emailed ? `Emailed to ${esc(p.emailed_to)}` : "Generated (not emailed)") : "—"}</dd>
      </dl>`;

    so.foot.innerHTML = "";
    if (p.pdf_url) {
      so.foot.insertAdjacentHTML("beforeend",
        `<a class="btn btn--ghost" href="${p.pdf_url}" target="_blank"><svg><use href="#i-eye"/></svg> View</a>
         <a class="btn btn--soft" href="${p.pdf_url}" download><svg><use href="#i-download"/></svg> PDF</a>
         <button class="btn btn--ghost" id="resendBtn"><svg><use href="#i-mail"/></svg> Resend</button>`);
      so.foot.querySelector("#resendBtn").addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true; btn.innerHTML = '<span class="spinner spinner--dark"></span>';
        try {
          const email = p.occupant.email || prompt("Email address to send the invoice to:");
          if (!email) { btn.disabled = false; btn.innerHTML = '<svg><use href="#i-mail"/></svg> Resend'; return; }
          await RF.api(p.resend_url, { method: "POST", body: { email } });
          toast("success", "Invoice sent", `Emailed to ${email}`);
        } catch (err) { toast("error", "Could not send", err.message); }
        btn.disabled = false; btn.innerHTML = '<svg><use href="#i-mail"/></svg> Resend';
      });
    }
    // Status editor
    so.foot.insertAdjacentHTML("beforeend",
      `<select class="input" id="statusEdit" style="width:auto;height:38px">
         <option value="paid" ${p.status === "paid" ? "selected" : ""}>Mark Paid</option>
         <option value="pending" ${p.status === "pending" ? "selected" : ""}>Mark Pending</option>
         <option value="overdue" ${p.status === "overdue" ? "selected" : ""}>Mark Overdue</option>
       </select>
       <button class="btn btn--danger" id="deleteBtn"><svg><use href="#i-trash"/></svg></button>`);

    so.foot.querySelector("#statusEdit").addEventListener("change", async (e) => {
      try {
        await RF.api(`/payments/api/payment/${p.id}/status/`, { method: "POST", body: { status: e.target.value } });
        toast("success", "Status updated", "The record has been refreshed.");
        setTimeout(() => location.reload(), 700);
      } catch (err) { toast("error", "Update failed", err.message); }
    });
    so.foot.querySelector("#deleteBtn").addEventListener("click", () => {
      if (!confirm("Delete this payment record? The invoice PDF will also be removed.")) return;
      RF.api(`/payments/api/payment/${p.id}/delete/`, { method: "POST" })
        .then(() => { closeSlideOver(); toast("success", "Deleted", "Payment record removed.");
          setTimeout(() => location.reload(), 700); })
        .catch(err => toast("error", "Delete failed", err.message));
    });
  }

  // Wire rows on dashboard + history pages
  document.addEventListener("click", (e) => {
    const row = e.target.closest("[data-payment-row]");
    if (!row) return;
    if (e.target.closest("a, button, input")) return;
    openPayment(row.dataset.paymentRow);
  });

  // Highlight target row after ?highlight=
  const hi = new URLSearchParams(location.search).get("highlight");
  if (hi) {
    const row = document.querySelector(`[data-payment-row="${hi}"]`);
    if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" }); row.style.background = "var(--orange-50)";
      setTimeout(() => openPayment(hi), 500); }
  }
})();
