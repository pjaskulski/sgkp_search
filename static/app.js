"use strict";

const $ = id => document.getElementById(id);
const optionFields = ["tom", "powiat_ujednolicony", "typ_punktu_osadniczego", "gubernia_ujednolicona"];
const CHAT_HISTORY_TURNS = 8;
const CHAT_HISTORY_ANSWER_CHARS = 5000;
const state = { page: 1, hasNext: false, entry: null, highlight: null, request: 0, gminas: [], chatBusy: false,
  chatController: null, chatGeneration: 0, chatHistory: [], exportTurns: [] };

function setText(node, value) { node.textContent = value == null ? "" : String(value); }
function element(tag, value, className) {
  const node = document.createElement(tag);
  if (value !== undefined) setText(node, value);
  if (className) node.className = className;
  return node;
}
function externalLink(label, url) {
  const node = element("a", label);
  node.href = url;
  node.target = "_blank";
  node.rel = "noopener noreferrer";
  return node;
}
async function api(url, options) {
  const response = await fetch(url, options);
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Nieprawidłowa odpowiedź serwera"); }
  if (!response.ok) throw new Error(data.error || "Usługa jest niedostępna");
  return data;
}
function selectedMode() { return document.querySelector('input[name="mode"]:checked').value; }
function localityOnly() { return document.querySelector('input[name="locality"]:checked').value === "only"; }
function activeFilters() {
  const selected = {};
  for (const id of ["tom", "powiat_ujednolicony"]) {
    if ($(id).value) selected[id] = $(id).value;
  }
  if (localityOnly()) {
    selected.jest_miejscowoscia = "true";
    if ($("kingdom-only").checked) selected["królestwo_polskie"] = "true";
    for (const id of ["typ_punktu_osadniczego", "gmina", "gubernia_ujednolicona"]) {
      if ($(id).value) selected[id] = $(id).value;
    }
  }
  return selected;
}
function updateFilterToggleLabel() {
  const count = Object.keys(activeFilters()).length;
  const expanded = $("search-filter-slot").classList.contains("expanded");
  $("mobile-filter-toggle").firstChild.textContent = (expanded ? "Ukryj filtry" : "Pokaż filtry") + (count ? " (" + count + ")" : "") + " ";
  setText($("assistant-filter-hint"), count ? count + " aktywne" : "Ogranicz zakres odpowiedzi");
}
function updateLocalityUi(clear = false) {
  const enabled = localityOnly();
  $("locality-options").disabled = !enabled;
  $("locality-hint").hidden = enabled;
  if (!enabled && clear) {
    $("kingdom-only").checked = false;
    for (const id of ["typ_punktu_osadniczego", "gmina", "gubernia_ujednolicona", "gmina-search"]) $(id).value = "";
    renderGminaChoices();
  }
  updateFilterToggleLabel();
}
function modeUi() {
  $("ratio-line").classList.toggle("visible", selectedMode() === "hybrid");
}
function viewFromHash() {
  return ["#konwersacja", "#asystent"].includes(location.hash) ? "konwersacja" : "wyszukiwanie";
}
function switchView(view, updateUrl = true) {
  const assistant = view === "konwersacja" || view === "asystent";
  $("search-view").hidden = assistant;
  $("assistant-view").hidden = !assistant;
  $("tab-search").setAttribute("aria-selected", String(!assistant));
  $("tab-assistant").setAttribute("aria-selected", String(assistant));
  (assistant ? $("assistant-filter-slot") : $("search-filter-slot")).append($("filter-panel"));
  if (updateUrl) history.replaceState(null, "", location.pathname + location.search + "#" + (assistant ? "konwersacja" : "wyszukiwanie"));
}
function queryParams(page) {
  const params = new URLSearchParams({ q: $("query").value.trim(), mode: selectedMode(), page: String(page) });
  if (selectedMode() === "hybrid") params.set("ratio", String(Number($("ratio").value) / 100));
  for (const [key, value] of Object.entries(activeFilters())) params.set(key, value);
  return params;
}
function makeEmpty(title, message) {
  const box = element("div", undefined, "empty-state");
  box.append(element("span", "⌕", "empty-symbol"), element("h3", title), element("p", message));
  box.firstChild.setAttribute("aria-hidden", "true");
  return box;
}
function snippetNode(hit) {
  const paragraph = element("p");
  const chars = Array.from(hit.snippet);
  let cursor = 0;
  for (const range of hit.snippet_highlights || []) {
    if (!Array.isArray(range) || range.length !== 2) continue;
    const [start, end] = range;
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < cursor || end <= start || end > chars.length) continue;
    paragraph.append(document.createTextNode(chars.slice(cursor, start).join("")));
    paragraph.append(element("mark", chars.slice(start, end).join(""), "snippet-match"));
    cursor = end;
  }
  paragraph.append(document.createTextNode(chars.slice(cursor).join("")));
  return paragraph;
}
function resultCard(hit) {
  const card = element("article", undefined, "result-card");
  const title = element("h3");
  const open = element("button", hit.nazwa || hit.ID);
  open.type = "button";
  open.addEventListener("click", () => openEntry(hit.ID));
  title.append(open);
  card.append(title);
  const meta = element("div", undefined, "result-meta");
  meta.append(element("span", "Tom " + (hit.tom || "—") + " · s. " + (hit.strona || "—")));
  if (hit.powiat_ujednolicony) meta.append(element("span", "Powiat " + hit.powiat_ujednolicony));
  if (hit.parent_id) meta.append(element("span", "Element hasła zbiorczego" + (hit.nr ? " · nr " + hit.nr : "")));
  if (hit.url_skanu) meta.append(externalLink("Skan strony ↗", hit.url_skanu));
  card.append(meta);
  if (Array.isArray(hit.typ_punktu_osadniczego) && hit.typ_punktu_osadniczego.length) {
    const tags = element("div", undefined, "result-meta");
    tags.style.marginTop = "10px";
    for (const value of hit.typ_punktu_osadniczego) tags.append(element("span", value, "tag"));
    card.append(tags);
  }
  if (hit.snippet) card.append(snippetNode(hit));
  return card;
}
async function search(page = 1) {
  const params = queryParams(page);
  if (!params.get("q")) return;
  const current = ++state.request;
  setText($("status"), "Wyszukiwanie…");
  $("status").classList.remove("error");
  $("results").replaceChildren();
  $("pagination").hidden = true;
  try {
    const data = await api("api/v1/search?" + params);
    if (current !== state.request) return;
    state.page = data.page;
    state.hasNext = data.has_next;
    $("prev").disabled = data.page <= 1;
    $("next").disabled = !data.has_next;
    setText($("page-label"), "Strona " + data.page);
    if (data.hits.length) {
      const start = (data.page - 1) * data.page_size + 1;
      const end = start + data.hits.length - 1;
      setText($("status"), "Wyniki " + start + "–" + end + " · około " + data.estimated_total_hits + " trafień");
      for (const hit of data.hits) $("results").append(resultCard(hit));
      $("pagination").hidden = false;
    } else {
      setText($("status"), "Brak wyników");
      $("results").append(makeEmpty("Nie znaleziono haseł", "Zmień słowa zapytania albo ograniczenia w panelu filtrów."));
    }
    history.replaceState(null, "", location.pathname + "?" + params + (location.hash || "#wyszukiwanie"));
  } catch (error) {
    if (current !== state.request) return;
    setText($("status"), error.message);
    $("status").classList.add("error");
    $("results").append(makeEmpty("Nie można wyświetlić wyników", "Sprawdź połączenie z usługą i spróbuj ponownie."));
  }
}
function renderGminaChoices() {
  const select = $("gmina");
  const selected = select.value;
  const query = $("gmina-search").value.trim().toLocaleLowerCase("pl");
  const matched = query ? state.gminas.filter(value => value.toLocaleLowerCase("pl").includes(query)) : state.gminas;
  const visible = matched.slice(0, 100);
  if (selected && !visible.includes(selected)) visible.unshift(selected);
  select.replaceChildren();
  const all = element("option", "Wszystkie gminy");
  all.value = "";
  select.append(all);
  for (const value of visible) {
    const option = element("option", value);
    option.value = value;
    select.append(option);
  }
  select.value = selected && visible.includes(selected) ? selected : "";
  setText($("gmina-hint"), query
    ? "Znaleziono " + matched.length + " nazw; na liście widać pierwsze 100."
    : "Wpisz fragment nazwy, potem wybierz gminę z listy.");
}
function fillSelect(id, values) {
  const select = $(id);
  for (const value of values) {
    const option = element("option", value);
    option.value = value;
    select.append(option);
  }
}
async function loadFilterOptions() {
  try {
    const data = await api("api/v1/filter-options");
    const options = data.options || {};
    for (const id of optionFields) fillSelect(id, options[id] || []);
    state.gminas = (options.gmina || []).filter(value =>
      typeof value === "string" && /^\p{L}/u.test(value.trimStart()));
    renderGminaChoices();
  } catch {
    fillSelect("tom", Array.from({length: 16}, (_, index) => String(index + 1).padStart(2, "0")));
    setText($("filter-options-status"), "Nie udało się wczytać list filtrów. Wyszukiwanie nadal jest dostępne.");
  }
}
function clearFilters() {
  for (const id of [...optionFields, "gmina-search", "gmina"]) $(id).value = "";
  $("kingdom-only").checked = false;
  document.querySelector('input[name="locality"][value="all"]').checked = true;
  updateLocalityUi();
  renderGminaChoices();
  updateFilterToggleLabel();
  if ($("query").value.trim()) search(1);
}

function appendAnswerInline(target, text) {
  let plain = "";
  const flush = () => {
    if (plain) target.append(document.createTextNode(plain));
    plain = "";
  };
  for (let index = 0; index < text.length;) {
    if (text[index] === "\\" && index + 1 < text.length && /[\\`*_\[\]()]/.test(text[index + 1])) {
      plain += text[index + 1];
      index += 2;
      continue;
    }
    const link = text.slice(index).match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/);
    if (link) {
      flush();
      target.append(externalLink(link[1], link[2]));
      index += link[0].length;
      continue;
    }
    let matched = false;
    for (const [marker, tag] of [["**", "strong"], ["__", "strong"], ["*", "em"], ["_", "em"], ["`", "code"]]) {
      if (!text.startsWith(marker, index)) continue;
      const end = text.indexOf(marker, index + marker.length);
      if (end <= index + marker.length) continue;
      const content = text.slice(index + marker.length, end);
      if (/^\s|\s$/.test(content)) continue;
      flush();
      const node = element(tag);
      if (tag === "code") setText(node, content);
      else appendAnswerInline(node, content);
      target.append(node);
      index = end + marker.length;
      matched = true;
      break;
    }
    if (!matched) plain += text[index++];
  }
  flush();
}
function renderAnswerMarkdown(target, raw) {
  target.replaceChildren();
  target.classList.add("rendered");
  let paragraph = [];
  let list = null;
  const flushParagraph = () => {
    if (!paragraph.length) return;
    const node = element("p");
    appendAnswerInline(node, paragraph.join(" "));
    target.append(node);
    paragraph = [];
  };
  for (const line of String(raw).replace(/\r\n?/g, "\n").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) { flushParagraph(); list = null; continue; }
    const item = line.match(/^\s{0,3}([-+*]|\d+[.)])\s+(.+)$/);
    if (item) {
      flushParagraph();
      const tag = /^\d/.test(item[1]) ? "ol" : "ul";
      if (!list || list.tagName.toLowerCase() !== tag) {
        list = element(tag);
        target.append(list);
      }
      const node = element("li");
      appendAnswerInline(node, item[2]);
      list.append(node);
      continue;
    }
    list = null;
    const heading = trimmed.match(/^#{1,3}\s+(.+)$/);
    if (heading) {
      flushParagraph();
      const node = element("h3");
      appendAnswerInline(node, heading[1]);
      target.append(node);
      continue;
    }
    paragraph.push(trimmed);
  }
  flushParagraph();
}
function renderEntry() {
  const entry = state.entry;
  setText($("entry-title"), entry.nazwa);
  setText($("entry-meta"), "ID: " + entry.ID + " · tom " + entry.tom + ", s. " + entry.strona + (entry.nr ? " · element nr " + entry.nr : ""));
  $("scan-link").hidden = !entry.url_skanu;
  if (entry.url_skanu) $("scan-link").href = entry.url_skanu;
  const localityType = entry.metadata.typ_punktu_osadniczego;
  const isLocality = Array.isArray(localityType) ? localityType.length > 0 : Boolean(localityType);
  const labels = {
    ...(isLocality ? {typ_punktu_osadniczego: "Typ miejscowości"} : {typ: "Typ"}),
    powiat_ujednolicony: "Powiat", gmina: "Gmina", gubernia_ujednolicona: "Gubernia",
    królestwo_polskie: "Królestwo Polskie", opis_lokalizacji: "Opis lokalizacji",
    parafia_katolicka: "Parafia katolicka", obiekty_sakralne: "Obiekty sakralne",
    przemysłowe: "Przemysł", młyny: "Młyny", archeo: "Archeologia", warianty_nazw: "Warianty nazw"
  };
  $("entry-fields-list").replaceChildren();
  for (const [key, label] of Object.entries(labels)) {
    let value = entry.metadata[key];
    if (value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length)) continue;
    if (key === "warianty_nazw") value = value.map(item => item.wariant_nazwy || "").filter(Boolean);
    if (Array.isArray(value)) value = value.map(item => typeof item === "object" ? JSON.stringify(item) : String(item)).join(", ");
    else if (typeof value === "boolean") value = value ? "Tak" : "Nie";
    else if (typeof value === "object") value = JSON.stringify(value);
    $("entry-fields-list").append(element("dt", label), element("dd", String(value)));
  }
  $("entry-fields").hidden = !$("entry-fields-list").children.length;
  const content = $("entry-content");
  content.classList.toggle("plain-text", !entry.rendered_html);
  if (entry.rendered_html) {
    content.innerHTML = entry.rendered_html;
    for (const table of content.querySelectorAll("table")) {
      const scroller = element("div", undefined, "entry-table-scroll");
      table.replaceWith(scroller);
      scroller.append(table);
    }
  } else if (state.highlight && state.highlight[0] >= 0) {
    const chars = Array.from(entry.text);
    const [start, end] = state.highlight;
    content.replaceChildren(document.createTextNode(chars.slice(0, start).join("")),
      element("mark", chars.slice(start, end).join("")),
      document.createTextNode(chars.slice(end).join("")));
  } else setText(content, entry.text);
  $("parent-context").hidden = !entry.parent;
  if (entry.parent) {
    $("parent-context").replaceChildren(element("h3", "Hasło zbiorcze: " + entry.parent.nazwa));
    const button = element("button", "Otwórz hasło zbiorcze", "button button-outline");
    button.type = "button";
    button.addEventListener("click", () => openEntry(entry.parent.ID));
    $("parent-context").append(button);
  }
}
async function openEntry(id, start, end) {
  try {
    state.entry = await api("api/v1/entries/" + encodeURIComponent(id));
    state.highlight = Number.isInteger(start) && Number.isInteger(end) ? [start, end] : null;
    renderEntry();
    if (!$("entry-dialog").open) $("entry-dialog").showModal();
    if (state.highlight && !state.entry.rendered_html) $("entry-content").querySelector("mark")?.scrollIntoView({block: "center"});
  } catch (error) { window.alert(error.message); }
}
async function askChat(question, filters, history, answerNode, sourcesNode, statusNode, signal) {
  const response = await fetch("api/v1/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json", "Accept": "text/event-stream"},
    body: JSON.stringify({question, filters, history}), signal
  });
  if (!response.ok) {
    let data = {};
    try { data = await response.json(); } catch {}
    throw new Error(data.error || "Usługa konwersacji jest niedostępna");
  }
  if (!response.body) throw new Error("Brak strumienia odpowiedzi");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", complete = false, provider = "local", model = "", finalAnswer = null;
  while (true) {
    const {value, done} = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), {stream: !done}).replace(/\r\n/g, "\n");
    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) >= 0) {
      const event = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const type = event.match(/^event: (.+)$/m)?.[1];
      const raw = event.match(/^data: (.+)$/m)?.[1];
      if (!raw) continue;
      const data = JSON.parse(raw);
      if (type === "delta") answerNode.append(document.createTextNode(data.text));
      else if (type === "retry") {
        setText(answerNode, "");
        answerNode.classList.remove("rendered");
        setText(statusNode, "Odpowiedź przekroczyła początkowy limit. Generuję ją ponownie…");
      }
      else if (type === "fallback") {
        setText(answerNode, "");
        answerNode.classList.remove("rendered");
        sourcesNode.replaceChildren();
        setText(statusNode, "Model lokalny jest niedostępny. Korzystam z OpenAI…");
      }
      else if (type === "error") throw new Error(data.error || "Przerwano odpowiedź");
      else if (type === "answer") {
        complete = true;
        finalAnswer = data;
        provider = data.provider || "local";
        model = data.model || "";
        renderAnswerMarkdown(answerNode, data.answer);
        sourcesNode.replaceChildren();
        for (const source of data.sources || []) {
          const item = element("li");
          const location = [source.tom ? "tom " + source.tom : "", source.strona ? "s. " + source.strona : ""].filter(Boolean).join(", ");
          const button = element("button", "[" + source.citation + "] " + source.nazwa + (location ? " · " + location : ""));
          button.type = "button";
          button.addEventListener("click", () => openEntry(source.entry_id, source.start_offset, source.end_offset));
          item.append(button);
          if (source.url_skanu) item.append(externalLink("Skan ↗", source.url_skanu));
          sourcesNode.append(item);
        }
      }
    }
    if (done) break;
  }
  if (!complete) throw new Error("Odpowiedź została przerwana");
  return {...finalAnswer, provider, model};
}
function makeTurn(question) {
  const turn = element("article", undefined, "turn");
  turn.append(element("div", question, "question-bubble"));
  const card = element("div", undefined, "answer-card");
  card.append(element("h2", "Odpowiedź"));
  const status = element("p", "Szukam źródeł i przygotowuję odpowiedź…", "answer-status");
  const answer = element("div", undefined, "answer-text");
  const heading = element("p", "Źródła", "source-heading");
  heading.hidden = true;
  const sources = element("ol", undefined, "source-list");
  card.append(status, answer, heading, sources);
  turn.append(card);
  $("conversation").append(turn);
  return {turn, status, answer, heading, sources};
}
function clearChat() {
  state.chatGeneration++;
  state.chatController?.abort();
  state.chatController = null;
  state.chatBusy = false;
  state.chatHistory = [];
  state.exportTurns = [];
  $("chat-submit").disabled = false;
  $("export-pdf").disabled = true;
  $("conversation").replaceChildren();
  $("conversation-actions").hidden = true;
  $("chat-intro").hidden = false;
  $("question").value = "";
  $("question").focus();
}
async function exportChatPdf() {
  if (!state.exportTurns.length) return;
  const button = $("export-pdf");
  button.disabled = true;
  try {
    const response = await fetch("api/v1/chat/export", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({turns: state.exportTurns})
    });
    if (!response.ok) {
      let data = {};
      try { data = await response.json(); } catch {}
      throw new Error(data.error || "Nie udało się przygotować PDF");
    }
    const blob = await response.blob();
    const name = response.headers.get("Content-Disposition")?.match(/filename="?([\w.-]+)"?/)?.[1]
      || "sgkp-konwersacja.pdf";
    const url = URL.createObjectURL(blob);
    const link = element("a");
    link.href = url;
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (error) {
    window.alert(error.message);
  } finally {
    button.disabled = state.chatBusy || !state.exportTurns.length;
  }
}
async function submitChat(event) {
  event.preventDefault();
  if (state.chatBusy) return;
  const question = $("question").value.trim();
  if (!question) return;
  const generation = ++state.chatGeneration;
  const controller = new AbortController();
  state.chatController = controller;
  state.chatBusy = true;
  $("chat-submit").disabled = true;
  $("export-pdf").disabled = true;
  $("chat-intro").hidden = true;
  $("conversation-actions").hidden = false;
  const nodes = makeTurn(question);
  nodes.turn.scrollIntoView({behavior: "smooth", block: "start"});
  try {
    const result = await askChat(question, activeFilters(), state.chatHistory, nodes.answer, nodes.sources, nodes.status, controller.signal);
    if (generation !== state.chatGeneration) return;
    state.chatHistory.push({question, answer: result.answer.slice(0, CHAT_HISTORY_ANSWER_CHARS),
      source_ids: (result.sources || []).map(source => source.passage_id),
      source_names: (result.sources || []).map(source => source.nazwa)});
    state.chatHistory = state.chatHistory.slice(-CHAT_HISTORY_TURNS);
    state.exportTurns.push({question, answer: result.answer, provider: result.provider, model: result.model,
      sources: (result.sources || []).map(source => ({citation: source.citation, nazwa: source.nazwa,
        tom: source.tom, strona: source.strona}))});
    setText(nodes.status, result.provider === "openai"
      ? "Odpowiedź przygotowana przez OpenAI (" + result.model + ") po niedostępności modelu lokalnego."
      : "");
    nodes.heading.hidden = !nodes.sources.children.length;
    $("question").value = "";
  } catch (error) {
    if (generation !== state.chatGeneration) return;
    setText(nodes.status, error.message);
    nodes.status.classList.add("error");
  } finally {
    if (generation === state.chatGeneration) {
      state.chatBusy = false;
      state.chatController = null;
      $("chat-submit").disabled = false;
      $("export-pdf").disabled = !state.exportTurns.length;
    }
  }
}
async function initialize() {
  $("tab-search").addEventListener("click", () => switchView("wyszukiwanie"));
  $("tab-assistant").addEventListener("click", () => switchView("konwersacja"));
  $("tab-search").parentElement.addEventListener("keydown", event => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const current = $("tab-assistant").getAttribute("aria-selected") === "true" ? "konwersacja" : "wyszukiwanie";
    const next = event.key === "Home" ? "wyszukiwanie" : event.key === "End" ? "konwersacja" : (current === "konwersacja" ? "wyszukiwanie" : "konwersacja");
    switchView(next);
    $(next === "konwersacja" ? "tab-assistant" : "tab-search").focus();
  });
  window.addEventListener("hashchange", () => switchView(viewFromHash(), false));
  $("open-help").addEventListener("click", () => $("help-dialog").showModal());
  $("close-help").addEventListener("click", () => $("help-dialog").close());
  $("search-form").addEventListener("submit", event => { event.preventDefault(); search(1); });
  $("prev").addEventListener("click", () => search(state.page - 1));
  $("next").addEventListener("click", () => search(state.page + 1));
  $("clear-filters").addEventListener("click", clearFilters);
  $("mobile-filter-toggle").addEventListener("click", () => {
    const expanded = $("search-filter-slot").classList.toggle("expanded");
    $("mobile-filter-toggle").setAttribute("aria-expanded", String(expanded));
    updateFilterToggleLabel();
  });
  $("gmina-search").addEventListener("input", () => {
    const hadSelection = Boolean($("gmina").value);
    $("gmina").value = "";
    renderGminaChoices();
    updateFilterToggleLabel();
    if (hadSelection && $("query").value.trim()) search(1);
  });
  $("ratio").addEventListener("input", () => setText($("ratio-value"), $("ratio").value + "%"));
  $("ratio").addEventListener("change", () => { if ($("query").value.trim()) search(1); });
  for (const input of document.querySelectorAll('input[name="mode"]')) input.addEventListener("change", () => { modeUi(); if ($("query").value.trim()) search(1); });
  for (const input of document.querySelectorAll('input[name="locality"]')) input.addEventListener("change", () => { updateLocalityUi(true); if ($("query").value.trim()) search(1); });
  for (const id of [...optionFields, "gmina", "kingdom-only"]) $(id).addEventListener("change", () => { updateFilterToggleLabel(); if ($("query").value.trim()) search(1); });
  $("close-dialog").addEventListener("click", () => $("entry-dialog").close());
  $("clear-chat").addEventListener("click", clearChat);
  $("export-pdf").addEventListener("click", exportChatPdf);
  $("chat-form").addEventListener("submit", submitChat);
  $("question").addEventListener("keydown", event => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) { event.preventDefault(); $("chat-form").requestSubmit(); }
  });
  for (const button of document.querySelectorAll(".suggestion")) button.addEventListener("click", () => {
    $("question").value = button.textContent;
    $("chat-form").requestSubmit();
  });
  await loadFilterOptions();
  const params = new URLSearchParams(location.search);
  $("query").value = params.get("q") || "";
  const mode = params.get("mode");
  if (["text", "hybrid", "semantic"].includes(mode)) document.querySelector('input[name="mode"][value="' + mode + '"]').checked = true;
  if (params.get("ratio")) $("ratio").value = String(Math.round(Number(params.get("ratio")) * 100));
  setText($("ratio-value"), $("ratio").value + "%");
  modeUi();
  for (const id of optionFields) if (params.get(id)) $(id).value = params.get(id);
  if (params.get("gmina")) { $("gmina-search").value = params.get("gmina"); renderGminaChoices(); $("gmina").value = params.get("gmina"); }
  if (params.get("jest_miejscowoscia") === "true" || ["gmina", "gubernia_ujednolicona", "typ_punktu_osadniczego", "królestwo_polskie"].some(id => params.get(id))) {
    document.querySelector('input[name="locality"][value="only"]').checked = true;
  }
  $("kingdom-only").checked = params.get("królestwo_polskie") === "true";
  updateLocalityUi();
  switchView(viewFromHash(), false);
  if ($("query").value.trim()) search(Number(params.get("page")) || 1);
}
initialize();
