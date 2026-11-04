/* Vaultify UI behaviour – no dependencies. */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const csrf = () => {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : ($("[name=csrfmiddlewaretoken]") || {}).value || "";
  };

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrf(), "Content-Type": "application/json", "X-Requested-With": "fetch" },
      body: body ? JSON.stringify(body) : null,
      credentials: "same-origin",
    });
    if (res.status === 403 || res.redirected) { window.location.reload(); throw new Error("auth"); }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (window.vaultResetLock) window.vaultResetLock();
    return res.json();
  }

  const icon = (name, cls = "icon") => `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;

  // ---------------------------------------------------------------- toasts
  const toastRoot = () => $(".toasts") || document.body.appendChild(Object.assign(document.createElement("div"), { className: "toasts" }));
  const toastIcons = { success: "check-circle", error: "alert", warning: "alert", info: "info" };
  function toast(message, level = "success") {
    const el = document.createElement("div");
    el.className = `toast toast-${level}`;
    el.setAttribute("role", "status");
    el.innerHTML = `${icon(toastIcons[level] || "info")}<span></span>`;
    el.querySelector("span").textContent = message;
    toastRoot().appendChild(el);
    dismissLater(el);
  }
  function dismissLater(el, ms = 4200) {
    setTimeout(() => { el.classList.add("is-leaving"); setTimeout(() => el.remove(), 260); }, ms);
  }
  $$(".toast").forEach((t) => dismissLater(t, 5000));
  window.vaultToast = toast;

  // ---------------------------------------------------------------- theme
  const root = document.documentElement;
  $$("[data-theme-toggle]").forEach((btn) => btn.addEventListener("click", () => {
    const next = root.dataset.theme === "light" ? "dark" : "light";
    root.dataset.theme = next;
    try { localStorage.setItem("vaultify-theme", next); } catch (e) { /* ignore */ }
  }));

  // ---------------------------------------------------------------- sidebar (mobile)
  const sidebar = $(".sidebar");
  $$("[data-sidebar-toggle]").forEach((b) => b.addEventListener("click", (e) => {
    e.stopPropagation();
    sidebar && sidebar.classList.toggle("is-open");
  }));
  document.addEventListener("click", (e) => {
    if (sidebar && sidebar.classList.contains("is-open") && !sidebar.contains(e.target)) sidebar.classList.remove("is-open");
  });

  // ---------------------------------------------------------------- keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if (e.key === "/" && !typing) {
      const s = $("#global-search");
      if (s) { e.preventDefault(); s.focus(); s.select(); }
    } else if (e.key === "n" && !typing && !e.metaKey && !e.ctrlKey) {
      const n = $("[data-shortcut-new]");
      if (n) window.location.href = n.href;
    } else if (e.key === "Escape" && typing) {
      document.activeElement.blur();
    }
  });

  // ---------------------------------------------------------------- clipboard
  async function copyText(text, label = "Copied to clipboard") {
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      const ta = Object.assign(document.createElement("textarea"), { value: text });
      ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove();
    }
    toast(label);
  }
  window.vaultCopy = copyText;

  $$("[data-copy-text]").forEach((btn) => btn.addEventListener("click", () => copyText(btn.dataset.copyText, btn.dataset.copyLabel || "Copied")));

  // ---------------------------------------------------------------- reveal / copy secrets
  const HIDE_AFTER = 20000;
  $$("[data-copy-secret]").forEach((btn) => btn.addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      const data = await post(`${btn.dataset.copySecret}?action=copy`);
      if (!data.secret) return toast("This item has no secret to copy", "info");
      await copyText(data.secret, "Password copied — clipboard clears in 30s");
      setTimeout(() => navigator.clipboard && navigator.clipboard.writeText("").catch(() => {}), 30000);
    } catch (err) { if (err.message !== "auth") toast("Could not copy secret", "error"); }
  }));

  $$("[data-reveal]").forEach((btn) => {
    const target = $(btn.dataset.target);
    const notesTarget = btn.dataset.notesTarget ? $(btn.dataset.notesTarget) : null;
    let timer;
    const hide = () => {
      target.textContent = "••••••••••••••";
      if (notesTarget) notesTarget.textContent = "Hidden — reveal to view";
      btn.innerHTML = icon("eye"); btn.dataset.shown = "";
      btn.setAttribute("aria-label", "Reveal");
    };
    btn.addEventListener("click", async () => {
      if (btn.dataset.shown) { clearTimeout(timer); return hide(); }
      try {
        const data = await post(btn.dataset.reveal);
        target.textContent = data.secret || "—";
        if (notesTarget) notesTarget.textContent = data.notes || "—";
        btn.innerHTML = icon("eye-off"); btn.dataset.shown = "1";
        btn.setAttribute("aria-label", "Hide");
        timer = setTimeout(hide, HIDE_AFTER);
      } catch (err) { if (err.message !== "auth") toast("Could not reveal secret", "error"); }
    });
  });

  // ---------------------------------------------------------------- favourites
  $$("form.fav-form").forEach((form) => form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("button", form);
    try {
      const res = await fetch(form.action, { method: "POST", body: new FormData(form), headers: { "X-Requested-With": "fetch" }, credentials: "same-origin" });
      const data = await res.json();
      btn.classList.toggle("is-active", data.favorite);
      toast(data.favorite ? "Pinned to favourites" : "Removed from favourites", "info");
    } catch (err) { form.submit(); }
  }));

  // ---------------------------------------------------------------- password visibility in forms
  $$("[data-toggle-visibility]").forEach((btn) => btn.addEventListener("click", () => {
    const input = $(btn.dataset.toggleVisibility);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.innerHTML = icon(show ? "eye-off" : "eye");
  }));

  // ---------------------------------------------------------------- strength meter
  const strengthUrl = document.body.dataset.strengthUrl;
  function attachMeter(input) {
    const meter = $(`[data-meter-for="${input.id}"]`);
    if (!meter || !strengthUrl) return;
    const bar = $(".meter", meter), label = $("[data-meter-label]", meter), hint = $("[data-meter-hint]", meter);
    let t;
    const update = () => {
      clearTimeout(t);
      t = setTimeout(async () => {
        if (!input.value) { bar.dataset.score = ""; label.textContent = "Strength"; hint.textContent = ""; return; }
        try {
          const s = await post(strengthUrl, { password: input.value });
          bar.dataset.score = s.score;
          label.textContent = `${s.label} · ${s.entropy} bits`;
          hint.textContent = s.feedback[0] || "Looks great.";
        } catch (e) { /* ignore */ }
      }, 160);
    };
    input.addEventListener("input", update);
    input.vaultUpdateMeter = update;
    update();
  }
  $$("input[data-strength]").forEach(attachMeter);

  // ---------------------------------------------------------------- generate into field
  const generateUrl = document.body.dataset.generateUrl;
  $$("[data-generate-into]").forEach((btn) => btn.addEventListener("click", async () => {
    const input = $(btn.dataset.generateInto);
    try {
      const data = await post(generateUrl, { length: 20 });
      input.value = data.password;
      input.type = "text";
      input.dispatchEvent(new Event("input"));
      toast("Strong password generated", "success");
    } catch (e) { toast("Could not generate password", "error"); }
  }));

  // ---------------------------------------------------------------- confirm modal
  const modal = $("#confirm-modal");
  $$("[data-confirm]").forEach((btn) => btn.addEventListener("click", (e) => {
    if (!modal || typeof modal.showModal !== "function") { if (!confirm(btn.dataset.confirm)) e.preventDefault(); return; }
    e.preventDefault();
    $("[data-modal-text]", modal).textContent = btn.dataset.confirm;
    $("[data-modal-title]", modal).textContent = btn.dataset.confirmTitle || "Are you sure?";
    const ok = $("[data-modal-ok]", modal);
    ok.onclick = () => { modal.close(); btn.closest("form").submit(); };
    modal.showModal();
  }));
  $$("[data-modal-cancel]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));

  // ---------------------------------------------------------------- generator page
  const gen = $("#generator");
  if (gen) {
    const out = $("#gen-value", gen), meter = $("#gen-meter .meter", gen), label = $("#gen-label", gen);
    const lengthInput = $("#gen-length", gen), lengthOut = $("#gen-length-out", gen);
    const wordsInput = $("#gen-words", gen), wordsOut = $("#gen-words-out", gen);
    let mode = "password";
    const esc = (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] || c);
    const paint = (pw) => pw.split("").map((c) => /\d/.test(c) ? `<span class="d">${c}</span>` : /[^A-Za-z0-9]/.test(c) ? `<span class="s">${esc(c)}</span>` : c).join("");
    const history = [];
    const historyEl = $("#gen-history", gen);
    const opts = () => ({
      mode,
      length: +lengthInput.value,
      words: +wordsInput.value,
      lowercase: $("#opt-lower", gen).checked,
      uppercase: $("#opt-upper", gen).checked,
      digits: $("#opt-digits", gen).checked,
      symbols: $("#opt-symbols", gen).checked,
      exclude_ambiguous: $("#opt-ambiguous", gen).checked,
      separator: $("#opt-sep", gen).value,
      capitalize: $("#opt-cap", gen).checked,
      add_number: $("#opt-num", gen).checked,
    });
    const run = async () => {
      try {
        const data = await post(generateUrl, opts());
        out.dataset.value = data.password;
        out.innerHTML = paint(data.password);
        meter.dataset.score = data.strength.score;
        label.textContent = `${data.strength.label} · ${data.strength.entropy} bits of entropy`;
        history.unshift(data.password); history.splice(6);
        historyEl.innerHTML = history.map((p) => `<button type="button" class="chip mono truncate" style="max-width:100%" data-h="${p.replace(/"/g, "&quot;")}">${p.replace(/[&<>"]/g, esc)}</button>`).join("");
      } catch (e) { toast("Could not generate password", "error"); }
    };
    $$(".seg button", gen).forEach((b) => b.addEventListener("click", () => {
      mode = b.dataset.mode;
      $$(".seg button", gen).forEach((x) => x.classList.toggle("is-active", x === b));
      $$("[data-mode-panel]", gen).forEach((p) => { p.hidden = p.dataset.modePanel !== mode; });
      run();
    }));
    lengthInput.addEventListener("input", () => { lengthOut.textContent = lengthInput.value; run(); });
    wordsInput.addEventListener("input", () => { wordsOut.textContent = wordsInput.value; run(); });
    $$("input[type=checkbox], select", gen).forEach((i) => i.addEventListener("change", run));
    $("#gen-refresh", gen).addEventListener("click", run);
    $("#gen-copy", gen).addEventListener("click", () => copyText(out.dataset.value, "Password copied"));
    historyEl.addEventListener("click", (e) => { const b = e.target.closest("[data-h]"); if (b) copyText(b.dataset.h, "Copied from history"); });
    run();
  }

  // ---------------------------------------------------------------- auto-lock countdown
  const lock = $("[data-lock-seconds]");
  if (lock) {
    const total = +lock.dataset.lockSeconds;
    let deadline = Date.now() + total * 1000;
    const out = $("strong", lock);
    // Any successful request to the server refreshes the session, so reset then.
    window.vaultResetLock = () => { deadline = Date.now() + total * 1000; };
    const tick = () => {
      const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      out.textContent = `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
      if (left === 0) { const f = $("#logout-form"); if (f) f.submit(); return; }
      setTimeout(tick, 1000);
    };
    tick();
  }
})();
