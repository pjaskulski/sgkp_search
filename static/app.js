"use strict";

const $ = id => document.getElementById(id);
const optionFields = ["tom", "powiat_ujednolicony", "typ_punktu_osadniczego", "gubernia_ujednolicona"];
const CHAT_HISTORY_TURNS = 8;
const CHAT_HISTORY_ANSWER_CHARS = 5000;
const THEME_STORAGE_KEY = "sgkp-theme";
const LANGUAGE_STORAGE_KEY = "sgkp-language";
const UI_COPY = {
  pl: {
    documentTitle: "SGKP — wyszukiwanie i konwersacja", brandName: "Słownik Geograficzny\nKrólestwa Polskiego",
    brandAria: "SGKP — przejdź do wyszukiwania", viewsAria: "Widoki aplikacji", languageAria: "Język interfejsu", themeToggleTitle: "Zmień motyw",
    searchPageTitle: "Wyszukiwanie w SGKP", chatPageTitle: "Konwersacja o treści SGKP",
    searchFiltersAria: "Filtry wyszukiwania", searchTab: "Wyszukiwanie", chatTab: "Konwersacja",
    help: "Pomoc", searchLabel: "Szukaj w słowniku", queryPlaceholder: "Nazwa miejscowości, osoba lub słowa z hasła",
    searchButton: "Wyszukaj", searchMode: "Tryb wyszukiwania", textMode: "Pełnotekstowe", hybridMode: "Hybrydowe",
    semanticMode: "Semantyczne", semanticShare: "Udział semantyki", mobileShowFilters: "Pokaż filtry",
    mobileHideFilters: "Ukryj filtry", narrowResults: "Zawęź wyniki", filters: "Filtry", clear: "Wyczyść",
    volume: "Tom", allVolumes: "Wszystkie tomy", district: "Powiat", allDistricts: "Wszystkie powiaty",
    entryScope: "Zakres haseł", allEntries: "Wszystkie hasła", placesOnly: "Tylko miejscowości",
    localityFilters: "Filtry miejscowości", localityAvailability: "Dostępne po wybraniu „Tylko miejscowości”.",
    kingdomOnly: "Tylko Królestwo Polskie", settlementType: "Typ miejscowości", allTypes: "Wszystkie typy",
    governorate: "Gubernia", allGovernorates: "Wszystkie gubernie", commune: "Gmina", findCommune: "Znajdź nazwę gminy",
    chooseCommune: "Wybierz gminę", allCommunes: "Wszystkie gminy", communeHint: "Wpisz fragment nazwy, potem wybierz gminę z listy.",
    catalog: "Katalog haseł", searchResults: "Wyniki wyszukiwania", startSearch: "Wpisz zapytanie, aby rozpocząć.",
    startByName: "Zacznij od nazwy lub tematu", enterQuery: "Wprowadź zapytanie w polu powyżej.",
    pagesLabel: "Strony wyników", previous: "← Poprzednia", next: "Następna →", sourceFilters: "Filtry źródeł",
    limitAnswer: "Ogranicz zakres odpowiedzi", exampleQuestions: "Przykładowe pytania",
    exampleSpas: "W jakich miejscowościach znajdowały się uzdrowiska?", exampleKingdom: "Czy Okuniew w powiecie warszawskim należał do Królestwa Polskiego?",
    exampleSettlements: "Jakie typy osad wymieniono w powiecie wileńskim?", exampleZawady: "Gdzie leżały Zawady w powiecie warszawskim?",
    exampleArchaeology: "Jakie znaleziska archeologiczne znajdowały się w miejscowościach powiatu warszawskiego?", exampleGlassworks: "W których miejscowościach znajdowały się huty szkła?",
    exampleOil: "Co słownik mówi o wydobyciu ropy naftowej w Borysławiu?", downloadPdf: "Pobierz PDF",
    clearConversation: "Wyczyść rozmowę", yourQuestion: "Twoje pytanie",
    questionPlaceholder: "Zapytaj o miejscowość, osobę lub zagadnienie opisane w słowniku…", ask: "Zapytaj",
    verifyAnswers: "Odpowiedzi generowane automatycznie należy weryfikować w przywołanych hasłach.",
    helpTitle: "Jak korzystać z SGKP?", aboutApp: "O aplikacji", aboutText: "Aplikacja udostępnia hasła z 16 tomów Słownika Geograficznego Królestwa Polskiego i innych krajów słowiańskich. Tekst pochodzi z odczytu OCR; przy każdym wyniku można otworzyć skan strony źródłowej.",
    helpSearchTitle: "Wyszukiwanie", helpSearchText: "Wpisz nazwę albo wyrażenie i wybierz tryb: pełnotekstowy, hybrydowy lub semantyczny. Filtry pozwalają zawęzić wyniki do tomów, powiatów i miejscowości. Kliknij nazwę wyniku, aby przeczytać całe hasło.",
    helpChatTitle: "Konwersacja", helpChatText: "Zadaj pytanie o treść słownika. Odpowiedź powstaje na podstawie odnalezionych fragmentów haseł i zawiera odsyłacze do wykorzystanych źródeł. Otwórz cytowane hasła, aby sprawdzić odpowiedź. Możesz zadać pytanie doprecyzowujące odnoszące się do poprzednich odpowiedzi. „Pobierz PDF” zapisuje bieżącą konwersację wraz ze źródłami; „Wyczyść rozmowę” usuwa ją z tej karty przeglądarki. Gdy model lokalny jest niedostępny, pytanie, krótka historia rozmowy i znalezione fragmenty są przesyłane do OpenAI; aplikacja oznacza taką odpowiedź. Konwersacja nie służy do sporządzania pełnych zestawień wszystkich miejscowości.",
    closeHelp: "Zamknij pomoc", dictionaryEntry: "Hasło słownikowe", openScan: "Otwórz skan strony", scan: "Skan",
    closeEntry: "Zamknij hasło", entryMetadata: "Metadane hasła", entryType: "Typ", localityType: "Typ miejscowości",
    locationDescription: "Opis lokalizacji", catholicParish: "Parafia katolicka", religiousSites: "Obiekty sakralne",
    industry: "Przemysł", mills: "Młyny", archaeology: "Archeologia", nameVariants: "Warianty nazw",
    yes: "Tak", no: "Nie", collectiveEntry: "Hasło zbiorcze: {name}", openCollective: "Otwórz hasło zbiorcze",
    searching: "Wyszukiwanie…", resultsRange: "Wyniki {start}–{end} · około {total} trafień", noResults: "Brak wyników",
    notFoundTitle: "Nie znaleziono haseł", noResultsAdvice: "Zmień słowa zapytania albo ograniczenia w panelu filtrów.",
    searchFailedTitle: "Nie można wyświetlić wyników", serviceRetry: "Sprawdź połączenie z usługą i spróbuj ponownie.",
    resultPage: "Strona {page}", volumePage: "Tom {volume} · s. {page}", districtPrefix: "Powiat {name}",
    volumeShort: "tom {volume}", pageShort: "s. {page}",
    collectiveItem: "Element hasła zbiorczego{number}", scanPage: "Skan strony ↗", filterLoadFailed: "Nie udało się wczytać list filtrów. Wyszukiwanie nadal jest dostępne.",
    communeMatches: "Znaleziono {count} nazw; na liście widać pierwsze 100.",
    chatPhase1: "Analizuję pytanie i kontekst rozmowy…", chatPhase2: "Przeszukuję hasła i fragmenty źródłowe…",
    chatPhase3: "Dobieram źródła odnoszące się do pytania…", chatPhase4: "Przekazuję wybrane fragmenty modelowi do opracowania odpowiedzi…",
    chatPhaseWait: "Model analizuje źródła. Dłuższa odpowiedź może wymagać chwili…",
    chatUnavailable: "Usługa konwersacji jest niedostępna", noStream: "Brak strumienia odpowiedzi",
    openaiGenerating: "OpenAI generuje odpowiedź…", retryGenerating: "Ponowiona próba generuje odpowiedź…",
    modelGenerating: "Model opracowuje odpowiedź na podstawie źródeł…", outputRetry: "Początkowy limit tokenów został osiągnięty. Ponawiam z większym limitem…",
    switchOpenAI: "Model lokalny nie ukończył odpowiedzi. Przełączam na OpenAI…", interrupted: "Przerwano odpowiedź",
    answerInterrupted: "Odpowiedź została przerwana", answerHeading: "Odpowiedź", sourcesHeading: "Źródła",
    openSourceScan: "Skan ↗", preparePdfFailed: "Nie udało się przygotować PDF", defaultPdfName: "sgkp-konwersacja.pdf",
    openaiAnswerNotice: "Odpowiedź przygotowana przez OpenAI ({model}) po niedostępności modelu lokalnego.",
    entryId: "ID: {id} · tom {volume}, s. {page}{number}", entryNumber: " · element nr {number}",
    entryScanAria: "Otwórz skan strony", answerLabel: "Odpowiedź", filtersActive: "{count} aktywne",
    serviceUnavailable: "Usługa jest niedostępna", badServerResponse: "Nieprawidłowa odpowiedź serwera",
    conversationServiceUnavailable: "Usługa konwersacji jest niedostępna", noResponseStream: "Brak strumienia odpowiedzi",
    responseInterrupted: "Odpowiedź została przerwana", couldNotPreparePdf: "Nie udało się przygotować PDF",
    sourceFallback: "Źródło"
  },
  en: {
    documentTitle: "SGKP — Search and Conversation", brandName: "Geographical Dictionary\nof the Kingdom of Poland",
    brandAria: "SGKP — go to search", viewsAria: "Application views", languageAria: "Interface language", themeToggleTitle: "Change theme",
    searchPageTitle: "Search SGKP", chatPageTitle: "Conversation about SGKP",
    searchFiltersAria: "Search filters", searchTab: "Search", chatTab: "Conversation",
    help: "Help", searchLabel: "Search the dictionary", queryPlaceholder: "Place name, person, or words from an entry",
    searchButton: "Search", searchMode: "Search mode", textMode: "Full-text", hybridMode: "Hybrid",
    semanticMode: "Semantic", semanticShare: "Semantic share", mobileShowFilters: "Show filters",
    mobileHideFilters: "Hide filters", narrowResults: "Refine results", filters: "Filters", clear: "Clear",
    volume: "Volume", allVolumes: "All volumes", district: "District", allDistricts: "All districts",
    entryScope: "Entry scope", allEntries: "All entries", placesOnly: "Localities only",
    localityFilters: "Locality filters", localityAvailability: "Available after selecting “Localities only”.",
    kingdomOnly: "Kingdom of Poland only", settlementType: "Settlement type", allTypes: "All types",
    governorate: "Governorate", allGovernorates: "All governorates", commune: "Commune", findCommune: "Find a commune",
    chooseCommune: "Choose a commune", allCommunes: "All communes", communeHint: "Enter part of a name, then select a commune from the list.",
    catalog: "Entry catalogue", searchResults: "Search results", startSearch: "Enter a query to begin.",
    startByName: "Start with a name or subject", enterQuery: "Enter a query in the field above.",
    pagesLabel: "Search result pages", previous: "← Previous", next: "Next →", sourceFilters: "Source filters",
    limitAnswer: "Narrow the answer scope", exampleQuestions: "Example questions",
    exampleSpas: "Which localities had spas?", exampleKingdom: "Did Okuniew in Warsaw County belong to the Kingdom of Poland?",
    exampleSettlements: "What types of settlements are listed in Vilnius County?", exampleZawady: "Where were the Zawady in Warsaw County located?",
    exampleArchaeology: "What archaeological finds were reported in localities in Warsaw County?", exampleGlassworks: "Which localities had glassworks?",
    exampleOil: "What does the dictionary say about oil extraction in Borysław?", downloadPdf: "Download PDF",
    clearConversation: "Clear conversation", yourQuestion: "Your question",
    questionPlaceholder: "Ask about a place, person, or subject described in the dictionary…", ask: "Ask",
    verifyAnswers: "Automatically generated answers should be checked against the cited entries.",
    helpTitle: "How to use SGKP?", aboutApp: "About the application", aboutText: "This application provides entries from all 16 volumes of the Geographical Dictionary of the Kingdom of Poland and Other Slavic Countries. The text comes from OCR; each result links to a scan of the source page.",
    helpSearchTitle: "Searching", helpSearchText: "Enter a name or phrase and choose full-text, hybrid, or semantic search. Filters can narrow results by volume, district, and locality. Select a result title to read the full entry.",
    helpChatTitle: "Conversation", helpChatText: "Ask a question about the dictionary. Answers are based on retrieved entry passages and include citations to the sources. Open cited entries to verify an answer. You can ask follow-up questions about earlier answers. “Download PDF” saves the conversation with its sources; “Clear conversation” removes it from this browser tab. If the local model is unavailable, the current question, a short conversation history, and retrieved passages are sent to OpenAI; the application identifies answers generated this way. The conversation is not intended to produce exhaustive lists of every locality.",
    closeHelp: "Close help", dictionaryEntry: "Dictionary entry", openScan: "Open page scan", scan: "Scan",
    closeEntry: "Close entry", entryMetadata: "Entry metadata", entryType: "Type", localityType: "Settlement type",
    locationDescription: "Location description", catholicParish: "Catholic parish", religiousSites: "Religious sites",
    industry: "Industry", mills: "Mills", archaeology: "Archaeology", nameVariants: "Name variants",
    yes: "Yes", no: "No", collectiveEntry: "Collective entry: {name}", openCollective: "Open collective entry",
    searching: "Searching…", resultsRange: "Results {start}–{end} · about {total} hits", noResults: "No results",
    notFoundTitle: "No entries found", noResultsAdvice: "Try different search terms or change the filters.",
    searchFailedTitle: "Search results are unavailable", serviceRetry: "Check the service connection and try again.",
    resultPage: "Page {page}", volumePage: "Vol. {volume} · p. {page}", districtPrefix: "District {name}",
    volumeShort: "vol. {volume}", pageShort: "p. {page}",
    collectiveItem: "Part of a collective entry{number}", scanPage: "Page scan ↗", filterLoadFailed: "Filter lists could not be loaded. Search is still available.",
    communeMatches: "Found {count} names; showing the first 100.",
    chatPhase1: "Analyzing the question and conversation context…", chatPhase2: "Searching entries and source passages…",
    chatPhase3: "Selecting sources relevant to the question…", chatPhase4: "Sending selected passages to the model…",
    chatPhaseWait: "The model is reviewing the sources. A longer answer may take a moment…",
    chatUnavailable: "The conversation service is unavailable", noStream: "No response stream was received",
    openaiGenerating: "OpenAI is generating the answer…", retryGenerating: "The model is generating a retry…",
    modelGenerating: "The model is preparing an answer from the sources…", outputRetry: "The initial token limit was reached. Retrying with a larger limit…",
    switchOpenAI: "The local model did not finish. Switching to OpenAI…", interrupted: "The answer was interrupted",
    answerInterrupted: "The response was interrupted", answerHeading: "Answer", sourcesHeading: "Sources",
    openSourceScan: "Scan ↗", preparePdfFailed: "Could not prepare the PDF", defaultPdfName: "sgkp-conversation.pdf",
    openaiAnswerNotice: "Answer generated by OpenAI ({model}) because the local model was unavailable.",
    entryId: "ID: {id} · vol. {volume}, p. {page}{number}", entryNumber: " · item {number}",
    entryScanAria: "Open page scan", answerLabel: "Answer", filtersActive: "{count} active",
    serviceUnavailable: "The service is unavailable", badServerResponse: "Invalid server response",
    conversationServiceUnavailable: "The conversation service is unavailable", noResponseStream: "No response stream was received",
    responseInterrupted: "The response was interrupted", couldNotPreparePdf: "Could not prepare the PDF",
    sourceFallback: "Source"
  }
};
let currentLanguage = "pl";
const state = { page: 1, hasNext: false, entry: null, highlight: null, request: 0, gminas: [], chatBusy: false,
  chatController: null, chatGeneration: 0, chatHistory: [], exportTurns: [], searchData: null };

function setText(node, value) { node.textContent = value == null ? "" : String(value); }
function t(key, values = {}) {
  const template = UI_COPY[currentLanguage][key] ?? UI_COPY.pl[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => values[name] ?? "");
}
function applyLanguage(language, persist = false) {
  currentLanguage = language === "en" ? "en" : "pl";
  document.documentElement.lang = currentLanguage;
  document.title = t("documentTitle");
  document.querySelectorAll("[data-i18n]").forEach(node => {
    const value = t(node.dataset.i18n);
    if (node.dataset.i18n === "brandName") {
      const [first, ...rest] = value.split("\n");
      node.replaceChildren(document.createTextNode(first), document.createElement("br"), document.createTextNode(rest.join(" ")));
    } else setText(node, value);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(node => node.placeholder = t(node.dataset.i18nPlaceholder));
  document.querySelectorAll("[data-i18n-aria]").forEach(node => node.setAttribute("aria-label", t(node.dataset.i18nAria)));
  document.querySelectorAll("[data-i18n-title]").forEach(node => node.title = t(node.dataset.i18nTitle));
  document.querySelectorAll("[data-language]").forEach(button => {
    const active = button.dataset.language === currentLanguage;
    button.setAttribute("aria-pressed", String(active));
  });
  $("theme-toggle")?.setAttribute("aria-label", currentLanguage === "en"
    ? (document.documentElement.dataset.theme === "dark" ? "Dark theme. Switch to light theme" : "Light theme. Switch to dark theme")
    : (document.documentElement.dataset.theme === "dark" ? "Tryb nocny. Włącz tryb dzienny" : "Tryb dzienny. Włącz tryb nocny"));
  updateFilterToggleLabel();
  if (state.gminas.length) renderGminaChoices();
  if (state.searchData) renderSearchResults(state.searchData);
  if (state.entry) renderEntry();
  if (persist) {
    try { localStorage.setItem(LANGUAGE_STORAGE_KEY, currentLanguage); } catch { /* Keep current language for this page. */ }
  }
}
function storedLanguage() {
  try { return localStorage.getItem(LANGUAGE_STORAGE_KEY) === "en" ? "en" : "pl"; }
  catch { return "pl"; }
}
function translatedError(message, fallbackKey = "serviceUnavailable") {
  if (currentLanguage !== "en" || !message) return message || t(fallbackKey);
  const direct = new Map([
    ["Nieprawidłowa odpowiedź serwera", "badServerResponse"],
    ["Usługa jest niedostępna", "serviceUnavailable"],
    ["Usługa konwersacji jest niedostępna", "conversationServiceUnavailable"],
    ["Brak strumienia odpowiedzi", "noResponseStream"],
    ["Odpowiedź została przerwana", "responseInterrupted"],
    ["Nie udało się przygotować PDF", "couldNotPreparePdf"]
  ]);
  if (direct.has(message)) return t(direct.get(message));
  const unavailable = message.match(/^Usługa ([\w-]+) jest niedostępna$/);
  if (unavailable) {
    const names = {meilisearch: "search", embedding: "embeddings", chat: "conversation", openai: "OpenAI"};
    return `The ${names[unavailable[1]] || unavailable[1]} service is unavailable.`;
  }
  return message;
}
function applyTheme(theme, persist = false) {
  const dark = theme === "dark";
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  const toggle = $("theme-toggle");
  if (toggle) {
    toggle.setAttribute("aria-pressed", String(dark));
    const labels = currentLanguage === "en"
      ? (dark ? "Dark theme. Switch to light theme" : "Light theme. Switch to dark theme")
      : (dark ? "Tryb nocny. Włącz tryb dzienny" : "Tryb dzienny. Włącz tryb nocny");
    toggle.setAttribute("aria-label", labels);
  }
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.content = dark ? "#101923" : "#1c4f89";
  if (persist) {
    try { localStorage.setItem(THEME_STORAGE_KEY, dark ? "dark" : "light"); }
    catch { /* Theme remains active for this page even when storage is unavailable. */ }
  }
}
function storedTheme() {
  try { return localStorage.getItem(THEME_STORAGE_KEY) === "dark" ? "dark" : "light"; }
  catch { return "light"; }
}
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
  catch { throw new Error(t("badServerResponse")); }
  if (!response.ok) throw new Error(translatedError(data.error, "serviceUnavailable"));
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
  $("mobile-filter-toggle").firstChild.textContent = (expanded ? t("mobileHideFilters") : t("mobileShowFilters")) + (count ? " (" + count + ")" : "") + " ";
  setText($("assistant-filter-hint"), count ? t("filtersActive", {count}) : t("limitAnswer"));
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
  meta.append(element("span", t("volumePage", {volume: hit.tom || "—", page: hit.strona || "—"})));
  if (hit.powiat_ujednolicony) meta.append(element("span", t("districtPrefix", {name: hit.powiat_ujednolicony})));
  if (hit.parent_id) meta.append(element("span", t("collectiveItem", {number: hit.nr ? " · " + hit.nr : ""})));
  if (hit.url_skanu) meta.append(externalLink(t("scanPage"), hit.url_skanu));
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
function renderSearchResults(data) {
  state.page = data.page;
  state.hasNext = data.has_next;
  $("prev").disabled = data.page <= 1;
  $("next").disabled = !data.has_next;
  setText($("page-label"), t("resultPage", {page: data.page}));
  $("results").replaceChildren();
  if (data.hits.length) {
    const start = (data.page - 1) * data.page_size + 1;
    const end = start + data.hits.length - 1;
    setText($("status"), t("resultsRange", {start, end, total: data.estimated_total_hits}));
    for (const hit of data.hits) $("results").append(resultCard(hit));
    $("pagination").hidden = false;
  } else {
    setText($("status"), t("noResults"));
    $("results").append(makeEmpty(t("notFoundTitle"), t("noResultsAdvice")));
    $("pagination").hidden = true;
  }
}
async function search(page = 1) {
  const params = queryParams(page);
  if (!params.get("q")) return;
  const current = ++state.request;
  state.searchData = null;
  setText($("status"), t("searching"));
  $("status").classList.remove("error");
  $("results").replaceChildren();
  $("pagination").hidden = true;
  try {
    const data = await api("api/v1/search?" + params);
    if (current !== state.request) return;
    state.searchData = data;
    renderSearchResults(data);
    history.replaceState(null, "", location.pathname + "?" + params + (location.hash || "#wyszukiwanie"));
  } catch (error) {
    if (current !== state.request) return;
    setText($("status"), translatedError(error.message));
    $("status").classList.add("error");
    $("results").append(makeEmpty(t("searchFailedTitle"), t("serviceRetry")));
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
  const all = element("option", t("allCommunes"));
  all.value = "";
  select.append(all);
  for (const value of visible) {
    const option = element("option", value);
    option.value = value;
    select.append(option);
  }
  select.value = selected && visible.includes(selected) ? selected : "";
  setText($("gmina-hint"), query
    ? t("communeMatches", {count: matched.length})
    : t("communeHint"));
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
    setText($("filter-options-status"), t("filterLoadFailed"));
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
  setText($("entry-meta"), t("entryId", {id: entry.ID, volume: entry.tom, page: entry.strona,
    number: entry.nr ? t("entryNumber", {number: entry.nr}) : ""}));
  $("scan-link").hidden = !entry.url_skanu;
  if (entry.url_skanu) $("scan-link").href = entry.url_skanu;
  const localityType = entry.metadata.typ_punktu_osadniczego;
  const isLocality = Array.isArray(localityType) ? localityType.length > 0 : Boolean(localityType);
  const labels = {
    ...(isLocality ? {typ_punktu_osadniczego: t("localityType")} : {typ: t("entryType")}),
    powiat_ujednolicony: t("district"), gmina: t("commune"), gubernia_ujednolicona: t("governorate"),
    królestwo_polskie: t("kingdomOnly"), opis_lokalizacji: t("locationDescription"),
    parafia_katolicka: t("catholicParish"), obiekty_sakralne: t("religiousSites"),
    przemysłowe: t("industry"), młyny: t("mills"), archeo: t("archaeology"), warianty_nazw: t("nameVariants")
  };
  $("entry-fields-list").replaceChildren();
  for (const [key, label] of Object.entries(labels)) {
    let value = entry.metadata[key];
    if (value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length)) continue;
    if (key === "warianty_nazw") value = value.map(item => item.wariant_nazwy || "").filter(Boolean);
    if (Array.isArray(value)) value = value.map(item => typeof item === "object" ? JSON.stringify(item) : String(item)).join(", ");
    else if (typeof value === "boolean") value = value ? t("yes") : t("no");
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
    $("parent-context").replaceChildren(element("h3", t("collectiveEntry", {name: entry.parent.nazwa})));
    const button = element("button", t("openCollective"), "button button-outline");
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
  const phases = [
    t("chatPhase1"), t("chatPhase2"), t("chatPhase3"), t("chatPhase4"),
  ];
  let phase = 0, gotFirstDelta = false, retrying = false;
  setText(statusNode, phases[0]);
  statusNode.classList.add("is-working");
  const progressTimer = setInterval(() => {
    if (phase < phases.length - 1) setText(statusNode, phases[++phase]);
    else setText(statusNode, t("chatPhaseWait"));
  }, 4500);
  try {
    const response = await fetch("api/v1/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json", "Accept": "text/event-stream"},
      body: JSON.stringify({question, filters, history, language: currentLanguage}), signal
    });
    if (!response.ok) {
      let data = {};
      try { data = await response.json(); } catch {}
      throw new Error(translatedError(data.error, "conversationServiceUnavailable"));
    }
    if (!response.body) throw new Error(t("noStream"));
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
        if (type === "delta") {
          if (!gotFirstDelta) {
            clearInterval(progressTimer);
            setText(statusNode, provider === "openai" ? t("openaiGenerating")
              : retrying ? t("retryGenerating") : t("modelGenerating"));
            gotFirstDelta = true;
            retrying = false;
          }
          answerNode.append(document.createTextNode(data.text));
        }
        else if (type === "retry") {
          setText(answerNode, "");
          answerNode.classList.remove("rendered");
          setText(statusNode, t("outputRetry"));
          gotFirstDelta = false;
          retrying = true;
        }
        else if (type === "fallback") {
          setText(answerNode, "");
          answerNode.classList.remove("rendered");
          sourcesNode.replaceChildren();
          provider = "openai";
          gotFirstDelta = false;
          setText(statusNode, t("switchOpenAI"));
        }
        else if (type === "error") throw new Error(translatedError(data.error, "interrupted"));
        else if (type === "answer") {
          complete = true;
          finalAnswer = data;
          provider = data.provider || "local";
          model = data.model || "";
          renderAnswerMarkdown(answerNode, data.answer);
          sourcesNode.replaceChildren();
          for (const source of data.sources || []) {
            const item = element("li");
            const location = [source.tom ? t("volumeShort", {volume: source.tom}) : "", source.strona ? t("pageShort", {page: source.strona}) : ""].filter(Boolean).join(", ");
            const button = element("button", "[" + source.citation + "] " + source.nazwa + (location ? " · " + location : ""));
            button.type = "button";
            button.addEventListener("click", () => openEntry(source.entry_id, source.start_offset, source.end_offset));
            item.append(button);
            if (source.url_skanu) item.append(externalLink(t("openSourceScan"), source.url_skanu));
            sourcesNode.append(item);
          }
        }
      }
      if (done) break;
    }
    if (!complete) throw new Error(t("answerInterrupted"));
    return {...finalAnswer, provider, model};
  } finally {
    clearInterval(progressTimer);
  }
}
function makeTurn(question) {
  const turn = element("article", undefined, "turn");
  turn.append(element("div", question, "question-bubble"));
  const card = element("div", undefined, "answer-card");
  card.append(element("h2", t("answerHeading")));
  const status = element("p", t("chatPhase1"), "answer-status is-working");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.setAttribute("aria-atomic", "true");
  const answer = element("div", undefined, "answer-text");
  const heading = element("p", t("sourcesHeading"), "source-heading");
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
      throw new Error(translatedError(data.error, "couldNotPreparePdf"));
    }
    const blob = await response.blob();
    const name = response.headers.get("Content-Disposition")?.match(/filename="?([\w.-]+)"?/)?.[1]
      || t("defaultPdfName");
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
    setText(nodes.status, result.provider === "openai" ? t("openaiAnswerNotice", {model: result.model}) : "");
    nodes.status.classList.remove("is-working");
    nodes.heading.hidden = !nodes.sources.children.length;
    $("question").value = "";
  } catch (error) {
    if (generation !== state.chatGeneration) return;
    setText(nodes.status, error.message);
    nodes.status.classList.remove("is-working");
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
  applyTheme(storedTheme());
  applyLanguage(storedLanguage());
  for (const button of document.querySelectorAll("[data-language]")) {
    button.addEventListener("click", () => applyLanguage(button.dataset.language, true));
  }
  $("theme-toggle").addEventListener("click", () => {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark", true);
  });
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
