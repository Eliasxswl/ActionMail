const state = { overview: null, selected: null, dirty: false };
const $ = (selector) => document.querySelector(selector);

function node(tag, className, value) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (value !== undefined) item.textContent = value;
  return item;
}

async function readJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

function text(value) { return value === null || value === undefined || value === "" ? "—" : String(value); }

function metaRow(label, value) {
  const row = node("div", "meta-row");
  row.append(node("span", "meta-label", label), node("span", "meta-value", text(value)));
  return row;
}

function renderList() {
  const list = $("#case-list");
  list.replaceChildren();
  const filter = $("#filter").value;
  const cases = state.overview.cases.filter((item) => {
    if (filter === "unreviewed") return !item.reviewed;
    if (filter === "status-mismatch") return item.status_correct === false;
    if (filter === "action") return item.predicted_status === "action";
    if (filter === "external") return item.category === "external_content";
    return true;
  });
  for (const item of cases) {
    const button = node("button", `case-item${item.case_id === state.selected ? " active" : ""}`);
    button.type = "button";
    if (item.case_id === state.selected) button.setAttribute("aria-current", "true");
    const top = node("span", "case-item-top");
    top.append(node("span", "case-id", item.case_id));
    top.append(node("span", `case-state ${item.reviewed ? "reviewed" : item.status_correct === false ? "mismatch" : ""}`, item.reviewed ? "Reviewed" : item.status_correct === false ? "Check" : "Pending"));
    button.append(top, node("span", "case-subject", item.subject || "(No subject)"));
    button.addEventListener("click", () => loadCase(item.case_id));
    list.append(button);
  }
  $("#progress").textContent = `${state.overview.cases.filter((item) => item.reviewed).length} / ${state.overview.cases.length} reviewed`;
}

function sourceBlock(label, sourceId, content, external = false, headers = null, readByModel = false) {
  const block = node("section", `source-block${external ? " external" : ""}`);
  const title = node("div", "source-title");
  title.append(node("span", "", label), node("span", "source-id", sourceId));
  if (external) title.append(node("span", "external-note", readByModel ? "Read by model" : "Not read by model"));
  block.append(title);
  if (headers) {
    const metadata = node("div", "metadata thread-metadata");
    metadata.append(metaRow("From", headers.sender || "unknown"), metaRow("To", headers.recipients || "unknown"));
    metadata.append(metaRow("From address", headers.sender_addresses.length ? headers.sender_addresses.join(", ") : "not provided in source"));
    metadata.append(metaRow("To address", headers.recipient_addresses.length ? headers.recipient_addresses.join(", ") : "not provided in source"));
    metadata.append(metaRow("Cc", headers.cc || "none shown"));
    if (headers.cc) metadata.append(metaRow("Cc address", headers.cc_addresses.length ? headers.cc_addresses.join(", ") : "not provided in source"));
    if (headers.subject) metadata.append(metaRow("Subject", headers.subject));
    block.append(metadata);
  }
  block.append(node("pre", "source-text", content || "(Empty)"));
  return block;
}

function definition(list, label, value) {
  list.append(node("dt", "", label), node("dd", "", text(value)));
}

function decisionBlock(title, decision) {
  const block = node("section", "decision");
  const heading = node("div", "decision-heading");
  heading.append(node("h3", "", title), node("span", `pill status-${decision?.status || "error"}`, decision?.status?.replaceAll("_", " ") || "error"));
  block.append(heading);
  if (!decision) return block;
  const reason = decision.reason || decision.review_reason || decision.explanation?.text;
  if (reason) {
    const list = node("dl"); definition(list, "Reason", reason); block.append(list);
  }
  const addQuotes = (evidence, parent) => {
    if (!evidence?.length) return;
    const quotes = node("ul", "quote-list");
    for (const e of evidence) {
      const entry = node("li"); entry.append(node("strong", "", e.source_id), node("span", "", e.quote)); quotes.append(entry);
    }
    parent.append(quotes);
  };
  addQuotes(decision.evidence?.length ? decision.evidence : decision.explanation?.evidence, block);
  const actions = decision.actions || (decision.action ? [{text: decision.action, deadline: decision.deadline, evidence: []}] : []);
  for (const [index, action] of actions.entries()) {
    const actionBlock = node("div", "action-row");
    actionBlock.append(node("strong", "", `${index + 1}. ${action.text}`));
    if (action.deadline) actionBlock.append(metaRow("Deadline", action.deadline));
    if (action.evidence?.length) {
      const details = node("details"); details.append(node("summary", "", "Action evidence")); addQuotes(action.evidence, details); actionBlock.append(details);
    }
    block.append(actionBlock);
  }
  return block;
}
function selectField(key, label, hint, value, disabled) {
  const wrap = node("div", "review-field");
  const caption = node("label", "", label);
  caption.htmlFor = key;
  const select = node("select");
  select.id = key;
  for (const [choice, title] of [["", "Not reviewed"], ["correct", "Yes"], ["incorrect", "No"], ["uncertain", "Unsure"]]) {
    const option = node("option", "", title);
    option.value = choice;
    select.append(option);
  }
  select.value = value || "";
  select.disabled = disabled;
  select.addEventListener("change", markDirty);
  wrap.append(caption, node("span", "review-hint", hint), select);
  return wrap;
}

function markDirty() {
  state.dirty = true;
  $("#save-status").textContent = "Unsaved changes";
}

function renderCase(data) {
  const main = $("#main");
  main.replaceChildren();
  const header = node("div", "case-header");
  const title = node("div");
  title.append(node("div", "muted", data.case_id), node("h2", "", data.email.subject || "(No subject)"));
  header.append(title);
  main.append(header);
  const beneficiary = node("section", "beneficiary");
  beneficiary.append(node("span", "beneficiary-label", "Finding tasks for"), node("strong", "beneficiary-address", data.email.target_recipient));
  main.append(beneficiary);

  const emailCard = node("section", "card email-card");
  const synthetic = ["authored", "authored_eml"].includes(data.email.source_kind);
  const metadata = node("div", "metadata");
  metadata.append(metaRow("From", data.email.sender), metaRow("To", data.email.to_recipients.join(", ")),
    metaRow("Cc", data.email.cc_recipients.join(", ") || "None"),
    metaRow(synthetic ? "Test fixture time" : "Received at", data.email.received_at || "Unknown in source"));
  emailCard.append(node("h3", "", synthetic ? "Email · synthetic test" : "Email · dataset source"), metadata,
    sourceBlock("Newest message", "body", data.email.body));
  for (const part of data.email.thread) {
    const details = node("details", "mail-detail");
    details.append(node("summary", "", `Earlier message · ${part.subject || part.source_id}`),
      sourceBlock("Older message", part.source_id, part.text, false, part));
    emailCard.append(details);
  }
  for (const source of data.external_sources) {
    const details = node("details", "mail-detail");
    details.append(node("summary", "", `${source.name} · ${source.read_by_model ? "Sent to model" : "Preview for you only — not sent to model"}`));
    if (source.original_attachment_url) {
      const link = node("a", "attachment-link", "Open original attachment");
      link.href = source.original_attachment_url; link.target = "_blank"; link.rel = "noopener";
      details.append(link);
    }
    details.append(sourceBlock("Attachment or page content", source.source_id, source.text, true, null, source.read_by_model));
    emailCard.append(details);
  }
  main.append(emailCard);

  const tabs = node("section", "card tabs-card");
  const tabbar = node("div", "tabbar"); tabbar.setAttribute("role", "tablist");
  const panels = node("div", "tab-panels");
  const addTab = (label, panel, active=false) => {
    const button = node("button", "tab-button", label); button.type = "button";
    button.setAttribute("role", "tab"); button.setAttribute("aria-selected", String(active));
    panel.hidden = !active; panel.setAttribute("role", "tabpanel");
    button.addEventListener("click", () => {
      for (const p of panels.children) p.hidden = true;
      for (const b of tabbar.children) b.setAttribute("aria-selected", "false");
      panel.hidden = false; button.setAttribute("aria-selected", "true");
    });
    tabbar.append(button); panels.append(panel);
  };
  const review = data.review || {};
  const assessment = (key, label, value, disabled=false) => {
    const wrap = node("section", "assessment-inline");
    wrap.append(node("h3", "", "Your assessment"), selectField(key, "Pass", "", value, disabled));
    return wrap;
  };
  const modelPanel = node("div");
  if (data.prediction) modelPanel.append(decisionBlock("Model result", data.prediction));
  else modelPanel.append(node("p", "", "No model result yet."));
  const shownReason = data.prediction?.reason || data.prediction?.review_reason || data.prediction?.explanation?.text;
  const validationNotes = [...new Set([...data.validation_errors, ...(data.error ? [data.error] : [])])]
    .filter(message => message !== shownReason);
  if (validationNotes.length) modelPanel.append(node("p", "validation-note", validationNotes.join("; ")));
  if (data.investigation) {
    const diagnosis = node("section", "investigation");
    diagnosis.append(node("h3", "", "Checked by ActionMail"), node("p", "", data.investigation.finding));
    if (data.investigation.offline_recheck) {
      diagnosis.append(node("p", "muted", "Offline recheck of the saved response · no new model call · original run unchanged"),
        decisionBlock("After evidence alignment", data.investigation.offline_recheck));
    }
    modelPanel.append(diagnosis);
  }
  modelPanel.append(assessment("model_pass", "Model", review.model_pass || "", !data.prediction));
  addTab("Model", modelPanel, true);

  const goldPanel = node("div");
  goldPanel.append(decisionBlock("Reference answer", data.gold));
  if (data.annotation_note) goldPanel.append(node("p", "context-note", data.annotation_note));
  goldPanel.append(assessment("gold_label", "Reference", review.gold_label ?? (data.reference_review_state === "approved" ? "correct" : data.prior_gold_review?.gold_label ?? "")));
  addTab("Reference", goldPanel);

  const readingPanel = node("div");
  readingPanel.append(node("h3", "", "What the model actually received"));
  const sent = data.external_sources.filter(s => s.read_by_model);
  readingPanel.append(node("p", "", sent.length ? `External content sent: ${sent.map(s => s.name).join(", ")}.` : "No attachment or page content was sent to the model in this run."));
  for (const choice of data.workflow_trace?.source_plan || []) {
    const entry = node("section", "reading-choice");
    entry.append(node("strong", "", `${choice.source_id} · ${choice.relevance}`), node("p", "", choice.reason));
    for (const e of choice.evidence || []) entry.append(sourceBlock("Evidence", e.source_id, e.quote));
    readingPanel.append(entry);
  }
  if (data.workflow_trace?.read_failures?.length) readingPanel.append(node("p", "validation-note", data.workflow_trace.read_failures.join("; ")));
  const trace = node("details"); trace.append(node("summary", "", "Technical details"),
    node("pre", "", JSON.stringify(data.workflow_trace, null, 2))); readingPanel.append(trace);
  addTab("Reading", readingPanel);

  const rawPanel = node("div");
  rawPanel.append(node("h3", "", "Saved model replies"), node("pre", "source-text", data.raw_model_response || "No reply saved."));
  addTab("Raw reply", rawPanel);
  tabs.append(tabbar, panels);
  const notes = node("div", "review-field notes-field");
  const caption = node("label", "", "Notes (optional)"); caption.htmlFor = "note";
  const note = node("textarea"); note.id = "note"; note.maxLength = 2000; note.value = review.note || "";
  note.addEventListener("input", markDirty); notes.append(caption, note); tabs.append(notes);
  const saveRow = node("div", "save-row");
  const save = node("button", "primary", "Save assessment"); save.type = "button"; save.addEventListener("click", saveReview);
  const status = node("span", "", review.updated_at_utc ? "Saved" : "Not saved"); status.id = "save-status";
  saveRow.append(save, status); tabs.append(saveRow); main.append(tabs);
}
async function loadCase(caseId) {
  if (state.dirty && !window.confirm("Discard unsaved assessment changes?")) return;
  state.dirty = false;
  state.selected = caseId;
  renderList();
  $("#case-list .active")?.scrollIntoView({ block: "nearest", inline: "nearest" });
  $("#main").replaceChildren(node("div", "empty-state", "Loading case…"));
  try {
    const data = await readJson(`/api/cases/${encodeURIComponent(caseId)}`);
    if (state.selected === caseId) renderCase(data);
  } catch (error) {
    $("#main").replaceChildren(node("div", "empty-state", error.message));
  }
}

async function saveReview() {
  const review = { gold_label: $("#gold_label").value, model_pass: $("#model_pass").value, note: $("#note").value };
  try {
    const result = await readJson(`/api/cases/${encodeURIComponent(state.selected)}/review`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(review),
    });
    state.dirty = false;
    const item = state.overview.cases.find((entry) => entry.case_id === state.selected);
    item.reviewed = true;
    renderList();
    $("#save-status").textContent = `Saved ${new Date(result.review.updated_at_utc).toLocaleTimeString()}`;
  } catch (error) {
    $("#save-status").textContent = `Save failed: ${error.message}`;
  }
}

async function start() {
  try {
    state.overview = await readJson("/api/cases");
    $("#run-meta").textContent = `${state.overview.model} · ${state.overview.run_id} · ${state.overview.manifest}`;
    $("#filter").addEventListener("change", renderList);
    renderList();
    const requested = new URLSearchParams(window.location.search).get("case");
    const first = state.overview.cases.find((item) => item.case_id === requested) || state.overview.cases[0];
    if (first) loadCase(first.case_id);
  } catch (error) {
    $("#main").replaceChildren(node("div", "empty-state", error.message));
  }
}

start();
