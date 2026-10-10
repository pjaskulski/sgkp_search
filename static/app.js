"use strict";

const $ = id => document.getElementById(id);
const optionFields = ["tom", "powiat_ujednolicony", "typ", "typ_punktu_osadniczego", "gubernia_ujednolicona"];
const CHAT_HISTORY_TURNS = 8;
const CHAT_HISTORY_ANSWER_CHARS = 5000;
const THEME_STORAGE_KEY = "sgkp-theme";
const LANGUAGE_STORAGE_KEY = "sgkp-language";
const UI_COPY = {
  pl: {
    documentTitle: "SGKP — wyszukiwanie i konwersacja", brandName: "Słownik Geograficzny\nKrólestwa Polskiego",
    brandAria: "SGKP — przejdź do wyszukiwania", viewsAria: "Widoki aplikacji", languageAria: "Język interfejsu", themeToggleTitle: "Zmień motyw",
    searchPageTitle: "Wyszukiwanie w SGKP", chatPageTitle: "Konwersacja o treści SGKP", browsePageTitle: "Przeglądanie haseł SGKP",
    searchFiltersAria: "Filtry wyszukiwania", searchTab: "Wyszukiwanie", chatTab: "Konwersacja", browseTab: "Przeglądanie",
    browseHeading: "Przeglądanie haseł", browseVolume: "Tom", browseAllVolumes: "Wybierz tom",
    browseName: "Nazwa", browseNamePlaceholder: "Nazwa lub fragment nazwy", browseNameEmpty: "Brak haseł o podanej nazwie spełniających filtry.",
    browseLoading: "Wczytuję hasła…", browseInitial: "Wybierz tom, aby wyświetlić listę haseł.", browseRange: "Hasła {start}–{end} z {total}", browseEmpty: "Brak haseł w tym tomie.", browsePages: "Strony listy haseł", browseViewLabel: "Widok haseł", browseListView: "Widok listy", browseGridView: "Widok siatki", firstPage: "Początek", lastPage: "Koniec",
    collectiveKind: "Hasło zbiorcze", showSubentries: "Pokaż podhasła", hideSubentries: "Ukryj podhasła",
    loadingSubentries: "Wczytuję podhasła…", noSubentries: "To hasło nie zawiera podhaseł.", subentriesTitle: "Podhasła",
    help: "Pomoc", projectCredit: "Aplikacja przygotowana w Pracowni Historii Cyfrowej IHPAN w ramach projektu „Geografia kulturowo-intelektualna dawnych ziem polskich pod zaborami 1865–1918 – cyfrowe vademecum” prowadzonego w Instytucie Historii Polskiej Akademii Nauk.",
    contactLabel: "Skontaktuj się z nami", searchLabel: "Szukaj w słowniku", queryPlaceholder: "Nazwa miejscowości, osoba lub słowa z hasła",
    semanticQueryPlaceholder: "Oczekiwana tematyka, np. 'wydobywanie surowców' lub 'mielenie ziarna'",
    searchButton: "Wyszukaj", searchMode: "Tryb wyszukiwania", textMode: "Pełnotekstowe", hybridMode: "Hybrydowe",
    semanticMode: "Semantyczne", semanticShare: "Udział semantyki", mobileShowFilters: "Pokaż filtry",
    mobileHideFilters: "Ukryj filtry", narrowResults: "Zawęź wyniki", filters: "Filtry", clear: "Wyczyść",
    volume: "Tom", allVolumes: "Wszystkie tomy", district: "Powiat", allDistricts: "Wszystkie powiaty",
    entryScope: "Zakres haseł", allEntries: "Wszystkie hasła", placesOnly: "Tylko miejscowości", nonPlacesOnly: "Tylko hasła niebędące miejscowościami",
    informationFilters: "Informacje w haśle",
    informationFiltersHint: "Wymagaj informacji o wszystkich zaznaczonych kategoriach. Brak adnotacji nie oznacza braku obiektu.",
    presenceReligiousSites: "Obiekty sakralne", presenceSchools: "Szkoły", presenceMills: "Młyny",
    presenceIndustry: "Zakłady przemysłowe", presenceMonuments: "Zabytki",
    presenceArchaeology: "Znaleziska archeologiczne", presenceHealthcare: "Opieka zdrowotna",
    presenceLibraries: "Biblioteki", presenceSpas: "Uzdrowiska",
    presenceCustoms: "Urzędy i obiekty celne",
    presenceOffices: 'Urzędy',
    presenceGardens: 'Ogrody i architektura krajobrazu',
    presenceBreeding: 'Hodowla',
    presenceCemeteries: 'Nekropolie',
    presenceCharity: 'Dobroczynność',
    presenceCourts: 'Sądy',
    presenceMilitary: 'Wojsko',
    presenceNavigation: 'Żegluga i przeprawy',
    presenceCollections: 'Kolekcjonerstwo',
    presencePrinting: 'Drukarnie',
    presenceMuseums: 'Muzealnictwo',
    presenceBookshops: 'Księgarnie',
    presenceBursas: 'Bursy',
    informationTransport: 'Transport i łączność',
    informationAdministration: 'Urzędy, sądy i wojsko',
    informationCulture: 'Kultura i książka',
    presenceManors: "Dwory i pałace", presencePost: "Poczta i telegraf", presenceRailway: "Stacje kolejowe",
    presenceTrade: "Handel", presenceCrafts: "Rzemiosło",
    informationHeritage: 'Obiekty i dziedzictwo', informationEconomy: 'Gospodarka',
    informationServices: 'Edukacja, zdrowie i dobroczynność',
    localityFilters: "Filtry miejscowości", localityAvailability: "Dostępne po wybraniu „Tylko miejscowości”.",
    otherEntries: "Inne hasła", otherEntriesAvailability: "Dostępne po wybraniu „Tylko hasła niebędące miejscowościami”.",
    kingdomOnly: "Tylko Królestwo Polskie", settlementType: "Typ miejscowości", allTypes: "Wszystkie typy",
    governorate: "Gubernia", allGovernorates: "Wszystkie gubernie", commune: "Gmina", findCommune: "Znajdź nazwę gminy",
    chooseCommune: "Wybierz gminę", allCommunes: "Wszystkie gminy", communeHint: "Wpisz fragment nazwy, potem wybierz gminę z listy.",
    findParish: "Znajdź nazwę parafii", chooseParish: "Wybierz parafię",
    allParishes: "Wszystkie parafie", parishHint: "Wpisz fragment nazwy, potem wybierz parafię z listy.",
    parishMatches: "Pasujące parafie: {count}. Wybierz parafię z listy.",
    catalog: "Katalog haseł", searchResults: "Wyniki wyszukiwania", startSearch: "Wpisz zapytanie, aby rozpocząć.",
    startByName: "Zacznij od nazwy lub tematu", enterQuery: "Wprowadź zapytanie w polu powyżej.",
    pagesLabel: "Strony wyników", previous: "← Poprzednia", next: "Następna →", sourceFilters: "Filtry źródeł",
    limitAnswer: "Ogranicz zakres odpowiedzi", chatFilters: "Filtry", exampleQuestions: "Przykładowe pytania",
    exampleSpas: "W jakich miejscowościach znajdowały się uzdrowiska?", exampleKingdom: "Czy Okuniew w powiecie warszawskim należał do Królestwa Polskiego?",
    exampleSettlements: "Jakie typy osad wymieniono w powiecie wileńskim?", exampleZawady: "Gdzie leżały Zawady w powiecie warszawskim?",
    exampleArchaeology: "Jakie znaleziska archeologiczne znajdowały się w miejscowościach powiatu warszawskiego?", exampleGlassworks: "W których miejscowościach znajdowały się huty szkła?",
    exampleOil: "Co słownik mówi o wydobyciu ropy naftowej w Borysławiu?", exampleKononowicze: "Co wiadomo o miejscowości Kononowicze w powiecie oszmiańskim?",
    exampleZyrardow: "Ilu robotników pracowało w zakładach Żyrardowa i jakie wyroby tam wytwarzano?", downloadPdf: "Pobierz PDF",
    moreExamples: 'Więcej przykładów',
    closeExamples: 'Zamknij przykłady',
    findExample: 'Znajdź pytanie',
    examplesSearchPlaceholder: 'Wpisz słowo lub fragment pytania',
    examplesCategory: 'Temat',
    examplesAll: 'Wszystkie tematy',
    examplesPlaces: 'Miejscowości',
    examplesEconomy: 'Gospodarka',
    examplesHeritage: 'Kultura i dziedzictwo',
    examplesHealth: 'Zdrowie i uzdrowiska',
    examplesCounts: 'Zliczanie haseł',
    examplesEmpty: 'Brak pytań pasujących do wybranych warunków.',
    examplesHint: 'Wybierz pytanie, aby wpisać je do Konwersacji. Przed wysłaniem możesz je zmienić i ustawić filtry.',
    exampleSpasCount: 'W ilu hasłach pojawiają się informacje o uzdrowiskach?',
    exampleLibrariesCount: 'W ilu hasłach pojawiają się informacje o bibliotekach?',
    exampleBarczaca: 'Co wiadomo o miejscowości Barcząca?',
    exampleCustomsCount: 'W ilu hasłach pojawiają się informacje o urzędach i obiektach celnych?',
    exampleReligiousCount: "W ilu hasłach pojawiają się informacje o obiektach sakralnych?",
    clearConversation: "Wyczyść rozmowę", yourQuestion: "Twoje pytanie",
    questionPlaceholder: "Zapytaj o miejscowość, osobę lub zagadnienie opisane w słowniku…", ask: "Zapytaj",
    verifyAnswers: "Odpowiedzi generowane automatycznie należy weryfikować w przywołanych hasłach.",
    helpTitle: "Jak korzystać z SGKP?", aboutApp: "O aplikacji", aboutText: "Aplikacja udostępnia hasła z 16 tomów Słownika Geograficznego Królestwa Polskiego i innych krajów słowiańskich. Tekst pochodzi z odczytu OCR; przy każdym wyniku można otworzyć skan strony źródłowej. Obecna wersja aplikacji jest prototypem, mogą występować problemy i częste zmiany w sposobie działania aplikacji. Dane dostępne w aplikacji (tekst SGKP i metadane) również są modyfikowane w wyniku trwającej weryfikacji błędów.",
    helpSearchTitle: "Wyszukiwanie", helpSearchText: "Wpisz nazwę albo wyrażenie i wybierz tryb: pełnotekstowy, hybrydowy lub semantyczny. Filtry pozwalają zawęzić wyniki do tomów, powiatów i miejscowości. Kliknij nazwę wyniku, aby przeczytać całe hasło.",
    helpChatTimeLimit: "Serwer może przerwać obsługę pytania, jeśli przetwarzanie trwa dłużej niż 5 minut (300 sekund). Limit obejmuje wyszukiwanie źródeł, ich weryfikację i przygotowanie odpowiedzi. W takim przypadku spróbuj ponownie lub zawęź zakres pytania.",
    helpBrowseTitle: "Przeglądanie",
    helpBrowseText: "Przeglądaj hasła indywidualne i elementy haseł zbiorczych w kolejności ich identyfikatorów, po 50 na stronie. Domyślnie wyświetlany jest tom 1 i wszystkie rodzaje haseł. W panelu po lewej wybierz tom lub wszystkie tomy, wpisz nazwę albo jej fragment i ustaw pozostałe filtry. Lista odświeża się po każdej zmianie; panel można zwinąć. W filtrach gminy i parafii katolickiej wpisz fragment nazwy, a następnie wybierz pozycję z listy. Możesz przełączać widok listy i siatki oraz korzystać z nawigacji na górze i dole listy. Kliknij nazwę, aby otworzyć treść i metadane hasła, albo link do skanu, aby zobaczyć stronę źródłową. Podhasła są oznaczone jako elementy haseł zbiorczych; ich tom i strona pochodzą z hasła zbiorczego. Filtry obecności informacji odnoszą się do adnotacji w metadanych — brak adnotacji nie dowodzi braku obiektu w miejscowości.",
    helpChatTitle: "Konwersacja", helpChatText: "Zadaj pytanie o treść słownika. Odpowiedź powstaje na podstawie odnalezionych fragmentów haseł i zawiera odsyłacze do wykorzystanych źródeł. Otwórz cytowane hasła, aby sprawdzić odpowiedź. Możesz zadać pytanie doprecyzowujące odnoszące się do poprzednich odpowiedzi. „Pobierz PDF” zapisuje bieżącą konwersację wraz ze źródłami; „Wyczyść rozmowę” usuwa ją z tej karty przeglądarki. Gdy model lokalny jest niedostępny, pytanie, krótka historia rozmowy i znalezione fragmenty są przesyłane do OpenAI; aplikacja oznacza taką odpowiedź. Konwersacja nie służy do sporządzania pełnych zestawień wszystkich miejscowości.",
    closeHelp: "Zamknij pomoc", dictionaryEntry: "Hasło słownikowe", openScan: "Otwórz skan strony", scan: "Skan",
    closeEntry: "Zamknij hasło", entryMetadata: "Metadane hasła", entryType: "Typ", localityType: "Typ miejscowości",
    locationDescription: "Opis lokalizacji", catholicParish: "Parafia katolicka", otherParish: "Inna parafia", religiousSites: "Obiekty sakralne",
    populationStatistics: "Liczba mieszkańców", dwellingStatistics: "Liczba domów", religiousStructure: "Struktura wyznaniowa",
    industry: "Przemysł", mills: "Młyny", archaeology: "Archeologia", nameVariants: "Warianty nazw",
    yes: "Tak", no: "Nie", collectiveEntry: "Hasło zbiorcze: {name}", openCollective: "Otwórz hasło zbiorcze",
    searching: "Wyszukiwanie…", rankingScore: "Ocena trafności",
    chatContextTruncated: "Osiągnięto limit długości kontekstu. Część zaakceptowanych źródeł została skrócona lub pominięta.",
    chatVerifyIncomplete: "Limit czasu weryfikacji został osiągnięty. Odpowiedź opiera się na dotychczas zaakceptowanych źródłach.",
    deeperAnalysis: "Pogłębiona analiza",
    deeperAnalysisTooltip: "Włącza dodatkowe rozumowanie modelu podczas przygotowywania końcowej odpowiedzi. Może pomóc przy złożonych pytaniach, ale nie gwarantuje większej poprawności.",
    chatVerifyHint: "(wydłuża przygotowanie odpowiedzi)",
    verifyResults: "Dodatkowa weryfikacja wyników", verifyHint: "Uwaga: wydłuża wyszukiwanie",
    searchingVerified: "Wyszukuję i weryfikuję wyniki — proszę czekać…",
    verifiedCount: "Zaakceptowane wyniki: {count}", verificationIncomplete: "Weryfikacja nie została ukończona. Możesz kontynuować na następnej stronie.",
    relevanceKeep: "{model}: zachowałby wynik", relevanceReject: "{model}: odrzuciłby wynik",
    relevanceUnavailable: "{model}: ocena niedostępna", relevanceBudget: "{model}: pominięto — limit czasu",
    relevanceSkippedError: "{model}: pominięto po błędzie wcześniejszej oceny",
    relevanceEvidence: "Fragment oceniony przez {model} (diagnostyka)",
    relevanceTime: "czas wywołania: {seconds} s", relevanceCached: "ocena z pamięci",
    resultsRange: "Wyniki {start}–{end} · około {total} trafień",
    resultsRangeLimited: "Wyniki {start}–{end} · można przeglądać maksymalnie pierwsze {limit} wyników",
    noResults: "Brak wyników",
    notFoundTitle: "Nie znaleziono haseł", noResultsAdvice: "Zmień słowa zapytania albo ograniczenia w panelu filtrów.",
    searchFailedTitle: "Nie można wyświetlić wyników", serviceRetry: "Sprawdź połączenie z usługą i spróbuj ponownie.",
    resultPage: "Strona {page}", volumePage: "Tom {volume} · s. {page}", volumePart1: "cz. 1", volumePart2: "cz. 2", districtPrefix: "Powiat {name}",
    volumeShort: "tom {volume}", pageShort: "s. {page}",
    collectiveItem: "Element hasła zbiorczego{number}", scanPage: "Skan strony ↗", filterLoadFailed: "Nie udało się wczytać list filtrów. Wyszukiwanie nadal jest dostępne.",
    communeMatches: "Znaleziono {count} nazw; na liście widać pierwsze 100.",
    chatPhase1: "Analizuję pytanie i kontekst rozmowy…", chatPhase2: "Przeszukuję hasła i fragmenty źródłowe…",
    chatPhase3: "Dobieram źródła odnoszące się do pytania…", chatPhase4: "Przekazuję wybrane fragmenty modelowi do opracowania odpowiedzi…",
    answerPreparationTime: "Czas przygotowania odpowiedzi: {seconds} s",
    chatSupplementarySearch: "Wyszukuję dodatkowe źródła, aby uzupełnić odpowiedź…",
    chatPhaseWait: "Model analizuje źródła. Dłuższa odpowiedź może wymagać chwili…",
    chatUnavailable: "Usługa konwersacji jest niedostępna", noStream: "Brak strumienia odpowiedzi",
    openaiGenerating: "OpenAI generuje odpowiedź…", retryGenerating: "Ponowiona próba generuje odpowiedź…",
    modelGenerating: "Model opracowuje odpowiedź na podstawie źródeł…", outputRetry: "Początkowy limit tokenów został osiągnięty. Ponawiam z większym limitem…",
    switchOpenAI: "Model lokalny nie ukończył odpowiedzi. Przełączam na OpenAI…", interrupted: "Przerwano odpowiedź",
    answerInterrupted: "Odpowiedź została przerwana", answerHeading: "Odpowiedź", sourcesHeading: "Źródła",
    openSourceScan: "Skan ↗", preparePdfFailed: "Nie udało się przygotować PDF", defaultPdfName: "sgkp-konwersacja.pdf",
    openaiAnswerNotice: "Odpowiedź przygotowana przez OpenAI ({model}) po niedostępności modelu lokalnego.",
    entryId: "ID: {id} · tom {volume}, s. {page}{number}", entryNumber: " · element nr {number}",
    entryScanAria: "Otwórz skan strony", answerLabel: "Odpowiedź", filtersActive: "Filtry źródeł: {count}",
    serviceUnavailable: "Usługa jest niedostępna", badServerResponse: "Nieprawidłowa odpowiedź serwera",
    http503: "Usługa jest chwilowo niedostępna (HTTP 503). Spróbuj ponownie za chwilę.",
    http502: "Serwer pośredniczący nie otrzymał poprawnej odpowiedzi aplikacji (HTTP 502). Spróbuj ponownie.",
    http504: "Przekroczono czas oczekiwania na odpowiedź aplikacji (HTTP 504). Spróbuj ponownie.",
    conversationServiceUnavailable: "Usługa konwersacji jest niedostępna", noResponseStream: "Brak strumienia odpowiedzi",
    responseInterrupted: "Odpowiedź została przerwana", couldNotPreparePdf: "Nie udało się przygotować PDF",
    sourceFallback: "Źródło"
  },
  en: {
    documentTitle: "SGKP — Search and Conversation", brandName: "Geographical Dictionary\nof the Kingdom of Poland",
    brandAria: "SGKP — go to search", viewsAria: "Application views", languageAria: "Interface language", themeToggleTitle: "Change theme",
    searchPageTitle: "Search SGKP", chatPageTitle: "Conversation about SGKP", browsePageTitle: "Browse SGKP entries",
    searchFiltersAria: "Search filters", searchTab: "Search", chatTab: "Conversation", browseTab: "Browse entries",
    browseHeading: "Browse entries", browseVolume: "Volume", browseAllVolumes: "Select a volume",
    browseName: "Name", browseNamePlaceholder: "Name or part of a name", browseNameEmpty: "No entry names match the selected filters.",
    browseLoading: "Loading entries…", browseInitial: "Select a volume to browse its entries.", browseRange: "Entries {start}–{end} of {total}", browseEmpty: "No entries in this volume.", browsePages: "Entry list pages", browseViewLabel: "Entry view", browseListView: "List view", browseGridView: "Grid view", firstPage: "First", lastPage: "Last",
    collectiveKind: "Collective entry", showSubentries: "Show subentries", hideSubentries: "Hide subentries",
    loadingSubentries: "Loading subentries…", noSubentries: "This entry has no subentries.", subentriesTitle: "Subentries",
    help: "Help", projectCredit: "This application was prepared by the Digital History Laboratory at the Institute of History of the Polish Academy of Sciences as part of the project “Geografia kulturowo-intelektualna dawnych ziem polskich pod zaborami 1865–1918 – cyfrowe vademecum”.",
    contactLabel: "Contact us", searchLabel: "Search the dictionary", queryPlaceholder: "Place name, person, or words from an entry",
    semanticQueryPlaceholder: "Topic, e.g. raw material extraction or grain milling",
    searchButton: "Search", searchMode: "Search mode", textMode: "Full-text", hybridMode: "Hybrid",
    semanticMode: "Semantic", semanticShare: "Semantic share", mobileShowFilters: "Show filters",
    mobileHideFilters: "Hide filters", narrowResults: "Refine results", filters: "Filters", clear: "Clear",
    volume: "Volume", allVolumes: "All volumes", district: "District", allDistricts: "All districts",
    entryScope: "Entry scope", allEntries: "All entries", placesOnly: "Localities only", nonPlacesOnly: "Non-locality entries only",
    informationFilters: "Information in the entry",
    informationFiltersHint: "Require information about all selected categories. Missing annotations do not establish absence.",
    presenceReligiousSites: "Religious sites", presenceSchools: "Schools", presenceMills: "Mills",
    presenceIndustry: "Industrial facilities", presenceMonuments: "Historic monuments",
    presenceArchaeology: "Archaeological finds", presenceHealthcare: "Healthcare",
    presenceLibraries: "Libraries", presenceSpas: "Spas",
    presenceCustoms: "Customs offices and facilities",
    presenceOffices: 'Offices',
    presenceGardens: 'Gardens and landscape architecture',
    presenceBreeding: 'Animal husbandry',
    presenceCemeteries: 'Cemeteries',
    presenceCharity: 'Charity',
    presenceCourts: 'Courts',
    presenceMilitary: 'Military',
    presenceNavigation: 'Navigation and crossings',
    presenceCollections: 'Collecting',
    presencePrinting: 'Printing houses',
    presenceMuseums: 'Museums',
    presenceBookshops: 'Bookshops',
    presenceBursas: 'Student boarding houses',
    informationTransport: 'Transport and communications',
    informationAdministration: 'Offices, courts and military',
    informationCulture: 'Culture and books',
    presenceManors: "Manor houses and palaces", presencePost: "Post and telegraph", presenceRailway: "Railway stations",
    presenceTrade: "Trade", presenceCrafts: "Crafts",
    informationHeritage: 'Buildings and heritage', informationEconomy: 'Economy',
    informationServices: 'Education, healthcare and charity',
    localityFilters: "Locality filters", localityAvailability: "Available after selecting “Localities only”.",
    otherEntries: "Other entries", otherEntriesAvailability: "Available after selecting “Non-locality entries only”.",
    kingdomOnly: "Kingdom of Poland only", settlementType: "Settlement type", allTypes: "All types",
    governorate: "Governorate", allGovernorates: "All governorates", commune: "Commune", findCommune: "Find a commune",
    chooseCommune: "Choose a commune", allCommunes: "All communes", communeHint: "Enter part of a name, then select a commune from the list.",
    findParish: "Find a parish", chooseParish: "Choose a parish",
    allParishes: "All parishes", parishHint: "Enter part of a name, then select a parish from the list.",
    parishMatches: "Matching parishes: {count}. Select a parish from the list.",
    catalog: "Entry catalogue", searchResults: "Search results", startSearch: "Enter a query to begin.",
    startByName: "Start with a name or subject", enterQuery: "Enter a query in the field above.",
    pagesLabel: "Search result pages", previous: "← Previous", next: "Next →", sourceFilters: "Source filters",
    limitAnswer: "Narrow the answer scope", chatFilters: "Filters", exampleQuestions: "Example questions",
    exampleSpas: "Which localities had spas?", exampleKingdom: "Did Okuniew in Warsaw County belong to the Kingdom of Poland?",
    exampleSettlements: "What types of settlements are listed in Vilnius County?", exampleZawady: "Where were the Zawady in Warsaw County located?",
    exampleArchaeology: "What archaeological finds were reported in localities in Warsaw County?", exampleGlassworks: "Which localities had glassworks?",
    exampleOil: "What does the dictionary say about oil extraction in Borysław?", exampleKononowicze: "What is known about the locality of Kononowicze in Oszmiana County?",
    exampleZyrardow: "How many workers were employed in Żyrardów's factories, and what products were made there?", downloadPdf: "Download PDF",
    moreExamples: 'More examples',
    closeExamples: 'Close examples',
    findExample: 'Find a question',
    examplesSearchPlaceholder: 'Enter a word or part of a question',
    examplesCategory: 'Topic',
    examplesAll: 'All topics',
    examplesPlaces: 'Localities',
    examplesEconomy: 'Economy',
    examplesHeritage: 'Culture and heritage',
    examplesHealth: 'Healthcare and spas',
    examplesCounts: 'Entry counts',
    examplesEmpty: 'No questions match the selected criteria.',
    examplesHint: 'Select a question to enter it in the Conversation field. You can edit it and set filters before sending.',
    exampleSpasCount: 'How many entries contain information about spas?',
    exampleLibrariesCount: 'How many entries contain information about libraries?',
    exampleBarczaca: 'What is known about the locality of Barcząca?',
    exampleCustomsCount: 'How many entries contain information about customs offices and facilities?',
    exampleReligiousCount: "How many entries contain information about religious buildings?",
    clearConversation: "Clear conversation", yourQuestion: "Your question",
    questionPlaceholder: "Ask about a place, person, or subject described in the dictionary…", ask: "Ask",
    verifyAnswers: "Automatically generated answers should be checked against the cited entries.",
    helpTitle: "How to use SGKP?", aboutApp: "About the application", aboutText: "This application provides entries from all 16 volumes of the Geographical Dictionary of the Kingdom of Poland and Other Slavic Countries. The text comes from OCR; each result links to a scan of the source page. The current version of the application is a prototype, so issues may occur and the way the application works may change frequently. The data available in the application (the SGKP text and metadata) are also subject to change as part of the ongoing error verification process.",
    helpSearchTitle: "Searching", helpSearchText: "Enter a name or phrase and choose full-text, hybrid, or semantic search. Filters can narrow results by volume, district, and locality. Select a result title to read the full entry.",
    helpChatTimeLimit: "The server may interrupt a request if processing takes longer than 5 minutes (300 seconds). This limit includes source retrieval, verification, and answer generation. If this happens, try again or narrow the scope of your question.",
    helpBrowseTitle: "Browsing",
    helpBrowseText: "Browse individual entries and subentries of collective entries in identifier order, with 50 entries per page. The default is volume 1 and all entry types. In the left panel, choose a volume or all volumes, enter a name or part of a name, and set other filters. The list updates after each change; the panel can be collapsed. For commune and Catholic parish filters, enter part of a name, then select an option from the list. Switch between list and grid views and use the navigation above or below the list. Select a name to open the entry text and metadata, or the scan link to view the source page. Subentries are labelled as parts of collective entries and inherit their volume and page from the collective entry. Information presence filters refer to metadata annotations — a missing annotation does not establish that an object was absent from a locality.",
    helpChatTitle: "Conversation", helpChatText: "Ask a question about the dictionary. Answers are based on retrieved entry passages and include citations to the sources. Open cited entries to verify an answer. You can ask follow-up questions about earlier answers. “Download PDF” saves the conversation with its sources; “Clear conversation” removes it from this browser tab. If the local model is unavailable, the current question, a short conversation history, and retrieved passages are sent to OpenAI; the application identifies answers generated this way. The conversation is not intended to produce exhaustive lists of every locality.",
    closeHelp: "Close help", dictionaryEntry: "Dictionary entry", openScan: "Open page scan", scan: "Scan",
    closeEntry: "Close entry", entryMetadata: "Entry metadata", entryType: "Type", localityType: "Settlement type",
    locationDescription: "Location description", catholicParish: "Catholic parish", otherParish: "Other parish", religiousSites: "Religious sites",
    populationStatistics: "Population", dwellingStatistics: "Number of houses", religiousStructure: "Religious composition",
    industry: "Industry", mills: "Mills", archaeology: "Archaeology", nameVariants: "Name variants",
    yes: "Yes", no: "No", collectiveEntry: "Collective entry: {name}", openCollective: "Open collective entry",
    searching: "Searching…", rankingScore: "Relevance score",
    chatContextTruncated: "The input length limit was reached. Some accepted sources were shortened or omitted.",
    chatVerifyIncomplete: "The verification time limit was reached. The answer uses the sources accepted so far.",
    deeperAnalysis: "Deeper analysis",
    deeperAnalysisTooltip: "Enables additional model reasoning when preparing the final answer. It may help with complex questions, but does not guarantee greater accuracy.",
    chatVerifyHint: "(increases answer preparation time)",
    verifyResults: "Additional result verification", verifyHint: "Note: increases search time",
    searchingVerified: "Searching and verifying results — please wait…",
    verifiedCount: "Accepted results: {count}", verificationIncomplete: "Verification was not completed. You can continue on the next page.",
    relevanceKeep: "{model}: would keep", relevanceReject: "{model}: would reject",
    relevanceUnavailable: "{model}: assessment unavailable", relevanceBudget: "{model}: skipped — time limit",
    relevanceSkippedError: "{model}: skipped after an earlier assessment failed",
    relevanceEvidence: "Passage assessed by {model} (diagnostic)",
    relevanceTime: "request time: {seconds} s", relevanceCached: "cached assessment",
    resultsRange: "Results {start}–{end} · about {total} hits",
    resultsRangeLimited: "Results {start}–{end} · browsing is limited to the first {limit} results",
    noResults: "No results",
    notFoundTitle: "No entries found", noResultsAdvice: "Try different search terms or change the filters.",
    searchFailedTitle: "Search results are unavailable", serviceRetry: "Check the service connection and try again.",
    resultPage: "Page {page}", volumePage: "Vol. {volume} · p. {page}", volumePart1: "pt. 1", volumePart2: "pt. 2", districtPrefix: "District {name}",
    volumeShort: "vol. {volume}", pageShort: "p. {page}",
    collectiveItem: "Part of a collective entry{number}", scanPage: "Page scan ↗", filterLoadFailed: "Filter lists could not be loaded. Search is still available.",
    communeMatches: "Found {count} names; showing the first 100.",
    chatPhase1: "Analyzing the question and conversation context…", chatPhase2: "Searching entries and source passages…",
    chatPhase3: "Selecting sources relevant to the question…", chatPhase4: "Sending selected passages to the model…",
    answerPreparationTime: "Answer preparation time: {seconds} s",
    chatSupplementarySearch: "Searching for additional sources to supplement the answer…",
    chatPhaseWait: "The model is reviewing the sources. A longer answer may take a moment…",
    chatUnavailable: "The conversation service is unavailable", noStream: "No response stream was received",
    openaiGenerating: "OpenAI is generating the answer…", retryGenerating: "The model is generating a retry…",
    modelGenerating: "The model is preparing an answer from the sources…", outputRetry: "The initial token limit was reached. Retrying with a larger limit…",
    switchOpenAI: "The local model did not finish. Switching to OpenAI…", interrupted: "The answer was interrupted",
    answerInterrupted: "The response was interrupted", answerHeading: "Answer", sourcesHeading: "Sources",
    openSourceScan: "Scan ↗", preparePdfFailed: "Could not prepare the PDF", defaultPdfName: "sgkp-conversation.pdf",
    openaiAnswerNotice: "Answer generated by OpenAI ({model}) because the local model was unavailable.",
    entryId: "ID: {id} · vol. {volume}, p. {page}{number}", entryNumber: " · item {number}",
    entryScanAria: "Open page scan", answerLabel: "Answer", filtersActive: "Source filters: {count}",
    serviceUnavailable: "The service is unavailable", badServerResponse: "Invalid server response",
    http503: "The service is temporarily unavailable (HTTP 503). Please try again shortly.",
    http502: "The gateway did not receive a valid application response (HTTP 502). Please try again.",
    http504: "The gateway timed out waiting for the application (HTTP 504). Please try again.",
    conversationServiceUnavailable: "The conversation service is unavailable", noResponseStream: "No response stream was received",
    responseInterrupted: "The response was interrupted", couldNotPreparePdf: "Could not prepare the PDF",
    sourceFallback: "Source"
  }
};
// Add new examples here, with corresponding Polish and English UI_COPY strings.
const EXAMPLE_GROUPS = [
  {category: "places", label: "examplesPlaces", questions: ["exampleKingdom", "exampleSettlements", "exampleZawady", "exampleKononowicze", "exampleBarczaca"]},
  {category: "economy", label: "examplesEconomy", questions: ["exampleGlassworks", "exampleOil", "exampleZyrardow"]},
  {category: "heritage", label: "examplesHeritage", questions: ["exampleArchaeology"]},
  {category: "health", label: "examplesHealth", questions: ["exampleSpas"]},
  {category: "counts", label: "examplesCounts", questions: ["exampleReligiousCount", "exampleSpasCount", "exampleLibrariesCount", "exampleCustomsCount"]},
];
let currentLanguage = "pl";
const state = { page: 1, hasNext: false, entry: null, highlight: null, request: 0, gminas: [], parishes: [], chatBusy: false,
  chatController: null, chatGeneration: 0, chatHistory: [], exportTurns: [], searchData: null, searchOffsets: {},
  browsePage: 1, browseHasNext: false, browseData: null, browseRequest: 0, browseView: "list", showParentContext: true,
  filtersCollapsed: window.matchMedia("(max-width: 760px)").matches };

function setText(node, value) { node.textContent = value == null ? "" : String(value); }
function t(key, values = {}) {
  const template = UI_COPY[currentLanguage][key] ?? UI_COPY.pl[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => values[name] ?? "");
}
function displayVolume(value) {
  const number = Number.parseInt(value, 10);
  if (!Number.isFinite(number)) return value || "—";
  if (number === 15) return `15 ${t("volumePart1")}`;
  if (number === 16) return `15 ${t("volumePart2")}`;
  return String(number);
}
function volumeValue(value) {
  const text = String(value ?? "").trim();
  const number = Number(text);
  return /^\d{1,2}$/.test(text) && number >= 1 && number <= 16
    ? String(number).padStart(2, "0") : text;
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
  document.querySelectorAll("[data-preparation-seconds]").forEach(renderPreparationTime);
  document.querySelectorAll("[data-i18n-placeholder]").forEach(node => node.placeholder = t(node.dataset.i18nPlaceholder));
  document.querySelectorAll("[data-i18n-aria]").forEach(node => node.setAttribute("aria-label", t(node.dataset.i18nAria)));
  document.querySelectorAll("[data-i18n-title]").forEach(node => node.title = t(node.dataset.i18nTitle));
  const volumeFilter = $("tom");
  const selectedVolume = volumeFilter.value;
  for (const option of Array.from(volumeFilter.options).slice(1)) option.textContent = displayVolume(option.value);
  volumeFilter.value = selectedVolume;
  document.querySelectorAll("[data-language]").forEach(button => {
    const active = button.dataset.language === currentLanguage;
    button.setAttribute("aria-pressed", String(active));
  });
  $("theme-toggle")?.setAttribute("aria-label", currentLanguage === "en"
    ? (document.documentElement.dataset.theme === "dark" ? "Dark theme. Switch to light theme" : "Light theme. Switch to dark theme")
    : (document.documentElement.dataset.theme === "dark" ? "Tryb nocny. Włącz tryb dzienny" : "Tryb dzienny. Włącz tryb nocny"));
  updateFilterToggleLabel();
  modeUi();
  if (state.gminas.length) renderGminaChoices();
  if (state.parishes.length) renderParishChoices();
  if (state.searchData) renderSearchResults(state.searchData);
  if (state.browseData) renderBrowseResults(state.browseData);
  if (state.entry) renderEntry();
  if ($("examples-dialog").open) renderExamples();
  if (persist) {
    try { localStorage.setItem(LANGUAGE_STORAGE_KEY, currentLanguage); } catch { /* Keep current language for this page. */ }
  }
}
function renderExamples() {
  const query = $("examples-search").value.trim().toLocaleLowerCase(currentLanguage);
  const category = $("examples-category").value;
  const list = $("examples-list");
  list.replaceChildren();
  for (const group of EXAMPLE_GROUPS) {
    if (category && category !== group.category) continue;
    const questions = group.questions.filter(key => t(key).toLocaleLowerCase(currentLanguage).includes(query));
    if (!questions.length) continue;
    const section = element("section");
    section.append(element("h3", t(group.label)));
    for (const key of questions) {
      const button = element("button", t(key), "example-choice");
      button.type = "button";
      button.addEventListener("click", () => {
        $("question").value = t(key);
        $("examples-dialog").close();
        $("question").focus();
        $("question").scrollIntoView({block: "center", behavior: "smooth"});
      });
      section.append(button);
    }
    list.append(section);
  }
  $("examples-empty").hidden = list.children.length > 0;
  list.scrollTop = 0;
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
async function responseError(response, fallbackKey = "serviceUnavailable") {
  try {
    const data = await response.json();
    if (typeof data?.error === "string" && data.error.trim()) return translatedError(data.error, fallbackKey);
  } catch { /* Gateways can return HTML or an empty body for HTTP errors. */ }
  if ([502, 503, 504].includes(response.status)) return t("http" + response.status);
  return `${t(fallbackKey)} (HTTP ${response.status})`;
}
async function api(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await responseError(response));
  let data;
  try { data = await response.json(); }
  catch { throw new Error(t("badServerResponse")); }
  return data;
}
function selectedMode() { return document.querySelector('input[name="mode"]:checked').value; }
function localityOnly() { return document.querySelector('input[name="locality"]:checked').value === "only"; }
function activeFilters() {
  const selected = {};
  if (document.querySelector('input[name="locality"]:checked').value === "nonlocalities") {
    selected.jest_miejscowoscia = "false";
    if ($("typ").value) selected.typ = $("typ").value;
  }
  for (const id of ["tom", "powiat_ujednolicony"]) {
    if ($(id).value) selected[id] = $(id).value;
  }
  if (localityOnly()) {
    selected.jest_miejscowoscia = "true";
    if ($("kingdom-only").checked) selected["królestwo_polskie"] = "true";
    for (const id of ["typ_punktu_osadniczego", "gmina", "gubernia_ujednolicona"]) {
      if ($(id).value) selected[id] = $(id).value;
    }
    if (!$("parish-filter").hidden && $("parafia_katolicka").value) selected.parafia_katolicka = $("parafia_katolicka").value;
  }
  if (!$("information-options").hidden) {
    document.querySelectorAll("[data-presence-filter]:checked").forEach(input =>
      { if (!input.disabled) selected[input.id] = "true"; });
  }
  return selected;
}
function updateFilterToggleLabel() {
  const count = Object.keys(activeFilters()).length;
  const expanded = !state.filtersCollapsed;
  document.querySelectorAll(".filter-workspace").forEach(workspace =>
    workspace.classList.toggle("filters-collapsed", !expanded));
  document.querySelectorAll("[data-filter-toggle]").forEach(button => {
    button.setAttribute("aria-expanded", String(expanded));
    const label = expanded ? t("mobileHideFilters") : t("mobileShowFilters");
    button.setAttribute("aria-label", label);
    button.title = label;
    setText(button.querySelector(".filter-toggle-icon"), expanded ? "‹" : "›");
    setText(button.querySelector(".filter-toggle-label"),
      t("filters") + (count ? " (" + count + ")" : ""));
  });
  $("filter-panel").hidden = !expanded;
}
function updateLocalityUi(clear = false) {
  const enabled = localityOnly();
  const otherEnabled = document.querySelector('input[name="locality"]:checked').value === "nonlocalities";
  $("other-entry-options").disabled = !otherEnabled;
  $("other-entry-hint").hidden = otherEnabled;
  if (!otherEnabled && clear) $("typ").value = "";
  $("locality-options").disabled = !enabled;
  $("locality-hint").hidden = enabled;
  if (!enabled && clear) {
    $("kingdom-only").checked = false;
    for (const id of ["typ_punktu_osadniczego", "gmina", "gubernia_ujednolicona", "gmina-search", "parafia_katolicka", "parafia_katolicka-search"]) $(id).value = "";
    renderGminaChoices();
    renderParishChoices();
  }
  updateFilterToggleLabel();
}
function modeUi() {
  const mode = selectedMode();
  $("ratio-line").classList.toggle("visible", mode === "hybrid");
  $("verify-line").hidden = mode !== "semantic";
  $("query").placeholder = t(mode === "semantic" ? "semanticQueryPlaceholder" : "queryPlaceholder");
}
function viewFromHash() {
  if (["#konwersacja", "#asystent"].includes(location.hash)) return "konwersacja";
  if (["#przegladanie", "#browse"].includes(location.hash)) return "przegladanie";
  return "wyszukiwanie";
}
function capturePanelFilters() {
  return Array.from($("filter-panel").querySelectorAll("input, select"), node => ({
    id: node.id, name: node.name, value: node.value, checked: node.checked, type: node.type,
  }));
}
function restorePanelFilters(saved, browsing) {
  for (const node of $("filter-panel").querySelectorAll("input, select")) {
    const previous = saved?.find(item => node.id ? item.id === node.id : item.name === node.name && item.value === node.value);
    if (node.type === "checkbox" || node.type === "radio") {
      node.checked = previous ? previous.checked : node.type === "radio" && node.value === (browsing ? "all" : "only");
    } else {
      const restored = previous ? previous.value : node.id === "tom" && browsing ? "01" : "";
      const value = node.id === "tom" ? volumeValue(restored) : restored;
      if (node.tagName === "SELECT" && value && !Array.from(node.options).some(option => option.value === value)) {
        const option = element("option", node.id === "tom" ? displayVolume(value) : value);
        option.value = value;
        node.append(option);
      }
      node.value = value;
    }
  }
  renderGminaChoices();
  renderParishChoices();
  updateLocalityUi();
}
function refreshFilteredView() {
  if (!$("browse-view").hidden) loadBrowse(1);
  else if (!$("search-view").hidden && $("query").value.trim()) search(1);
}
function switchView(view, updateUrl = true) {
  const selected = view === "konwersacja" || view === "asystent" ? "konwersacja"
    : view === "przegladanie" ? "przegladanie" : "wyszukiwanie";
  const scope = selected === "przegladanie" ? "browse" : "shared";
  const previousScope = state.filterScope || "shared";
  if (scope !== previousScope) {
    state[previousScope + "PanelFilters"] = capturePanelFilters();
    restorePanelFilters(state[scope + "PanelFilters"], scope === "browse");
    state.filterScope = scope;
  }
  $("search-view").hidden = selected !== "wyszukiwanie";
  $("assistant-view").hidden = selected !== "konwersacja";
  $("browse-view").hidden = selected !== "przegladanie";
  $("tab-search").setAttribute("aria-selected", String(selected === "wyszukiwanie"));
  $("tab-assistant").setAttribute("aria-selected", String(selected === "konwersacja"));
  $("tab-browse").setAttribute("aria-selected", String(selected === "przegladanie"));
  $(selected === "przegladanie" ? "browse-filter-slot" : selected === "konwersacja" ? "assistant-filter-slot" : "search-filter-slot").append($("filter-panel"));
  $("browse-name-filter").hidden = selected !== "przegladanie";
  if (updateUrl) history.replaceState(null, "", location.pathname + location.search + "#" + selected);
}
function queryParams(page) {
  const params = new URLSearchParams({ q: $("query").value.trim(), mode: selectedMode(), page: String(page) });
  params.set("language", currentLanguage);
  if (selectedMode() === "hybrid") params.set("ratio", String(Number($("ratio").value) / 100));
  if (selectedMode() === "semantic") params.set("verify", String($("verify-results").checked));
  if (state.searchOffsets[page] !== undefined) params.set("candidate_offset", String(state.searchOffsets[page]));
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
  if (hit.snippet_is_markdown) {
    paragraph.classList.add("browse-preview");
    appendAnswerInline(paragraph, hit.snippet);
    return paragraph;
  }
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
  open.addEventListener("click", () => openEntry(hit.ID, undefined, undefined, $("browse-view").hidden));
  title.append(open);
  card.append(title);
  const meta = element("div", undefined, "result-meta");
  meta.append(element("span", t("volumePage", {volume: displayVolume(hit.tom), page: hit.strona || "—"})));
  if (Number.isFinite(Number(hit.ranking_score))) {
    const score = Number(hit.ranking_score).toLocaleString(currentLanguage === "en" ? "en" : "pl-PL", {
      minimumFractionDigits: 3, maximumFractionDigits: 3,
    });
    meta.append(element("span", `${t("rankingScore")}: ${score}`));
  }
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
  if (hit.relevance_diagnostic) {
    const diagnostic = hit.relevance_diagnostic;
    const label = diagnostic.status === "ok" ?
      `${t(diagnostic.would_reject ? "relevanceReject" : "relevanceKeep", {model: diagnostic.model || "tev1"})} · ${Number(diagnostic.score).toFixed(3)}` :
      t(diagnostic.status === "budget_exceeded" ? "relevanceBudget" :
        diagnostic.status === "skipped_after_error" ? "relevanceSkippedError" : "relevanceUnavailable", {model: diagnostic.model || "tev1"});
    const error = diagnostic.error_type ? ` (${diagnostic.error_type}${diagnostic.http_status ? ", HTTP " + diagnostic.http_status : ""})` : "";
    const timing = Number.isFinite(diagnostic.decision_seconds) ? " · " + t("relevanceTime", {
      seconds: diagnostic.decision_seconds.toLocaleString(currentLanguage === "en" ? "en" : "pl-PL", {
        minimumFractionDigits: 2, maximumFractionDigits: 2,
      }),
    }) : "";
    const cached = diagnostic.cache_hit ? " · " + t("relevanceCached") : "";
    card.append(element("p", label + error + timing + cached, "field-hint"));
    if (diagnostic.evidence) {
      const details = element("details");
      details.append(element("summary", t("relevanceEvidence", {model: diagnostic.model || "tev1"})), element("p", diagnostic.evidence));
      card.append(details);
    }
  }
  return card;
}
function browseGridCard(hit) {
  const card = element("article", undefined, "result-card browse-grid-card");
  const title = element("h3");
  const open = element("button", hit.nazwa || hit.ID);
  open.type = "button";
  open.addEventListener("click", () => openEntry(hit.ID, undefined, undefined, $("browse-view").hidden));
  title.append(open);
  card.append(title);
  const meta = element("div", undefined, "result-meta");
  meta.append(element("span", t("volumePage", {volume: displayVolume(hit.tom), page: hit.strona || "—"})));
  if (hit.url_skanu) meta.append(externalLink(t("scanPage"), hit.url_skanu));
  card.append(meta);
  if (hit.parent_id) meta.append(element("span", t("collectiveItem", {number: hit.nr ? " · " + hit.nr : ""})));
  const values = (Array.isArray(hit.typ_punktu_osadniczego) && hit.typ_punktu_osadniczego.length
      ? hit.typ_punktu_osadniczego
      : Array.isArray(hit.typ) ? hit.typ : hit.typ ? [hit.typ] : []);
  if (values.length) {
    const types = element("div", undefined, "browse-grid-types");
    for (const value of values) types.append(element("span", typeof value === "string" ? value : JSON.stringify(value), "tag"));
    card.append(types);
  }
  return card;
}
function setBrowseView(view) {
  state.browseView = view === "grid" ? "grid" : "list";
  $("browse-view-list").setAttribute("aria-pressed", String(state.browseView === "list"));
  $("browse-view-grid").setAttribute("aria-pressed", String(state.browseView === "grid"));
  if (state.browseData) renderBrowseResults(state.browseData);
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
    const beyondWindow = Number(data.estimated_total_hits) > Number(data.max_result_window);
    if (data.verification_mode === "filter") {
      setText($("status"), t("verifiedCount", {count: data.hits.length}));
    } else if (data.mode === "semantic" && beyondWindow) {
      setText($("status"), t("resultsRangeLimited", {start, end, limit: Number(data.max_result_window).toLocaleString(currentLanguage === "en" ? "en" : "pl-PL")}));
    } else {
      setText($("status"), t("resultsRange", {start, end, total: data.estimated_total_hits}));
    }
    for (const hit of data.hits) $("results").append(resultCard(hit));
    $("pagination").hidden = false;
  } else {
    setText($("status"), t("noResults"));
    $("results").append(makeEmpty(t("notFoundTitle"), t("noResultsAdvice")));
    $("pagination").hidden = !data.has_next && data.page <= 1;
  }
  if (data.verification_incomplete) {
    setText($("status"), t("verifiedCount", {count: data.hits.length}) + " · " + t("verificationIncomplete"));
  }
}
function clearSearchResults() {
  // Invalidate pending responses so they cannot restore cleared results.
  ++state.request;
  state.searchData = null;
  state.searchOffsets = {};
  state.page = 1;
  state.hasNext = false;
  $("status").classList.remove("is-searching", "error");
  setText($("status"), t("startSearch"));
  $("results").setAttribute("aria-busy", "false");
  const empty = makeEmpty(t("startByName"), t("enterQuery"));
  empty.querySelector("h3").dataset.i18n = "startByName";
  empty.querySelector("p").dataset.i18n = "enterQuery";
  $("results").replaceChildren(empty);
  $("pagination").hidden = true;
  $("prev").disabled = true;
  $("next").disabled = true;
  setText($("page-label"), t("resultPage", {page: 1}));
  const params = new URLSearchParams(location.search);
  for (const key of ["q", "page", "candidate_offset"]) params.delete(key);
  const query = params.toString();
  history.replaceState(null, "", location.pathname + (query ? "?" + query : "") + location.hash);
}
async function search(page = 1) {
  if (page === 1) state.searchOffsets = {};
  const params = queryParams(page);
  if (!params.get("q")) { clearSearchResults(); return; }
  const current = ++state.request;
  state.searchData = null;
  setText($("status"), t(params.get("verify") === "true" ? "searchingVerified" : "searching"));
  $("status").classList.add("is-searching");
  $("results").setAttribute("aria-busy", "true");
  $("status").classList.remove("error");
  $("results").replaceChildren();
  $("pagination").hidden = true;
  try {
    const data = await api("api/v1/search?" + params);
    if (current !== state.request) return;
    state.searchData = data;
    if (data.next_candidate_offset !== undefined) state.searchOffsets[page + 1] = data.next_candidate_offset;
    renderSearchResults(data);
    history.replaceState(null, "", location.pathname + "?" + params + (location.hash || "#wyszukiwanie"));
  } catch (error) {
    if (current !== state.request) return;
    setText($("status"), translatedError(error.message));
    $("status").classList.add("error");
    $("results").append(makeEmpty(t("searchFailedTitle"), t("serviceRetry")));
  } finally {
    if (current === state.request) {
      $("status").classList.remove("is-searching");
      $("results").setAttribute("aria-busy", "false");
    }
  }
}
function renderBrowseResults(data) {
  state.browsePage = data.page;
  state.browseHasNext = data.has_next;
  const lastPage = Math.max(1, Math.ceil(data.estimated_total_hits / data.page_size));
  for (const suffix of ["", "-top"]) {
    $("browse-first" + suffix).disabled = data.page <= 1;
    $("browse-prev" + suffix).disabled = data.page <= 1;
    $("browse-next" + suffix).disabled = !data.has_next;
    $("browse-last" + suffix).disabled = data.page >= lastPage;
    setText($("browse-page-label" + suffix), t("resultPage", {page: data.page}));
    $("browse-pagination" + suffix).hidden = !data.hits.length;
  }
  $("browse-results").replaceChildren();
  $("browse-results").classList.toggle("browse-grid", state.browseView === "grid");
  if (data.hits.length) {
    const start = (data.page - 1) * data.page_size + 1;
    const end = start + data.hits.length - 1;
    setText($("browse-status"), t("browseRange", {start, end, total: data.estimated_total_hits}));
    for (const hit of data.hits) {
      if (state.browseView === "grid") {
        $("browse-results").append(browseGridCard(hit));
        continue;
      }
      const card = resultCard({...hit, typ_punktu_osadniczego: [], snippet: hit.preview,
        snippet_is_markdown: hit.preview_is_markdown});
      const localityTypes = Array.isArray(hit.typ_punktu_osadniczego)
        ? hit.typ_punktu_osadniczego : hit.typ_punktu_osadniczego ? [hit.typ_punktu_osadniczego] : [];
      const values = localityTypes.length ? localityTypes : Array.isArray(hit.typ) ? hit.typ : hit.typ ? [hit.typ] : [];
      if (values.length) {
        const type = element("div", undefined, "result-meta");
        type.style.marginTop = "10px";
        for (const value of values) type.append(element("span", typeof value === "string" ? value : JSON.stringify(value), "tag"));
        card.append(type);
      }
      $("browse-results").append(card);
    }
  } else {
    setText($("browse-status"), t("noResults"));
    $("browse-results").append(makeEmpty(t(data.name ? "browseNameEmpty" : "browseEmpty"), ""));
  }
}
async function loadBrowse(page = 1) {
  clearTimeout(state.browseFilterTimer);
  const current = ++state.browseRequest;
  state.browseData = null;
  setText($("browse-status"), t("browseLoading"));
  $("browse-status").classList.remove("error");
  $("browse-results").replaceChildren();
  $("browse-pagination").hidden = true;
  $("browse-pagination-top").hidden = true;
  const params = new URLSearchParams({...activeFilters(), tom: $("tom").value, page: String(page)});
  const name = $("browse-name").value.trim();
  if (name) params.set("name", name);
  try {
    const data = await api("api/v1/browse?" + params);
    if (current !== state.browseRequest) return;
    state.browseData = data;
    renderBrowseResults(data);
  } catch (error) {
    if (current !== state.browseRequest) return;
    setText($("browse-status"), translatedError(error.message));
    $("browse-status").classList.add("error");
    $("browse-pagination-top").hidden = true;
    $("browse-results").append(makeEmpty(t("searchFailedTitle"), t("serviceRetry")));
  }
}
function renderGminaChoices() {
  renderNamedFilterChoices("gmina", state.gminas, "allCommunes", "communeMatches", "communeHint");
}
function renderParishChoices() {
  renderNamedFilterChoices("parafia_katolicka", state.parishes, "allParishes", "parishMatches", "parishHint");
}
function renderNamedFilterChoices(id, values, allKey, matchesKey, hintKey) {
  const select = $(id);
  const selected = select.value;
  const query = $(id + "-search").value.trim().toLocaleLowerCase("pl");
  const matched = query ? values.filter(value => value.toLocaleLowerCase("pl").includes(query)) : values;
  const visible = matched.slice(0, 100);
  if (selected && !visible.includes(selected)) visible.unshift(selected);
  select.replaceChildren();
  const all = element("option", t(allKey));
  all.value = "";
  select.append(all);
  for (const value of visible) {
    const option = element("option", value);
    option.value = value;
    select.append(option);
  }
  select.value = selected && visible.includes(selected) ? selected : "";
  setText($(id + "-hint"), query ? t(matchesKey, {count: matched.length}) : t(hintKey));
}
function fillSelect(id, values) {
  const select = $(id);
  const selected = id === "tom" ? volumeValue(select.value) : select.value;
  const all = select.options[0];
  select.replaceChildren(all);
  const unique = [...new Set(values.map(value => id === "tom" ? volumeValue(value) : value))];
  for (const value of unique) {
    if (!value) continue;
    const option = element("option", id === "tom" ? displayVolume(value) : value);
    option.value = value;
    select.append(option);
  }
  select.value = unique.includes(selected) ? selected : "";
}
async function loadFilterOptions() {
  try {
    const data = await api("api/v1/filter-options");
    const options = data.options || {};
    $("information-options").hidden = !data.presence_filters_available;
    document.querySelectorAll("[data-presence-filter]").forEach(input => {
      const available = Array.isArray(data.presence_filter_fields)
        ? data.presence_filter_fields.includes(input.id)
        : data.presence_filters_available && ["has_obiekty_sakralne", "has_szkoły", "has_młyny",
            "has_przemysłowe", "has_zabytki", "has_archeo", "has_opieka_zdrowotna",
            "has_biblioteki", "has_uzdrowiska"].includes(input.id);
      input.disabled = !available;
      input.closest("label").hidden = !available;
    });
    $("parish-filter").hidden = !data.catholic_parish_filter_available;
    for (const id of optionFields) fillSelect(id, options[id] || []);
    state.gminas = (options.gmina || []).filter(value =>
      typeof value === "string" && /^\p{L}/u.test(value.trimStart()));
    renderGminaChoices();
    state.parishes = (options.parafia_katolicka || []).filter(value =>
      typeof value === "string" && /^\p{L}/u.test(value.trimStart()));
    renderParishChoices();
  } catch {
    fillSelect("tom", Array.from({length: 16}, (_, index) => String(index + 1).padStart(2, "0")));
    setText($("filter-options-status"), t("filterLoadFailed"));
  }
}
function clearFilters() {
  for (const id of [...optionFields, "gmina-search", "gmina", "parafia_katolicka", "parafia_katolicka-search"]) $(id).value = "";
  $("kingdom-only").checked = false;
  document.querySelectorAll("[data-presence-filter]").forEach(input => input.checked = false);
  $("browse-name").value = "";
  document.querySelector('input[name="locality"][value="' + ($("browse-view").hidden ? "only" : "all") + '"]').checked = true;
  updateLocalityUi();
  renderGminaChoices();
  renderParishChoices();
  updateFilterToggleLabel();
  refreshFilteredView();
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
function structuredMetadataNode(field, value, entryName) {
  const groups = Array.isArray(value) ? value : [value];
  const result = element("div", undefined, "metadata-groups");
  for (const group of groups) {
    if (!group || typeof group !== "object" || Array.isArray(group)) continue;
    const section = element("div", undefined, "metadata-group");
    const scope = typeof group.dotyczy === "string" && group.dotyczy.trim().toLocaleLowerCase("pl-PL") === "główna miejscowość"
      ? entryName : group.dotyczy;
    if (scope) section.append(element("strong", scope, "metadata-group-title"));
    const list = element("ul", undefined, "metadata-detail-list");
    let details = [];
    if (field === "parafia_inna") {
      details = Array.isArray(group) ? group : [group];
      for (const detail of details) {
        if (typeof detail === "string") list.append(element("li", detail));
        else if (detail && typeof detail === "object") {
          const parish = detail.nazwa_parafii || detail.nazwa || "";
          const confession = detail.wyznanie || "";
          const text = [confession, parish].filter(Boolean).join(": ");
          if (text) list.append(element("li", text));
        }
      }
    } else if (field === "ludność_wyznanie") {
      details = Array.isArray(group.struktura_wyznaniowa) ? group.struktura_wyznaniowa : [];
      for (const detail of details) {
        if (!detail || typeof detail !== "object") continue;
        const denomination = detail.wyznanie_ocr || detail.wyznanie || "";
        const count = detail.liczba;
        const text = [denomination, count !== null && count !== undefined && count !== "" ? String(count) : ""]
          .filter(Boolean).join(": ");
        if (text) list.append(element("li", text));
      }
    } else {
      details = Array.isArray(group.liczba) ? group.liczba : [group.liczba];
      for (const detail of details) {
        if (detail === null || detail === undefined || detail === "") continue;
        if (typeof detail === "object") {
          const number = detail.liczba;
          if (number === null || number === undefined || number === "") continue;
          const date = typeof detail.data === "string" && detail.data.trim().toLocaleLowerCase("pl-PL") === "obecnie"
            ? "" : detail.data;
          list.append(element("li", date ? `${date}: ${number}` : String(number)));
        } else list.append(element("li", String(detail)));
      }
    }
    if (list.children.length) section.append(list);
    if (section.children.length) result.append(section);
  }
  return result.children.length ? result : null;
}
function renderEntry() {
  const entry = state.entry;
  setText($("entry-title"), entry.nazwa);
  setText($("entry-meta"), t("entryId", {id: entry.ID, volume: displayVolume(entry.tom), page: entry.strona,
    number: entry.nr ? t("entryNumber", {number: entry.nr}) : ""}));
  $("scan-link").hidden = !entry.url_skanu;
  if (entry.url_skanu) $("scan-link").href = entry.url_skanu;
  const localityType = entry.metadata.typ_punktu_osadniczego;
  const isLocality = Array.isArray(localityType) ? localityType.length > 0 : Boolean(localityType);
  const labels = {
    ...(isLocality ? {typ_punktu_osadniczego: t("localityType")} : {typ: t("entryType")}),
    warianty_nazw: t("nameVariants"),
    powiat_ujednolicony: t("district"), gmina: t("commune"), gubernia_ujednolicona: t("governorate"),
    opis_lokalizacji: t("locationDescription"),
    parafia_katolicka: t("catholicParish"), parafia_inna: t("otherParish"),
    obiekty_sakralne: t("religiousSites"), przemysłowe: t("industry"), młyny: t("mills"),
    archeo: t("archaeology"), zabytki: t("presenceMonuments"), szkoły: t("presenceSchools"),
    biblioteki: t("presenceLibraries"), opieka_zdrowotna: t("presenceHealthcare"),
    uzdrowiska: t("presenceSpas"), celne: t("presenceCustoms"),
    budownictwo_palacowe: t("presenceManors"), poczta: t("presencePost"),
    stacje_drogi_zelaznej: t("presenceRailway"), handel: t("presenceTrade"), rzemioslo: t("presenceCrafts"),
    urzędy: t("presenceOffices"),
    architektura_krajobrazu: t("presenceGardens"),
    hodowla: t("presenceBreeding"),
    nekropolie: t("presenceCemeteries"),
    dobroczynnosc: t("presenceCharity"),
    sądy: t("presenceCourts"),
    wojsko: t("presenceMilitary"),
    żegluga: t("presenceNavigation"),
    kolekcjonerstwo: t("presenceCollections"),
    drukarnie: t("presencePrinting"),
    muzealnictwo: t("presenceMuseums"),
    księgarnie: t("presenceBookshops"),
    bursa: t("presenceBursas"),
    królestwo_polskie: t("kingdomOnly"),
    l_mk_statystyka: t("populationStatistics"),
    l_dm_statystyka: t("dwellingStatistics"), ludność_wyznanie: t("religiousStructure")
  };
  $("entry-fields-list").replaceChildren();
  for (const [key, label] of Object.entries(labels)) {
    let value = entry.metadata[key];
    if (value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length)) continue;
    if (["parafia_inna", "l_mk_statystyka", "l_dm_statystyka", "ludność_wyznanie"].includes(key)) {
      const formatted = structuredMetadataNode(key, value, entry.nazwa);
      if (!formatted) continue;
      const definition = element("dd");
      definition.append(formatted);
      $("entry-fields-list").append(element("dt", label), definition);
      continue;
    }
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
  $("parent-context").hidden = !entry.parent || !state.showParentContext;
  if (entry.parent && state.showParentContext) {
    $("parent-context").replaceChildren(element("h3", t("collectiveEntry", {name: entry.parent.nazwa})));
    const button = element("button", t("openCollective"), "button button-outline");
    button.type = "button";
    button.addEventListener("click", () => openEntry(entry.parent.ID));
    $("parent-context").append(button);
  }
}
async function openEntry(id, start, end, showParentContext = true) {
  try {
    state.entry = await api("api/v1/entries/" + encodeURIComponent(id));
    state.highlight = Number.isInteger(start) && Number.isInteger(end) ? [start, end] : null;
    state.showParentContext = showParentContext;
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
      body: JSON.stringify({question, filters, history, language: currentLanguage, verify: $("chat-verify-results").checked, deeper_analysis: $("chat-deeper-analysis").checked}), signal
    });
    if (!response.ok) {
      throw new Error(await responseError(response, "conversationServiceUnavailable"));
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
        if (type === "progress") {
          clearInterval(progressTimer);
          setText(statusNode, data.phase === "supplementary_search" ? t("chatSupplementarySearch") : t("chatPhase4"));
        }
        else if (type === "delta") {
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
            const location = [source.tom ? t("volumeShort", {volume: displayVolume(source.tom)}) : "", source.strona ? t("pageShort", {page: source.strona}) : ""].filter(Boolean).join(", ");
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
function renderPreparationTime(node) {
  const seconds = Number(node.dataset.preparationSeconds);
  setText(node, t("answerPreparationTime", {seconds: new Intl.NumberFormat(
    currentLanguage === "en" ? "en-GB" : "pl-PL", {
      minimumFractionDigits: 1, maximumFractionDigits: 1
    }).format(seconds)}));
}
function makeTurn(question) {
  const turn = element("article", undefined, "turn");
  turn.append(element("div", question, "question-bubble"));
  const card = element("div", undefined, "answer-card");
  const header = element("div", undefined, "answer-header");
  header.append(element("h2", t("answerHeading")));
  const status = element("p", t("chatPhase1"), "answer-status is-working");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.setAttribute("aria-atomic", "true");
  const answer = element("div", undefined, "answer-text");
  const timing = element("p", undefined, "answer-timing");
  timing.hidden = true;
  header.append(timing);
  const heading = element("p", t("sourcesHeading"), "source-heading");
  heading.hidden = true;
  const sources = element("ol", undefined, "source-list");
  card.append(header, status, answer, heading, sources);
  turn.append(card);
  $("conversation").append(turn);
  return {turn, status, answer, timing, heading, sources};
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
      throw new Error(await responseError(response, "couldNotPreparePdf"));
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
      source_ids: (result.sources || []).flatMap(source => source.passage_ids || [source.passage_id]).filter(Boolean),
      source_names: (result.sources || []).map(source => source.nazwa)});
    state.chatHistory = state.chatHistory.slice(-CHAT_HISTORY_TURNS);
    state.exportTurns.push({question, answer: result.answer, provider: result.provider, model: result.model,
      sources: (result.sources || []).map(source => ({citation: source.citation, nazwa: source.nazwa,
        tom: source.tom, strona: source.strona}))});
    setText(nodes.status, [result.provider === "openai" ? t("openaiAnswerNotice", {model: result.model}) : "",
      result.verification_incomplete ? t("chatVerifyIncomplete") : "",
      result.context_truncated ? t("chatContextTruncated") : ""].filter(Boolean).join(" "));
    if (Number.isFinite(result.processing_seconds) && result.processing_seconds >= 0) {
      nodes.timing.dataset.preparationSeconds = String(result.processing_seconds);
      renderPreparationTime(nodes.timing);
      nodes.timing.hidden = false;
    }
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
  $("tab-browse").addEventListener("click", () => { switchView("przegladanie"); loadBrowse(1); });
  $("tab-search").parentElement.addEventListener("keydown", event => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const tabs = [
      {id: "tab-search", view: "wyszukiwanie"},
      {id: "tab-assistant", view: "konwersacja"},
      {id: "tab-browse", view: "przegladanie"}
    ];
    const current = tabs.findIndex(tab => $(tab.id).getAttribute("aria-selected") === "true");
    const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1
      : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    const next = tabs[nextIndex];
    switchView(next.view);
    if (next.view === "przegladanie") loadBrowse(1);
    $(next.id).focus();
  });
  window.addEventListener("hashchange", () => {
    const view = viewFromHash();
    switchView(view, false);
    if (view === "przegladanie") loadBrowse(1);
  });
  $("more-examples").addEventListener("click", () => {
    renderExamples();
    $("examples-dialog").showModal();
    $("examples-search").focus();
  });
  $("close-examples").addEventListener("click", () => $("examples-dialog").close());
  $("examples-search").addEventListener("input", renderExamples);
  $("examples-category").addEventListener("change", renderExamples);
  $("open-help").addEventListener("click", () => $("help-dialog").showModal());
  $("close-help").addEventListener("click", () => $("help-dialog").close());
  $("search-form").addEventListener("submit", event => { event.preventDefault(); search(1); });
  $("query").addEventListener("input", () => {
    if (!$("query").value.trim()) clearSearchResults();
  });
  $("prev").addEventListener("click", () => search(state.page - 1));
  $("next").addEventListener("click", () => search(state.page + 1));
  $("browse-name").addEventListener("input", () => loadBrowse(1));
  $("browse-view-list").addEventListener("click", () => setBrowseView("list"));
  $("browse-view-grid").addEventListener("click", () => setBrowseView("grid"));
  $("browse-first-top").addEventListener("click", () => loadBrowse(1));
  $("browse-prev-top").addEventListener("click", () => loadBrowse(state.browsePage - 1));
  $("browse-next-top").addEventListener("click", () => loadBrowse(state.browsePage + 1));
  $("browse-last-top").addEventListener("click", () => loadBrowse(Math.ceil(state.browseData.estimated_total_hits / state.browseData.page_size)));
  $("browse-first").addEventListener("click", () => loadBrowse(1));
  $("browse-prev").addEventListener("click", () => loadBrowse(state.browsePage - 1));
  $("browse-next").addEventListener("click", () => loadBrowse(state.browsePage + 1));
  $("browse-last").addEventListener("click", () => loadBrowse(Math.ceil(state.browseData.estimated_total_hits / state.browseData.page_size)));
  document.querySelectorAll("[data-clear-filters]").forEach(button =>
    button.addEventListener("click", clearFilters));
  document.querySelectorAll("[data-filter-toggle]").forEach(button =>
    button.addEventListener("click", () => {
      state.filtersCollapsed = !state.filtersCollapsed;
      updateFilterToggleLabel();
    }));
  for (const id of ["gmina", "parafia_katolicka"]) $(id + "-search").addEventListener("input", () => {
    const hadSelection = Boolean($(id).value);
    $(id).value = "";
    if (id === "gmina") renderGminaChoices(); else renderParishChoices();
    updateFilterToggleLabel();
    if (hadSelection) refreshFilteredView();
  });
  $("ratio").addEventListener("input", () => setText($("ratio-value"), $("ratio").value + "%"));
  $("ratio").addEventListener("change", () => { if ($("query").value.trim()) search(1); });
  $("verify-results").addEventListener("change", () => { if ($("query").value.trim()) search(1); });
  for (const input of document.querySelectorAll('input[name="mode"]')) input.addEventListener("change", () => { modeUi(); if ($("query").value.trim()) search(1); });
  for (const input of document.querySelectorAll('input[name="locality"]')) input.addEventListener("change", () => { updateLocalityUi(true); refreshFilteredView(); });
  document.querySelectorAll("[data-presence-filter]").forEach(input =>
    input.addEventListener("change", () => {
      updateFilterToggleLabel();
      refreshFilteredView();
    }));
  for (const id of [...optionFields, "gmina", "parafia_katolicka", "kingdom-only"]) $(id).addEventListener("change", () => { updateFilterToggleLabel(); refreshFilteredView(); });
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
  $("verify-results").checked = params.get("verify") !== "false";
  if (params.has("candidate_offset")) state.searchOffsets[Number(params.get("page") || 1)] = Number(params.get("candidate_offset"));
  setText($("ratio-value"), $("ratio").value + "%");
  modeUi();
  for (const id of optionFields) if (params.get(id)) $(id).value = id === "tom" ? volumeValue(params.get(id)) : params.get(id);
  if (params.get("gmina")) { $("gmina-search").value = params.get("gmina"); renderGminaChoices(); $("gmina").value = params.get("gmina"); }
  if (params.get("parafia_katolicka") && !$("parish-filter").hidden) { $("parafia_katolicka-search").value = params.get("parafia_katolicka"); renderParishChoices(); $("parafia_katolicka").value = params.get("parafia_katolicka"); }
  if (params.get("jest_miejscowoscia") === "false" || params.get("typ")) {
    document.querySelector('input[name="locality"][value="nonlocalities"]').checked = true;
  } else if (params.get("jest_miejscowoscia") === "true" || ["gmina", "parafia_katolicka", "gubernia_ujednolicona", "typ_punktu_osadniczego", "królestwo_polskie"].some(id => params.get(id))) {
    document.querySelector('input[name="locality"][value="only"]').checked = true;
  }
  $("kingdom-only").checked = params.get("królestwo_polskie") === "true";
  document.querySelectorAll("[data-presence-filter]").forEach(input =>
    input.checked = params.get(input.id) === "true");
  updateLocalityUi();
  const initialView = viewFromHash();
  switchView(initialView, false);
  if (initialView === "przegladanie") loadBrowse(1);
  if ($("query").value.trim()) search(Number(params.get("page")) || 1);
}
initialize();
