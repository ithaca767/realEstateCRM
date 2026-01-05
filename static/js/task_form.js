// static/js/task_form.js
//
// Notes:
// - initTaskFormEnhancements() binds behaviors to a rendered task form instance.
// - The task modal loader is bound once at DOMContentLoaded and fetches /tasks/new?modal=1
//   then calls initTaskFormEnhancements() after injecting HTML.

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
      const resp = await fetch(`/tasks/options?contact_id=${encodeURIComponent(cid)}`, {
        credentials: "include",
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

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

    const resp = await fetch(`/contacts/search?q=${encodeURIComponent(term)}`, {
      credentials: "include",
    });

    if (!resp.ok) {
      contactResultsEl.style.display = "";
      contactResultsEl.innerHTML = `<div class="list-group-item text-danger">Search failed.</div>`;
      return;
    }

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
    contactShowSelected(label ? label : "Contact #" + contactHiddenId.value);
  }

  refreshTaskContactScopedDropdowns();

  // Close contact dropdown if clicking elsewhere
  if (!window.__taskFormDocClickBound) {
    window.__taskFormDocClickBound = true;

    document.addEventListener("click", (evt) => {
      // Since this handler is global, re-resolve elements each click (modal content can change)
      const input = document.getElementById("taskContactSearch");
      const results = document.getElementById("taskContactResults");
      const selectedWrap = document.getElementById("taskContactSelected");

      if (!input || !results) return;

      const clickedInside =
        input.contains(evt.target) ||
        results.contains(evt.target) ||
        (selectedWrap && selectedWrap.contains(evt.target));

      if (!clickedInside) results.style.display = "none";
    });
  }

  // Professional selector wiring is intentionally deferred.
};

// Bind the modal loader once, then init enhancements after HTML is injected.
document.addEventListener("DOMContentLoaded", () => {
  // If we are on a full page form (not modal), initialize immediately
  if (document.getElementById("taskContactId") && window.initTaskFormEnhancements) {
    window.initTaskFormEnhancements();
  }

  const modalEl = document.getElementById("taskModal");
  if (!modalEl) return;

  modalEl.addEventListener("show.bs.modal", async (event) => {
    const trigger = event.relatedTarget;
    const contactId = trigger?.getAttribute("data-contact-id") || "";
    const nextUrl = trigger?.getAttribute("data-next") || "";

    const body = modalEl.querySelector(".modal-body");
    if (!body) return;

    body.innerHTML = '<div class="text-muted">Loading...</div>';

    const url =
      "/tasks/new?modal=1" +
      "&contact_id=" + encodeURIComponent(contactId) +
      "&next=" + encodeURIComponent(nextUrl);

    try {
      const resp = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!resp.ok) throw new Error("HTTP " + resp.status);

      body.innerHTML = await resp.text();

      // After injecting the form HTML, bind task form behaviors to that DOM.
      if (window.initTaskFormEnhancements) {
        window.initTaskFormEnhancements();
      }

      // After injecting, bind engagement "See more" toggles if any exist in this DOM.
      if (window.bindEngagementSeeMore) {
        window.bindEngagementSeeMore(body);
      }
    } catch (err) {
      console.error(err);
      body.innerHTML =
        '<div class="alert alert-danger mb-0">' +
        "Could not load the task form. Please refresh and try again." +
        "</div>";
    }
  });
});

// Bootstrap modal focus warning fix: return focus to the trigger button
(function () {
  const modalEl = document.getElementById("taskModal");
  if (!modalEl) return;

  if (modalEl.dataset.focusFixBound === "1") return;
  modalEl.dataset.focusFixBound = "1";

  let lastTrigger = null;

  modalEl.addEventListener("show.bs.modal", (event) => {
    lastTrigger = event.relatedTarget || null;
  });

  modalEl.addEventListener("hidden.bs.modal", () => {
    if (lastTrigger && typeof lastTrigger.focus === "function") {
      lastTrigger.focus();
    }
    lastTrigger = null;
  });
})();

// Engagement "See more / See less" toggle binder
(function () {
  function bindEngagementSeeMore(root) {
    const scope = root || document;

    scope.querySelectorAll('[data-eng-toggle="1"]').forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";

      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-target");
        if (!targetId) return;

        const desc = document.getElementById(targetId);
        if (!desc) return;

        const isClamped = desc.classList.contains("is-clamped");
        if (isClamped) {
          desc.classList.remove("is-clamped");
          btn.textContent = "See less";
        } else {
          desc.classList.add("is-clamped");
          btn.textContent = "See more";
        }
      });
    });
  }

  // Expose for cases where we inject HTML and want to bind within that subtree.
  window.bindEngagementSeeMore = bindEngagementSeeMore;

  // Bind on initial page load
  document.addEventListener("DOMContentLoaded", () => bindEngagementSeeMore(document));
})();
