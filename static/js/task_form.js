window.initTaskFormEnhancements = function initTaskFormEnhancements() {
  // Bind once per rendered form instance
  const contactHiddenId = document.getElementById("taskContactId");
  if (!contactHiddenId) return;
  if (contactHiddenId.dataset.bound === "1") return;
  contactHiddenId.dataset.bound = "1";

  const contactInput = document.getElementById("taskContactSearch");
  const contactResultsEl = document.getElementById("taskContactResults");

  const contactSelectedWrap = document.getElementById("taskContactSelected");
  const contactSelectedLabel = document.getElementById("taskContactSelectedLabel");
  const contactBtnClear = document.getElementById("taskContactClear");

  if (!contactInput || !contactResultsEl) return;

  let contactTimer = null;

  function contactShowSelected(name) {
    if (contactSelectedLabel) contactSelectedLabel.textContent = name || "Selected contact";
    if (contactSelectedWrap) contactSelectedWrap.style.display = "";
    contactResultsEl.style.display = "none";
    contactResultsEl.innerHTML = "";
  }

  async function refreshTaskContactScopedDropdowns() {
    const cid = (contactHiddenId.value || "").trim();

    const txSel = document.getElementById("taskTransactionId");
    const engSel = document.getElementById("taskEngagementId");
    const txHelp = document.getElementById("taskTransactionHelp");
    const engHelp = document.getElementById("taskEngagementHelp");

    if (!txSel || !engSel) return;

    // Preserve current selections if still valid
    const prevTx = txSel.value || "";
    const prevEng = engSel.value || "";

    txSel.innerHTML = `<option value="">—</option>`;
    engSel.innerHTML = `<option value="">—</option>`;

    if (!cid) {
      if (txHelp) txHelp.textContent = "Select a contact first.";
      if (engHelp) engHelp.textContent = "Select a contact first.";
      return;
    }

    if (txHelp) txHelp.textContent = "Loading...";
    if (engHelp) engHelp.textContent = "Loading...";

    try {
      const resp = await fetch(`/tasks/options?contact_id=${encodeURIComponent(cid)}`, { credentials: "include" });
      const data = await resp.json();

      (data.transactions || []).forEach((tx) => {
        const parts = [];
        if (tx.address) parts.push(tx.address);
        if (tx.transaction_type) parts.push(tx.transaction_type.replaceAll("_", " "));
        if (tx.status) parts.push(tx.status.replaceAll("_", " "));
        if (tx.expected_close_date) parts.push(tx.expected_close_date);

        const opt = document.createElement("option");
        opt.value = String(tx.id);
        opt.textContent = parts.join(" · ") || `Transaction #${tx.id}`;
        txSel.appendChild(opt);
      });

      (data.engagements || []).forEach((e) => {
        const parts = [];
        if (e.engagement_type) parts.push(e.engagement_type.replaceAll("_", " "));
        if (e.occurred_at) parts.push(e.occurred_at);

        let s = (e.summary_display || "").trim();
        if (s.length > 110) s = s.slice(0, 110) + "...";
        if (s) parts.push(s);

        const opt = document.createElement("option");
        opt.value = String(e.id);
        opt.textContent = parts.join(" · ") || `Engagement #${e.id}`;
        engSel.appendChild(opt);
      });

      // Restore selection if still present, otherwise keep blank
      if (prevTx) txSel.value = prevTx;
      if (prevEng) engSel.value = prevEng;

      if (txHelp) txHelp.textContent = "";
      if (engHelp) engHelp.textContent = "";
    } catch (err) {
      if (txHelp) txHelp.textContent = "Could not load transactions.";
      if (engHelp) engHelp.textContent = "Could not load engagements.";
    }
  }

  function contactClearSelected() {
    contactHiddenId.value = "";
    contactHiddenId.dispatchEvent(new Event("change"));

    if (contactSelectedWrap) contactSelectedWrap.style.display = "none";
    if (contactSelectedLabel) contactSelectedLabel.textContent = "";
    contactInput.value = "";
    contactInput.focus();

    refreshTaskContactScopedDropdowns();
  }

  if (contactBtnClear) contactBtnClear.addEventListener("click", contactClearSelected);

  async function contactDoSearch(q) {
    const term = (q || "").trim();
    if (term.length < 2) {
      contactResultsEl.style.display = "none";
      contactResultsEl.innerHTML = "";
      return;
    }

    const resp = await fetch(`/contacts/search?q=${encodeURIComponent(term)}`, { credentials: "include" });
    const data = await resp.json();

    contactResultsEl.innerHTML = "";
    contactResultsEl.style.display = "";

    if (!data || data.length === 0) {
      contactResultsEl.innerHTML = `<div class="list-group-item text-muted">No matches.</div>`;
      return;
    }

    data.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "list-group-item list-group-item-action";

      const meta = [item.email, item.phone].filter(Boolean).join(" · ");
      btn.innerHTML = `<div class="fw-semibold">${item.name}</div><div class="text-muted small">${meta}</div>`;

      btn.addEventListener("click", async () => {
        contactHiddenId.value = item.id;
        contactHiddenId.dispatchEvent(new Event("change"));

        contactInput.value = item.name;
        contactShowSelected(item.name);

        await refreshTaskContactScopedDropdowns();
      });

      contactResultsEl.appendChild(btn);
    });
  }

  contactInput.addEventListener("input", () => {
    clearTimeout(contactTimer);
    contactTimer = setTimeout(() => contactDoSearch(contactInput.value), 200);
  });

  // If prefilled, show selected badge and populate dropdowns
  if (contactHiddenId.value) {
    const label = (contactInput.value || "").trim();
    contactShowSelected(label ? label : ("Contact #" + contactHiddenId.value));
  }

  refreshTaskContactScopedDropdowns();

  // Close contact dropdown if clicking elsewhere
  document.addEventListener("click", (evt) => {
    const clickedInside = contactInput.contains(evt.target) || contactResultsEl.contains(evt.target) || (contactSelectedWrap && contactSelectedWrap.contains(evt.target));
    if (!clickedInside) contactResultsEl.style.display = "none";
  });

  // NOTE: Remove or ignore the old initEntitySelector() calls for transaction/engagement.
  // If you keep Professional as a search field, we will wire that separately after you confirm the HTML IDs still exist.
};
