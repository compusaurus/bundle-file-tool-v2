"use strict";

const pathParts = window.location.pathname.split("/").filter(Boolean);
const token = pathParts[1] || "";
const sessionBase = `/session/${encodeURIComponent(token)}/`;
const terminalStates = new Set(["succeeded", "failed", "cancelled"]);

const state = {
  mode: "bundle",
  busy: false,
  activeJob: null,
  after: 0,
  plan: null,
  overrides: [],
  decisionFilter: "included",
  selectedDecision: null,
  selectionCheck: null,
  bundleCheck: null,
  checkedFingerprint: "",
  entries: [],
  upload: null,
  skin: "studio",
};

const progressRuntime = {
  bundle: { phaseStartedAt: performance.now(), lastEvent: null },
  unbundle: { phaseStartedAt: performance.now(), lastEvent: null },
};

const progressViews = Object.fromEntries(["bundle", "unbundle"].map((mode) => [
  mode,
  new window.NodeThermXWeb.WebThermometer(byId(`${mode}-progress`), {
    cancellable: true,
    showDetails: true,
    labels: { cancel: "Cancel operation" },
    onCancel: () => cancelActiveJob(),
    onError: ({ error }) => activity(mode, "Progress display failed", error.message, "Failed"),
  }),
]));

const modeHelp = {
  bundle: "Plan, check, and create a bundle from local source files.",
  unbundle: "Check, validate, and safely extract an existing bundle.",
};

function byId(id) { return document.getElementById(id); }
function text(id, value) { byId(id).textContent = String(value); }

function presentPath(targetId, value, previewId = null) {
  const field = byId(targetId);
  const path = String(value || "");
  field.value = path;
  field.title = path;
  window.requestAnimationFrame(() => { field.scrollLeft = field.scrollWidth; });
  if (previewId) {
    const preview = byId(previewId);
    preview.textContent = path || "No source selected.";
    preview.title = path;
    preview.classList.toggle("has-path", Boolean(path));
  }
}

function syncPathPresentation(targetId, previewId = null) {
  presentPath(targetId, byId(targetId).value, previewId);
}

function replaySplash() {
  const current = byId("startup-splash");
  if (!current) return;
  const replacement = current.cloneNode(false);
  replacement.removeAttribute("hidden");
  current.replaceWith(replacement);
}

async function applySkin(skin, persist = false) {
  const selected = skin === "midnight" ? "midnight" : "studio";
  state.skin = selected;
  document.documentElement.dataset.skin = selected;
  document.querySelectorAll(".skin-button").forEach((button) => {
    const active = button.dataset.skin === selected;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  if (!persist) return;
  try {
    await request("api/preferences/skin", {
      method: "POST", body: JSON.stringify({ skin: selected }),
    });
  } catch (error) {
    activity(state.mode, "Appearance changed for this session",
      `The ${selected} skin is active, but could not be remembered: ${error.message}`, "Ready");
  }
}

function humanBytes(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  let amount = Math.max(0, Number(value));
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) { amount /= 1024; unit += 1; }
  return `${amount >= 10 || unit === 0 ? amount.toFixed(0) : amount.toFixed(1)} ${units[unit]}`;
}

async function request(relative, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-BFT-Session", token);
  if (options.body && !(options.body instanceof Blob)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${sessionBase}${relative}`, { ...options, headers, cache: "no-store" });
  const payload = await response.json().catch(() => ({ error: "INVALID_RESPONSE", message: "The local service returned an unreadable response." }));
  if (!response.ok) throw new Error(payload.message || payload.error || `Request failed (${response.status}).`);
  return payload;
}

function activity(mode, title, message, phase = "Idle") {
  text(`${mode}-activity-title`, title);
  text(`${mode}-activity-message`, message || "");
  byId(`${mode}-activity-message`).title = String(message || "");
  text(`${mode}-activity-phase`, phase);
}

function resetProgress(mode) {
  progressRuntime[mode] = { phaseStartedAt: performance.now(), lastEvent: null };
  progressViews[mode].reset();
}

function progressDocument(mode, event, job = {}) {
  const runtime = progressRuntime[mode];
  const now = performance.now();
  if (runtime.lastEvent?.phase !== event.phase) runtime.phaseStartedAt = now;
  runtime.lastEvent = event;

  const rawCurrent = Number(event.current);
  const rawTotal = Number(event.total);
  const determinate = event.mode === "determinate"
    && Number.isFinite(rawTotal) && rawTotal > 0;
  const total = determinate ? rawTotal : null;
  const current = Math.max(0, Number.isFinite(rawCurrent) ? rawCurrent : 0);
  const boundedCurrent = determinate ? Math.min(current, total) : current;
  const terminalOutcome = {
    succeeded: "completed",
    failed: "failed",
    cancelled: "cancelled",
  }[job.state] || null;
  const cancellationState = job.state === "cancelled"
    ? "cancelled"
    : (job.cancel_requested ? "requested" : "active");

  return {
    state_version: "1.1",
    mode: determinate ? "determinate" : "indeterminate",
    current: boundedCurrent,
    total,
    percent: determinate ? (boundedCurrent / total) * 100 : null,
    label: event.message || `Working on ${event.phase || "operation"}`,
    unit: event.unit || "items",
    phase: event.phase || job.state || null,
    elapsed_s: Math.max(0, (now - runtime.phaseStartedAt) / 1000),
    promoted_from: null,
    cancellation_state: cancellationState,
    terminal_outcome: terminalOutcome,
  };
}

function setProgress(mode, event, job = {}) {
  if (!event) {
    resetProgress(mode);
    return;
  }
  progressViews[mode].render(progressDocument(mode, event, job));
  if (!terminalStates.has(job.state)) {
    activity(mode, "Operation in progress", event.message || `Working on ${event.phase}`, event.phase || "Working");
  }
}

function setBusy(value, mode = state.mode) {
  state.busy = value;
  document.querySelectorAll("button, input, select").forEach((control) => {
    if (control.id !== "stop-server" && !control.hasAttribute("data-always-enabled")
        && !control.classList.contains("thermx__cancel")) control.disabled = value;
  });
  refreshActionStates();
}

function refreshActionStates() {
  if (state.busy) return;
  document.querySelectorAll("button, input, select").forEach((control) => {
    if (!control.classList.contains("thermx__cancel")) control.disabled = false;
  });
  byId("decision-search").disabled = !state.plan;
  byId("include-override").disabled = !state.selectedDecision;
  byId("exclude-override").disabled = !state.selectedDecision;
  byId("check-selection").disabled = !state.plan;
  const needsConfirmation = Boolean(state.plan?.capacity_estimate?.requires_confirmation);
  byId("create-bundle").disabled = !state.plan
    || (needsConfirmation && !byId("large-confirm").checked);
  const hasBundle = Boolean(byId("bundle-path").value.trim() || state.upload);
  byId("check-bundle").disabled = !hasBundle;
  byId("validate-bundle").disabled = !hasBundle;
  byId("entry-search").disabled = !state.entries.length;
  byId("extract-bundle").disabled = !(state.bundleCheck?.valid)
    || state.checkedFingerprint !== currentBundleFingerprint()
    || !byId("extract-output").value.trim();
}

async function startJob(action, payload, mode, onSuccess) {
  if (state.busy) return;
  resetProgress(mode);
  setBusy(true, mode);
  const queuedEvent = {
    mode: "indeterminate", current: 0, total: null, unit: "items",
    phase: "queued", message: "Waiting for the local service…",
  };
  activity(mode, "Starting operation", queuedEvent.message, "Queued");
  try {
    const job = await request(`api/jobs/${action}`, { method: "POST", body: JSON.stringify(payload) });
    state.activeJob = { id: job.id, mode };
    state.after = 0;
    setProgress(mode, queuedEvent, job);
    await pollJob(onSuccess);
  } catch (error) {
    state.activeJob = null;
    setProgress(mode, progressRuntime[mode].lastEvent || queuedEvent, { state: "failed" });
    setBusy(false, mode);
    activity(mode, "Operation failed", error.message, "Failed");
  }
}

async function pollJob(onSuccess) {
  const active = state.activeJob;
  if (!active) return;
  try {
    const job = await request(`api/jobs/${active.id}?after=${state.after}`);
    if (!state.activeJob || state.activeJob.id !== active.id) return;
    state.after = job.next_after || state.after;
    const latest = job.events?.length
      ? job.events[job.events.length - 1]
      : progressRuntime[active.mode].lastEvent;
    if (latest) setProgress(active.mode, latest, job);
    if (!terminalStates.has(job.state)) {
      window.setTimeout(() => pollJob(onSuccess), 180);
      return;
    }
    state.activeJob = null;
    setBusy(false, active.mode);
    if (job.state === "succeeded") {
      onSuccess(job.result || {});
    } else {
      activity(active.mode, job.state === "cancelled" ? "Operation cancelled" : "Operation failed",
        job.error?.message || "The operation did not complete.", job.state);
    }
  } catch (error) {
    state.activeJob = null;
    setProgress(active.mode, progressRuntime[active.mode].lastEvent, { state: "failed" });
    setBusy(false, active.mode);
    activity(active.mode, "Connection interrupted", error.message, "Failed");
  }
}

async function cancelActiveJob() {
  if (!state.activeJob) return;
  const active = state.activeJob;
  try {
    await request(`api/jobs/${active.id}/cancel`, { method: "POST", body: "{}" });
    active.cancelRequested = true;
    setProgress(active.mode, progressRuntime[active.mode].lastEvent, {
      state: "running", cancel_requested: true,
    });
    activity(active.mode, "Cancelling…", "The current phase will stop at its next safe cancellation point.", "Cancelling");
  } catch (error) {
    activity(active.mode, "Cancellation failed", error.message, "Running");
    throw error;
  }
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".mode-button").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  byId("bundle-mode").classList.toggle("hidden", mode !== "bundle");
  byId("unbundle-mode").classList.toggle("hidden", mode !== "unbundle");
  text("mode-help", modeHelp[mode]);
}

function addOption(select, value, label = value) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  select.append(option);
}

function addPreset(preset) {
  const label = document.createElement("label");
  label.className = "check-row";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.value = preset.name;
  const caption = document.createElement("span");
  caption.textContent = preset.label;
  label.append(input, caption);
  byId("preset-list").append(label);
}

function selectedPresets() {
  if (byId("auto-preset").checked) return null;
  return [...byId("preset-list").querySelectorAll("input:checked")].map((input) => input.value);
}

function planPayload() {
  return {
    source: byId("source-path").value.trim(),
    output_path: byId("bundle-output").value.trim() || null,
    presets: selectedPresets(),
  };
}

function renderPlan(plan) {
  state.plan = plan;
  state.selectionCheck = null;
  state.selectedDecision = null;
  const counts = Object.fromEntries(Object.entries(plan.counts || {})
    .map(([name, count]) => [name.toLowerCase(), count]));
  text("count-included", counts.included || 0);
  text("count-excluded", counts.excluded || 0);
  text("count-blocked", counts.blocked || 0);
  text("plan-estimate", humanBytes(plan.capacity_estimate?.output_bytes ?? plan.estimated_bytes));
  for (const button of byId("decision-filters").querySelectorAll("button")) {
    const filter = button.dataset.filter;
    button.querySelector("span").textContent = filter === "all" ? plan.decisions.length : (counts[filter] || 0);
  }
  const needsConfirmation = Boolean(plan.capacity_estimate?.requires_confirmation);
  byId("large-confirm-row").classList.toggle("hidden", !needsConfirmation);
  byId("large-confirm").checked = false;
  text("selection-integrity", "Not checked");
  byId("bundle-findings").replaceChildren();
  byId("bundle-empty").classList.add("hidden");
  byId("decision-table-wrap").classList.remove("hidden");
  renderDecisions();
  renderInspector();
  activity("bundle", "Selection planned",
    `${plan.decisions.length} paths decided in generation ${plan.generation}.`, "Complete");
  refreshActionStates();
}

function invalidateSourcePlan() {
  if (!state.plan) {
    refreshActionStates();
    return;
  }
  state.plan = null;
  state.overrides = [];
  state.selectionCheck = null;
  state.selectedDecision = null;
  text("count-included", 0);
  text("count-excluded", 0);
  text("count-blocked", 0);
  text("plan-estimate", "—");
  byId("decision-filters").querySelectorAll("button span").forEach((count) => { count.textContent = "0"; });
  byId("decision-rows").replaceChildren();
  byId("decision-table-wrap").classList.add("hidden");
  byId("bundle-empty").classList.remove("hidden");
  byId("large-confirm-row").classList.add("hidden");
  byId("large-confirm").checked = false;
  text("selection-integrity", "Not checked");
  byId("bundle-findings").replaceChildren();
  renderInspector();
  activity("bundle", "Source changed", "Plan the selection again before checking or creating a bundle.", "Ready");
  refreshActionStates();
}

function renderDecisions() {
  if (!state.plan) return;
  const query = byId("decision-search").value.trim().toLocaleLowerCase();
  const matches = state.plan.decisions.filter((decision) =>
    (state.decisionFilter === "all" || decision.state.toLowerCase() === state.decisionFilter)
    && (!query || decision.path.toLocaleLowerCase().includes(query)));
  const shown = matches.slice(0, 500);
  const body = byId("decision-rows");
  body.replaceChildren();
  for (const decision of shown) {
    const row = document.createElement("tr");
    row.className = `state-${decision.state.toLowerCase()}`;
    if (state.selectedDecision?.path === decision.path) row.classList.add("selected");
    for (const [index, value] of [decision.path, decision.state, decision.detail || decision.winning_rule || "Default", humanBytes(decision.size)].entries()) {
      const cell = document.createElement("td");
      cell.textContent = value;
      cell.title = value;
      if (index === 0) cell.className = "path-cell";
      row.append(cell);
    }
    row.addEventListener("click", () => {
      state.selectedDecision = decision;
      renderDecisions();
      renderInspector();
      refreshActionStates();
    });
    body.append(row);
  }
  text("decision-note", matches.length > shown.length
    ? `Showing the first ${shown.length.toLocaleString()} of ${matches.length.toLocaleString()} matching paths.`
    : `${matches.length.toLocaleString()} matching path${matches.length === 1 ? "" : "s"}.`);
}

function renderInspector() {
  const decision = state.selectedDecision;
  text("selected-path", decision ? `${decision.path} · ${decision.state}` : "Choose a planned path to inspect its rule chain.");
  byId("selected-path").title = decision?.path || "";
  const chain = byId("decision-chain");
  chain.replaceChildren();
  if (!decision) return;
  if (!decision.chain?.length) {
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = decision.detail || "No matching rule; the base action decided this path.";
    chain.append(note);
  }
  for (const entry of decision.chain || []) {
    const item = document.createElement("div");
    item.className = entry.won ? "chain-item winner" : "chain-item";
    const heading = document.createElement("strong");
    heading.textContent = `[${entry.layer}] ${entry.rule}${entry.won ? " · winner" : ""}`;
    const detail = document.createElement("span");
    detail.textContent = `${entry.action} ${entry.pattern}`;
    item.append(heading, detail);
    chain.append(item);
  }
}

function overridePattern() {
  const path = state.selectedDecision?.path;
  if (!path) return "";
  return byId("override-scope").value === "subtree" ? `${path.replace(/\/$/, "")}/**` : path;
}

function applyOverride(action) {
  const pattern = overridePattern();
  if (!state.plan || !pattern) return;
  state.overrides = state.overrides.filter((entry) => entry[1] !== pattern);
  state.overrides.push([action, pattern]);
  startJob("replan", { plan_id: state.plan.plan_id, overrides: state.overrides }, "bundle", (result) => {
    renderPlan(result.plan);
    activity("bundle", "Override applied", `${action === "include" ? "Included" : "Excluded"} ${pattern} for this session.`, "Complete");
  });
}

function renderFindings(containerId, check) {
  const container = byId(containerId);
  container.replaceChildren();
  const findings = check?.findings || [];
  if (!findings.length) {
    const pass = document.createElement("p");
    pass.className = "finding-pass";
    pass.textContent = "No integrity findings.";
    container.append(pass);
    return;
  }
  for (const finding of findings) {
    const item = document.createElement("article");
    item.className = `finding severity-${finding.severity || "info"}`;
    const heading = document.createElement("strong");
    heading.textContent = finding.summary || finding.code;
    const detail = document.createElement("p");
    detail.textContent = [finding.path, finding.detail, finding.remediation].filter(Boolean).join(" · ");
    item.append(heading, detail);
    container.append(item);
  }
}

function renderCheck(check, mode, containerId, integrityId) {
  text(integrityId, check.status || (check.valid ? "passed" : "blocked"));
  renderFindings(containerId, check);
  activity(mode, check.valid ? "Check complete" : "Check blocked",
    `${check.file_count || 0} files checked · ${check.blocking_count || 0} blockers · ${check.warning_count || 0} warnings.`, "Complete");
}

function bundleSourcePayload() {
  if (state.upload) return { upload_id: state.upload.id };
  return { bundle_path: byId("bundle-path").value.trim() };
}

function currentBundleFingerprint() {
  return state.upload ? `upload:${state.upload.id}` : `path:${byId("bundle-path").value.trim()}`;
}

function renderEntries(entries, check) {
  state.entries = entries || [];
  text("entry-count", state.entries.length);
  text("entry-size", humanBytes(check?.total_bytes));
  text("bundle-profile-value", check?.profile || "unknown");
  byId("unbundle-empty").classList.add("hidden");
  byId("entry-table-wrap").classList.remove("hidden");
  renderEntryRows();
  refreshActionStates();
}

function renderEntryRows() {
  const query = byId("entry-search").value.trim().toLocaleLowerCase();
  const matches = state.entries.filter((entry) => !query || entry.path.toLocaleLowerCase().includes(query));
  const shown = matches.slice(0, 500);
  const body = byId("entry-rows");
  body.replaceChildren();
  for (const entry of shown) {
    const row = document.createElement("tr");
    for (const [index, value] of [entry.path, humanBytes(entry.size), entry.binary ? "base64" : (entry.encoding || "text"), entry.eol || "—"].entries()) {
      const cell = document.createElement("td");
      cell.textContent = value;
      cell.title = value;
      if (index === 0) cell.className = "path-cell";
      row.append(cell);
    }
    body.append(row);
  }
  text("entry-note", matches.length > shown.length
    ? `Showing the first ${shown.length.toLocaleString()} of ${matches.length.toLocaleString()} entries.`
    : `${matches.length.toLocaleString()} matching entr${matches.length === 1 ? "y" : "ies"}.`);
}

function invalidateBundleCheck() {
  state.bundleCheck = null;
  state.checkedFingerprint = "";
  state.entries = [];
  text("bundle-integrity", "Not checked");
  byId("unbundle-findings").replaceChildren();
  byId("entry-table-wrap").classList.add("hidden");
  byId("unbundle-empty").classList.remove("hidden");
  text("entry-count", 0);
  text("entry-size", "—");
  text("bundle-profile-value", "—");
  refreshActionStates();
}

function runBundleCheck() {
  const payload = { ...bundleSourcePayload(), profile: byId("unbundle-profile").value || null };
  startJob("check-bundle", payload, "unbundle", (result) => {
    state.bundleCheck = result.check;
    state.checkedFingerprint = currentBundleFingerprint();
    renderCheck(result.check, "unbundle", "unbundle-findings", "bundle-integrity");
    renderEntries(result.entries, result.check);
  });
}

async function uploadBundle() {
  const file = byId("bundle-upload").files[0];
  if (!file || state.busy) return;
  setBusy(true, "unbundle");
  activity("unbundle", "Uploading bundle", `${file.name} · ${humanBytes(file.size)}`, "Upload");
  try {
    if (state.upload) await request(`api/uploads/${state.upload.id}`, { method: "DELETE" });
    const result = await request("api/uploads", {
      method: "POST",
      headers: { "X-BFT-Filename": encodeURIComponent(file.name) },
      body: file,
    });
    state.upload = result.upload;
    presentPath("bundle-path", "");
    text("upload-status", `Temporary upload: ${state.upload.name} · ${humanBytes(state.upload.size)}`);
    invalidateBundleCheck();
    setBusy(false, "unbundle");
    runBundleCheck();
  } catch (error) {
    setBusy(false, "unbundle");
    activity("unbundle", "Upload failed", error.message, "Failed");
  }
}

function chooseBrowserPath(kind, title, initialPath, defaultName) {
  const dialog = byId("path-picker");
  let current = "", parent = "", separator = "/", pending = false;
  text("path-picker-title", title);
  byId("path-picker-name-label").hidden = kind === "folder";
  byId("path-picker-name").value = defaultName;
  return new Promise((resolve) => {
    async function navigate(path) {
      if (pending) return;
      pending = true;
      byId("path-picker-select").disabled = true;
      text("path-picker-error", "Loading folder...");
      try {
        const listing = await request("api/filesystem", {method: "POST", body: JSON.stringify({path})});
        current = listing.path; parent = listing.parent; separator = listing.separator;
        byId("path-picker-folder").value = current;
        byId("path-picker-entries").replaceChildren();
        for (const entry of listing.entries) {
          if (kind === "folder" && !entry.directory) continue;
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = `${entry.directory ? "Folder: " : "File: "}${entry.name}`;
          button.addEventListener("click", () => {
            if (entry.directory) navigate(entry.path);
            else byId("path-picker-name").value = entry.name;
          });
          byId("path-picker-entries").append(button);
        }
        text("path-picker-error", listing.truncated ? "Showing the first 1,000 entries. Enter a folder path to navigate directly." : "");
      } catch (error) { text("path-picker-error", error.message); }
      finally { pending = false; byId("path-picker-select").disabled = !current; }
    }
    function finish(path) { dialog.close(); resolve({path}); }
    dialog.oncancel = (event) => { event.preventDefault(); finish(""); };
    byId("path-picker-cancel").onclick = () => finish("");
    byId("path-picker-up").onclick = () => navigate(parent);
    byId("path-picker-navigation").onsubmit = (event) => {
      event.preventDefault(); navigate(byId("path-picker-folder").value);
    };
    byId("path-picker-select").onclick = () => {
      if (!current || pending) return;
      const name = byId("path-picker-name").value.trim();
      if (kind !== "folder" && (!name || /[\\/]/.test(name) || name === "." || name === "..")) {
        text("path-picker-error", "Enter a file name without folder separators."); return;
      }
      finish(kind === "folder" ? current : `${current.replace(/[\\/]$/, "")}${separator}${name}`);
    };
    dialog.showModal();
    navigate(initialPath);
  });
}

async function choosePath(kind, targetId, title, defaultName = "") {
  if (state.busy) return "";
  const mode = targetId.startsWith("bundle-path") || targetId.startsWith("extract") ? "unbundle" : "bundle";
  activity(mode, "Waiting for selection", "Choose a path to continue.", "Browse");
  try {
    const initialPath = byId(targetId).value.trim() || (targetId === 'bundle-output' ? state.bundleOutputDir || '' : '');
    const result = state.pathPicker === "browser" ? await chooseBrowserPath(kind, title, initialPath, defaultName) : await request("api/dialogs", {
      method: "POST",
      body: JSON.stringify({ kind, title, initial_path: initialPath, default_name: defaultName }),
    });
    if (result.path) {
      presentPath(targetId, result.path, targetId === "source-path" ? "source-path-preview" : null);
      byId(targetId).dispatchEvent(new Event("input"));
      activity(mode, "Path selected", result.path, "Ready");
      return result.path;
    } else {
      activity(mode, "Selection cancelled", "No path was changed.", "Ready");
      return "";
    }
  } catch (error) {
    activity(mode, "Chooser unavailable", error.message, "Failed");
    return "";
  }
}

async function ensurePlanTargetsOutput(outputPath) {
  if (!state.plan || state.plan.output_path === outputPath) return Boolean(state.plan);
  let replanned = false;
  const confirmed = byId("large-confirm").checked;
  await startJob("replan", {
    plan_id: state.plan.plan_id,
    overrides: state.overrides,
    output_path: outputPath,
  }, "bundle", (result) => {
    renderPlan(result.plan);
    if (confirmed && result.plan.capacity_estimate?.requires_confirmation) {
      byId("large-confirm").checked = true;
      refreshActionStates();
    }
    replanned = true;
    activity("bundle", "Output added to selection plan",
      "The chosen bundle path is protected from being included as an input.", "Complete");
  });
  return replanned;
}

async function bootstrap() {
  const response = await fetch(`${sessionBase}api/bootstrap`, { cache: "no-store" });
  if (!response.ok) throw new Error("The local BFT service did not accept this session.");
  const data = await response.json();
  const splash = byId('startup-splash');
  for (const [key, value] of Object.entries(data.splash || {})) {
    if (key !== 'error') splash.setAttribute(key, String(value));
  }
  byId('replay-splash').disabled = data.splash?.enabled !== 'true';
  if (data.splash?.enabled === 'true') replaySplash();
  text("version", `v${data.version}`);
  state.pathPicker = data.path_picker;
  if (data.platform === "linux") document.title = "Bundle File Tool — Linux Web Workspace";
  for (const profile of data.profiles) {
    addOption(byId("bundle-profile"), profile);
    addOption(byId("unbundle-profile"), profile);
  }
  byId("bundle-profile").value = data.default_profile;
  data.presets.forEach(addPreset);
  applySkin(data.defaults.web_skin || "studio");
  presentPath("source-path", data.defaults.source_path || "", "source-path-preview");
  presentPath("bundle-path", data.defaults.bundle_path || "");
  presentPath('extract-output', data.defaults.extract_output_dir || '');
  state.bundleOutputDir = data.defaults.bundle_output_dir || '';
  byId("overwrite-policy").value = data.defaults.overwrite_policy || "prompt";
  byId('add-headers').checked = Boolean(data.defaults.add_headers);
  byId('dry-run').checked = Boolean(data.defaults.dry_run);
  setMode(data.defaults.default_mode === 'unbundle' ? 'unbundle' : 'bundle');
  activity("bundle", "Web service connected", "Plan a selection to begin.", "Ready");
  refreshActionStates();
}

document.querySelectorAll(".mode-button").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
document.querySelectorAll(".skin-button").forEach((button) => button.addEventListener("click", () => applySkin(button.dataset.skin, true)));
byId("replay-splash").addEventListener("click", replaySplash);
byId("plan-button").addEventListener("click", () => {
  const payload = planPayload();
  if (!payload.source) {
    activity("bundle", "Source required", "Choose or enter a local folder or file.", "Ready");
    return;
  }
  state.overrides = [];
  startJob("plan", payload, "bundle", (result) => renderPlan(result.plan));
});
byId("check-selection").addEventListener("click", () => {
  if (!state.plan) return;
  startJob("check-selection", { plan_id: state.plan.plan_id, profile: byId("bundle-profile").value }, "bundle", (result) => {
    state.selectionCheck = result.check;
    renderCheck(result.check, "bundle", "bundle-findings", "selection-integrity");
  });
});
byId("create-bundle").addEventListener("click", async () => {
  if (!state.plan) return;
  let outputPath = byId("bundle-output").value.trim();
  if (!outputPath) {
    outputPath = await choosePath("save", "bundle-output", "Save bundle as", "bundle.txt");
    if (!outputPath) return;
  }
  if (!(await ensurePlanTargetsOutput(outputPath))) return;
  startJob("create", {
    plan_id: state.plan.plan_id,
    output_path: outputPath,
    profile: byId("bundle-profile").value,
    confirm_large: byId("large-confirm").checked,
  }, "bundle", (result) => {
    state.selectionCheck = result.check;
    renderCheck(result.check, "bundle", "bundle-findings", "selection-integrity");
    activity("bundle", "Bundle created and verified",
      `${result.bundle.file_count} files · ${humanBytes(result.bundle.bytes)} · ${result.bundle.output_path}`, "Complete");
  });
});
byId("include-override").addEventListener("click", () => applyOverride("include"));
byId("exclude-override").addEventListener("click", () => applyOverride("exclude"));
byId("large-confirm").addEventListener("change", refreshActionStates);
byId("decision-search").addEventListener("input", renderDecisions);
byId("decision-filters").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-filter]");
  if (!button) return;
  state.decisionFilter = button.dataset.filter;
  byId("decision-filters").querySelectorAll("button").forEach((item) => item.classList.toggle("active", item === button));
  renderDecisions();
});
byId("bundle-upload").addEventListener("change", uploadBundle);
byId("bundle-path").addEventListener("input", () => {
  syncPathPresentation("bundle-path");
  state.upload = null;
  text("upload-status", "No temporary upload.");
  invalidateBundleCheck();
});
byId("unbundle-profile").addEventListener("change", invalidateBundleCheck);
byId("check-bundle").addEventListener("click", runBundleCheck);
byId("validate-bundle").addEventListener("click", () => {
  startJob("validate", { ...bundleSourcePayload(), profile: byId("unbundle-profile").value || null }, "unbundle", (result) => {
    const validation = result.validation;
    const findings = [
      ...(validation.errors || []).map((message) => ({ severity: "error", summary: message })),
      ...(validation.warnings || []).map((message) => ({ severity: "warning", summary: message })),
    ];
    renderFindings("unbundle-findings", { findings });
    activity("unbundle", validation.valid ? "Validation passed" : "Validation failed",
      `${validation.file_count} files · ${validation.profile || "unknown profile"}.`, "Complete");
  });
});
byId("extract-bundle").addEventListener("click", () => {
  startJob("extract", {
    ...bundleSourcePayload(),
    output_dir: byId("extract-output").value.trim(),
    profile: byId("unbundle-profile").value || null,
    overwrite_policy: byId("overwrite-policy").value,
    add_headers: byId("add-headers").checked,
    dry_run: byId("dry-run").checked,
  }, "unbundle", (result) => {
    const extraction = result.extraction;
    activity("unbundle", byId("dry-run").checked ? "Dry run complete" : "Extraction complete",
      `${extraction.processed} processed · ${extraction.skipped} skipped · ${extraction.errors} errors · ${extraction.output_dir}`, "Complete");
  });
});
byId("extract-output").addEventListener("input", () => {
  syncPathPresentation("extract-output");
  refreshActionStates();
});
byId("entry-search").addEventListener("input", renderEntryRows);
byId("source-path").addEventListener("input", invalidateSourcePlan);
byId("source-path").addEventListener("input", () => syncPathPresentation("source-path", "source-path-preview"));
byId("browse-source-folder").addEventListener("click", () => choosePath("folder", "source-path", "Choose source folder"));
byId("browse-source-file").addEventListener("click", () => choosePath("file", "source-path", "Choose source file"));
byId("browse-bundle-output").addEventListener("click", () => choosePath("save", "bundle-output", "Save bundle as", "bundle.txt"));
byId("browse-bundle-path").addEventListener("click", () => choosePath("file", "bundle-path", "Choose bundle file"));
byId("browse-extract-output").addEventListener("click", () => choosePath("folder", "extract-output", "Choose extraction folder"));
byId("bundle-output").addEventListener("input", () => {
  syncPathPresentation("bundle-output");
  refreshActionStates();
});
byId("stop-server").addEventListener("click", async () => {
  try {
    await request("api/shutdown", { method: "POST", body: "{}" });
    document.body.classList.add("stopped");
    byId("stop-server").disabled = true;
    text("mode-help", "The local BFT web server has stopped. This page can be closed.");
  } catch (error) {
    text("mode-help", error.message);
  }
});

bootstrap().catch((error) => {
  activity("bundle", "Connection failed", error.message, "Failed");
  activity("unbundle", "Connection failed", error.message, "Failed");
});
