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
  heading.append(node("h3", "", title), node("span", `pill status-${decision ? decision.status : "error"}`, decision ? decision.status.replaceAll("_", " ") : "error"));
  block.append(heading);
  if (!decision) return block;
  const list = node("dl");
  if (Array.isArray(decision.actions)) {
    definition(list, "Action count", decision.actions.length);
  } else {
    definition(list, "Action", decision.action);
    definition(list, "Deadline", decision.deadline);
  }
  if (decision.review_reason) definition(list, "Reason", decision.review_reason);
  block.append(list);
  if (Array.isArray(decision.actions)) {
    for (const [index, action] of decision.actions.entries()) {
      const actionBlock = node("div", "source-block");
      actionBlock.append(node("strong", "", `${index + 1}. ${action.text}`));
      actionBlock.append(metaRow("Type", action.kind), metaRow("Deadline", action.deadline));
      const quotes = node("ul", "quote-list");
      for (const evidence of action.evidence || []) {
        const entry = node("li");
        entry.append(node("strong", "", evidence.source_id), node("span", "", evidence.quote));
        quotes.append(entry);
      }
      actionBlock.append(quotes);
      block.append(actionBlock);
    }
  }
  if (decision.evidence && decision.evidence.length) {
    const quotes = node("ul", "quote-list");
    for (const evidence of decision.evidence) {
      const entry = node("li");
      entry.append(node("strong", "", evidence.source_id), node("span", "", evidence.quote));
      quotes.append(entry);
    }
    block.append(quotes);
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
  title.append(node("div", "muted", `${data.case_id}  /  ${data.category.replaceAll("_", " ")}`), node("h2", "", data.email.subject || "(No subject)"));
  const pills = node("div", "pill-row");
  const statusText = data.status_correct === null ? "Reference pending review" : data.status_correct ? "Status matches gold" : "Status differs from gold";
  pills.append(node("span", `pill ${data.status_correct === false ? "warning" : "good"}`, statusText));
  if (data.action_count_match !== null && data.action_count_match !== undefined) pills.append(node("span", `pill ${data.action_count_match ? "good" : "warning"}`, data.action_count_match ? "Action count matches" : "Action count differs"));
  if (data.validation_errors.length) pills.append(node("span", "pill warning", `${data.validation_errors.length} validation issue(s)`));
  header.append(title, pills);
  main.append(header);

  const grid = node("div", "grid");
  const sourceCard = node("section", "card");
  sourceCard.append(node("h3", "", "Original email"));
  const metadata = node("div", "metadata");
  metadata.append(
    metaRow("Reviewing for", data.email.target_recipient),
    metaRow("From", data.email.sender || "unknown"),
    metaRow("To", data.email.to_recipients.join(", ") || "none shown"),
    metaRow("Cc", data.email.cc_recipients.join(", ") || "none shown"),
  );
  if (data.email.received_at) metadata.append(metaRow("Received at", data.email.received_at));
  sourceCard.append(metadata, sourceBlock("Newest message", "body", data.email.body));
  for (const thread of data.email.thread) sourceCard.append(sourceBlock("Earlier message", thread.source_id, thread.text, false, thread));
  for (const source of data.external_sources) sourceCard.append(sourceBlock(source.name, source.source_id, source.text, true, null, source.read_by_model));
  grid.append(sourceCard);

  const right = node("div", "stack");
  const comparison = node("section", "card comparison");
  comparison.append(decisionBlock(`Reference label used in this run (${data.manifest_name})`, data.gold));
  if (data.prior_gold_review?.gold_label) {
    comparison.append(node("p", "muted", `Your earlier gold review: ${data.prior_gold_review.gold_label}${data.prior_gold_review.note ? ` — ${data.prior_gold_review.note}` : ""}`));
  }
  if (data.annotation_note) comparison.append(node("p", "muted", `Annotation note: ${data.annotation_note}`));
  if (data.multi_action_draft) {
    const draft = data.multi_action_draft;
    comparison.append(node("p", "muted", "Proposed v2 reference — pending your review. It is not included in correctness scores."));
    comparison.append(decisionBlock("Draft multi-action reference", {
      status: draft.proposed_status, actions: draft.candidate_actions, review_reason: draft.review_reason,
    }));
    if (draft.annotation_note) comparison.append(node("p", "muted", draft.annotation_note));
  }
  if (data.revised_gold) comparison.append(decisionBlock("Current revised label (not used to score this run)", data.revised_gold));
  const predictionTitle = state.overview.model === "rules-v1" ? "Rule baseline (prediction)" : "Model result (prediction)";
  comparison.append(decisionBlock(predictionTitle, data.prediction));
  if (data.validation_errors.length || data.error) {
    const errors = node("ul", "error-list");
    for (const message of [...data.validation_errors, ...(data.error ? [data.error] : [])]) errors.append(node("li", "", message));
    comparison.append(errors);
  }
  if (data.reference_review_state) {
    comparison.append(node("p", "muted", `Reference: ${data.reference_review_state}. Review candidate gold before scoring.`));
  }
  if (data.workflow_trace || data.source_expectations) {
    const trace = node("details");
    trace.append(node("summary", "", "Source selection, coverage and provenance"),
      node("pre", "", JSON.stringify({expected_sources: data.source_expectations, expected_locations: data.expected_evidence_locations, ...data.workflow_trace}, null, 2)));
    comparison.append(trace);
  }
  if (data.raw_model_response) {
    const details = node("details");
    details.append(node("summary", "", "Raw model response"), node("pre", "", data.raw_model_response));
    comparison.append(details);
  }
  right.append(comparison);

  const reviewCard = node("section", "card");
  reviewCard.append(node("h3", "", "Your assessment"));
  const review = data.review || {};
  const hasAction = data.prediction && data.prediction.status === "action";
  const isMulti = Array.isArray(data.prediction?.actions);
  const fields = node("div", "review-grid");
  fields.append(
    selectField("action_meaning", "Is the proposed action useful and faithful?", "Judge meaning in context, not exact wording.", review.action_meaning, !hasAction || isMulti),
    selectField("evidence_support", "Does the evidence support that action?", "An exact quote can still support the wrong recipient or obligation.", review.evidence_support, !hasAction || isMulti),
    selectField("gold_label", data.multi_action_draft ? "Is the draft multi-action reference reasonable?" : "Is the reference label reasonable?", "Pending v2 drafts are not scored as gold.", review.gold_label ?? (data.multi_action_draft ? "" : data.prior_gold_review?.gold_label), false),
  );
  if (data.prediction && data.reference_review_state) {
    fields.append(
      selectField("action_completeness", "Are all requested tasks represented?", "Check omissions and extra tasks across the complete message.", review.action_completeness, false),
      selectField("deadline_correct", "Are the action deadlines correct?", "Check relative dates, timezone and source conflicts.", review.deadline_correct, false),
      selectField("source_selection", "Were the relevant sources selected?", "Compare the source plan with the email and source expectations.", review.source_selection, false),
      selectField("content_coverage", "Was enough decisive content read?", "Check offsets, failures and budget explanations.", review.content_coverage, false),
    );
  }
  if (isMulti) {
    for (const [index, action] of data.prediction.actions.entries()) {
      const checks = review.action_checks?.[index] || {};
      const group = node("div", "source-block");
      group.append(node("strong", "", `${index + 1}. ${action.text}`));
      group.append(
        selectField(`action_meaning_${index}`, "Action meaning", "Is this individual task faithful to the email?", checks.action_meaning, false),
        selectField(`evidence_support_${index}`, "Evidence support", "Does the cited source support this task?", checks.evidence_support, false),
      );
      fields.append(group);
    }
  }
  const noteWrap = node("div", "review-field");
  const noteLabel = node("label", "", "Notes (optional)");
  noteLabel.htmlFor = "note";
  const note = node("textarea");
  note.id = "note";
  note.maxLength = 2000;
  note.value = review.note || "";
  note.addEventListener("input", markDirty);
  noteWrap.append(noteLabel, note);
  fields.append(noteWrap);
  reviewCard.append(fields);
  const saveRow = node("div", "save-row");
  const save = node("button", "primary", "Save assessment");
  save.type = "button";
  save.addEventListener("click", saveReview);
  saveRow.append(save, node("span", "", review.updated_at_utc ? "Saved previously" : data.prior_gold_review ? "Gold judgment carried over; model result not reviewed" : "Not saved"));
  saveRow.lastChild.id = "save-status";
  reviewCard.append(saveRow);
  right.append(reviewCard);
  grid.append(right);
  main.append(grid);
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
  const review = {
    action_meaning: $("#action_meaning").value,
    evidence_support: $("#evidence_support").value,
    gold_label: $("#gold_label").value,
    note: $("#note").value,
  };
  for (const field of ["action_completeness", "deadline_correct", "source_selection", "content_coverage"]) {
    if ($(`#${field}`)) review[field] = $(`#${field}`).value;
  }
  const meaningChecks = [...document.querySelectorAll('[id^="action_meaning_"]')];
  if (meaningChecks.length) review.action_checks = meaningChecks.map((field, index) => ({
    action_meaning: field.value,
    evidence_support: $(`#evidence_support_${index}`).value,
  }));
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
