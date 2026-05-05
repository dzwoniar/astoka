# Astoka — Product Requirements Document

| Field    | Value       |
|----------|-------------|
| Project  | Astoka (robocza nazwa — wewnętrzne narzędzie Akademii 100k do automatycznej produkcji shortów) |
| Version  | 0.1 (Draft) |
| Date     | 2026-05-05  |
| Author   | Janek + zespół Akademia 100k |
| Status   | Draft — gotowy do implementacji MVP |

---

## 1. Overview / Problem Statement

Akademia 100k oraz jej klienci (twórcy 10k–50k followersów na IG/TikTok) produkują regularnie shorty z long-form video (webinary, podcasty, talking head). Obecnie zespół wykorzystuje płatne narzędzia SaaS (OpusClip, Submagic, Klap, Vizard) na maksymalnych planach abonamentowych — koszty rosną nieliniowo wraz z wolumenem materiału (per-minute pricing penalizuje długie webinary), a nakładające się subskrypcje wielu narzędzi tworzą dodatkowy koszt operacyjny i fragmentację przepływu pracy.

Astoka to wewnętrzna, samoobsługowa (self-hosted) aplikacja webowa zastępująca ten stos. Działa lokalnie na sprzęcie GPU firmy, eliminuje opłaty per-minute i per-clip, zapewnia pełną prywatność materiałów klientów oraz daje zespołowi pełną kontrolę nad pipeline'm produkcyjnym. MVP celuje w 1–2 montażystów wewnętrznych Akademii; faza 2 rozszerza dostęp na klientów programu.

---

## 2. Goals and Non-Goals

**Goals (v1 — MVP):**

- Zastąpienie obecnych narzędzi SaaS dla podstawowego workflow: long-form (20–90 min) → shorty (15–60 s) w formacie 9:16 z napisami
- Pełen pipeline działający lokalnie na pojedynczej stacji z RTX 4090 (24 GB VRAM)
- Throughput minimum 60 minut input video / 1 godzina pracy GPU dla pełnego pipeline'u (transkrypcja + reframe + render)
- Wsparcie języka polskiego z WER ≤10% na typowych nagraniach klientów Akademii (cel: zbliżenie do Whisper-large-v3 turbo benchmarku FLEURS PL ~7.6%)
- Word-level synchronizacja captions z dokładnością ≤120 ms (próg akceptowalny dla 30 fps; cel ≤50 ms)
- Generowanie 3–10 propozycji shortów z każdego long-form input
- Eksport gotowych klipów w formatach: 9:16 (Reels/Shorts/TikTok) + 16:9 (LinkedIn/YouTube standard) w 1080p (faza 1) i 4K (faza 2)
- Prompt-driven edit z walidowanym JSON schema (nie freeform FFmpeg)
- Brak limitów per-minute, per-clip, znaków wodnych

**Non-Goals (v1 — celowo odkładane):**

- Multi-tenancy z izolacją danych per klient (faza 2)
- Auto-scheduler dystrybucji do TikTok/Instagram/YouTube (faza 3)
- AI Avatar Studio / generatywny lip-sync
- Tłumaczenia wielojęzyczne / dubbing (Canary 1B v2 możliwy w fazie 3)
- Mobilna aplikacja iOS/Android
- Auto-generacja B-roll z bibliotek stockowych
- Brand kits z customowymi szablonami per klient (faza 2)
- Real-time analytics dashboard z platform społecznościowych
- Integracja z platformami social do publikacji "one-click"
- AI-generowane awatary (HeyGen-style)
- Diaryzacja mówców jako feature MVP (pyannote 3.1 dostępny w stacku, ale UI tylko w fazie 2)
- Automatyczna detekcja screen-share / B-roll z różnych typów ujęć

---

## 3. Target Users

**Primary user — Montażysta Akademii 100k / Montażysta u klienta Akademii**

Decyzja produktowa: traktujemy te dwie role jako jedną personę. Niczym się nie różnią pod kątem zadań, technical comfort i workflow.

Profil:
- Wiek 22–35, zazwyczaj freelancer lub member małego zespołu marketingowego
- Średni-zaawansowany poziom techniczny — używa CapCut/Premiere/Resolve, rozumie pojęcia takie jak timeline, keyframe, render
- Pracuje z polskim językiem natywnie, ale rozumie angielskie UI
- Skala: jeden montażysta przerabia 5–20 godzin material long-form tygodniowo, generuje 30–100 shortów
- Pain points dzisiaj: per-minute pricing OpusClipa, słabe polskie captions w narzędziach amerykańskich, redundancja klonujących klipów, brak elastyczności w timeline
- Oczekiwania: szybki pipeline (tolerancja czekania: 5–15 min na 30-min input), przewidywalna jakość, możliwość ręcznej korekty zanim wyeksportuje
- Środowisko pracy: laptop/desktop z dobrym monitorem, dostęp do firmowej infrastruktury przez przeglądarkę

**Secondary user — Administrator techniczny (1 osoba na całą firmę, wstępnie Janek)**

Profil:
- Odpowiada za uruchomienie i utrzymanie serwera GPU
- Konfiguruje konta użytkowników, zarządza limitami storage, monitoruje queue
- Reaguje na błędy pipeline, restartuje workery, aktualizuje modele
- Skala: 1–3 użytkowników w fazie 1, 10–50 w fazie 2

Skala MVP: 1–3 jednoczesnych użytkowników, 1 serwer GPU lokalnie.

---

## 4. Jobs to Be Done

| ID    | Job (When… I want to… so I can…) | Priorytet |
|-------|-----------------------------------|-----------|
| JTBD-01 | Kiedy dostaję 60-minutowy webinar od klienta na Drive, chcę wgrać go do narzędzia jednym kliknięciem (upload MP4 lub link YouTube), żeby od razu uruchomić proces analizy bez manualnej konwersji formatów | P0 |
| JTBD-02 | Kiedy materiał jest przeanalizowany, chcę zobaczyć transkrypcję polską z timestamps na poziomie pojedynczych słów, żeby móc edytować wideo przez tekst (jak w Descript) zamiast szukać momentów na osi czasu | P0 |
| JTBD-03 | Kiedy chcę wyciąć shorty z webinaru, chcę dostać 5–10 automatycznych propozycji z uzasadnieniem ("dlaczego ten fragment?") i score wiralności, żebym mógł szybko zaakceptować lub odrzucić zamiast samemu szukać momentów | P0 |
| JTBD-04 | Kiedy mam wybrane fragmenty, chcę żeby narzędzie automatycznie przekadrowało je do 9:16 z trackingiem mówcy w centrum kadru, żebym nie musiał ręcznie ustawiać każdego cięcia w CapCut | P0 |
| JTBD-05 | Kiedy generuję shorty po polsku, chcę żeby napisy były perfekcyjnie zsynchronizowane z dźwiękiem (karaoke-style, słowo po słowie) i miały spójny styl, żebym mógł je publikować bez ręcznej korekty | P0 |
| JTBD-06 | Kiedy mam konkretną wizję shortów ("zrób 3 klipy o automatyzacji AI, hook w 1. sekundzie, usuń długie pauzy"), chcę napisać to promptem i dostać shorty zgodne z opisem, żeby narzędzie reagowało na intencję, a nie tylko na przyciski | P1 |
| JTBD-07 | Kiedy któryś z auto-wygenerowanych shortów jest prawie OK ale wymaga drobnej korekty (przesunąć cięcie o sekundę, zmienić styl captions), chcę to poprawić w timeline UI bez eksportu do innego programu, żeby nie tracić czasu na re-import | P1 |
| JTBD-08 | Kiedy zaakceptuję shorty, chcę je wyeksportować do MP4 w 1080p z prawidłowymi proporcjami (9:16 dla Reels, 16:9 dla LinkedIn), żeby od razu wrzucić na social bez postprodukcji | P0 |
| JTBD-09 | Kiedy wracam do projektu następnego dnia, chcę zobaczyć wszystkie poprzednie analizy, transkrypcje i wygenerowane shorty zachowane, żebym nie musiał re-procesować materiału | P0 |
| JTBD-10 | Kiedy odrzucam wygenerowany short jako "zły fragment", chcę móc go schować/oznaczyć jako odrzucony, żeby nie zaśmiecał mi listy aktywnych klipów (anti-pattern: workspace clutter z OpusClipa) | P1 |

---

## 5. Functional Requirements

### Ingest (INGEST-XX)

- **INGEST-01**: System przyjmuje upload pliku MP4/MOV/MKV o rozmiarze do 5 GB przez drag-and-drop lub przycisk wyboru pliku
- **INGEST-02**: System przyjmuje URL z YouTube i pobiera materiał lokalnie używając yt-dlp (wbudowana biblioteka, nie zewnętrzne API)
- **INGEST-03**: System wyświetla ostrzeżenie ToS przed pobraniem z YouTube: "Pobieraj wyłącznie własne materiały lub takie, do których masz prawa autorskie"
- **INGEST-04**: System generuje proxy preview (480p, 30 fps, H.264) dla szybkiego podglądu w UI; oryginał trzymany na disk
- **INGEST-05**: System ekstrahuje metadata: długość, rozdzielczość źródłowa, klatkaż, ścieżki audio, język (best-guess)
- **INGEST-06**: System pokazuje progress bar dla operacji uploadu i ekstraktu
- **INGEST-07**: System rejestruje zadanie w queue i informuje użytkownika o szacowanym czasie oczekiwania (na podstawie długości input × współczynnik throughputu)

### Project management (PROJ-XX)

- **PROJ-01**: Użytkownik może utworzyć nowy projekt z polem "nazwa" i opcjonalnym "klient" (string, do 100 znaków)
- **PROJ-02**: Każdy projekt ma listę source materials (uploadowanych long-form) i listę generated clips (krótkie shorty)
- **PROJ-03**: Lista projektów wyświetla: nazwa, klient, data utworzenia, liczba klipów, ostatnia modyfikacja
- **PROJ-04**: Sortowanie projektów: po dacie modyfikacji (default), po nazwie, po kliencie
- **PROJ-05**: Filtr projektów: wszystkie / tylko aktywne / tylko zarchiwizowane
- **PROJ-06**: Soft-delete projektu (przeniesienie do "Archive", nie fizyczne usunięcie przez 30 dni)
- **PROJ-07**: Hard-delete projektu z arkivum z confirmation modal
- **PROJ-08**: Przechowywanie projektów: dane w Postgres, pliki w MinIO (lokalnie)

### ASR & Transcription (ASR-XX)

- **ASR-01**: System uruchamia automatyczną transkrypcję w faster-whisper (model: distil-whisper-large-v3-pl lub Whisper-large-v3-turbo) po zakończeniu uploadu
- **ASR-02**: System generuje transkrypcję z word-level timestamps przez WhisperX + wav2vec2 forced alignment
- **ASR-03**: System zapisuje transkrypcję jako JSON z polami: `segments[].text`, `segments[].start`, `segments[].end`, `segments[].words[].text`, `segments[].words[].start`, `segments[].words[].end`, `segments[].words[].confidence`
- **ASR-04**: System wyświetla transkrypcję w UI z możliwością odsłuchu fragmentu po kliknięciu w słowo/zdanie
- **ASR-05**: Język domyślny: polski. System detekuje język automatycznie ale pozwala wymusić ręcznie (PL/EN)
- **ASR-06**: System obsługuje pliki audio do 90 minut na pojedynczą transkrypcję bez zmian w architekturze
- **ASR-07**: Transkrypcja jest cache'owana — re-upload tego samego pliku (po hash) używa istniejącej transkrypcji
- **ASR-08**: Edycja transkrypcji w UI: użytkownik może poprawić błędne słowo, zmiana zapisuje się w bazie ale nie powoduje re-renderu (chyba że re-export)

### Text-based editing (EDIT-XX)

- **EDIT-01**: Użytkownik może zaznaczyć tekst w transkrypcji i kliknąć "Wytnij ten fragment" — system oznacza odpowiednie sekundy jako wykluczone z renderu
- **EDIT-02**: System automatycznie wykrywa filler words po polsku (`yyy`, `eee`, `no`, `wiesz`, `tego`, `jakby`, `że`, `znaczy się`) i pokazuje opcję "Usuń wszystkie wypełniacze" jednym kliknięciem
- **EDIT-03**: System detekuje pauzy dłuższe niż 800 ms (próg konfigurowalny) używając silero-vad i pokazuje opcję "Skróć pauzy do max 300 ms"
- **EDIT-04**: Wszystkie operacje edycji są niedestruktywne — oryginalna transkrypcja i source video pozostają nietknięte; edits to JSON z markup
- **EDIT-05**: Undo/Redo dla operacji edycyjnych (minimum 10 kroków historii)

### Highlight detection (HIGH-XX)

- **HIGH-01**: System uruchamia automatyczne wykrywanie highlightów po zakończeniu ASR
- **HIGH-02**: Highlight scoring łączy heurystyki + LLM reranking; heurystyki: tempo mowy, zmiany energii audio, długość pauz przed/po, scene changes (PySceneDetect), obecność twarzy (YOLOv11s), podobieństwo do prompt użytkownika
- **HIGH-03**: LLM reranking: Llama 3.3 8B / Qwen 2.5 14B (lokalnie via Ollama) ocenia każdy potencjalny segment w skali 0–100 na bazie hooks, emotional peaks, opinion bombs, story peaks, practical value (framework z forka SamurAIGPT)
- **HIGH-04**: System chunkuje long-form > 20 minut na 20-min bloki z 60s overlap (Long-Video Aware z forka), żeby nie przekraczać context window LLM
- **HIGH-05**: Output: lista 3–10 propozycji shortów, każda z polami: `start`, `end`, `score`, `hook` (jednozdaniowy hook line), `reason` (1–2 zdania uzasadnienia), `suggested_title`
- **HIGH-06**: Domyślna długość proponowanego shorta: 30–60 s (konfigurowalne w preferencjach projektu)
- **HIGH-07**: Mechanizm deduplikacji — jeśli dwa proponowane segmenty mają overlap > 50%, system zachowuje tylko ten z wyższym score (z forka)
- **HIGH-08**: Konfiguracja LLM provider: lokalny (default, via Ollama) lub fallback API (GPT-4o-mini, Gemini Flash) — przełącznik per projekt
- **HIGH-09**: System pokazuje czas analizy i estimated cost (dla API) przed uruchomieniem
- **HIGH-10**: Każdy wygenerowany highlight ma akcję "Akceptuj" / "Odrzuć / Schowaj" / "Edytuj" — odrzucone klipy znikają z głównego widoku ale pozostają w historii (anti-pattern: brak workspace clutter)

### Reframe 9:16 (REFR-XX)

- **REFR-01**: System wykrywa twarze i body w każdej klatce używając YOLOv11s (face detection) z próbkowaniem co 5. klatka (180 detekcji na minutę)
- **REFR-02**: System śledzi spójną tożsamość obiektów w czasie używając ByteTrack (filter Kalmana + dwuetapowe matching low-confidence boxes)
- **REFR-03**: System aplikuje filtr wygładzający trajektorię kadru (motion smoothing) — eliminacja jitteringu, max przesunięcie kadru: 30 px/klatka
- **REFR-04**: Domyślny tryb: TRACK (kadr podąża za aktywnym mówcą). Użytkownik może wymusić tryb GENERAL (centrum + blur background)
- **REFR-05**: Dla nagrań z 2+ osobami w kadrze — domyślnie kadr na osobie najbliższej środka źródła (heurystyka). W fazie 2: integracja z Active Speaker Detection (LoCoNet)
- **REFR-06**: Format wyjściowy: 1080×1920 (9:16) lub 1920×1080 (16:9 — rezerwuje dla LinkedIn)
- **REFR-07**: User może wymusić ręczny pivot kadru w timeline UI — drag & drop ramki w wybranych momentach
- **REFR-08**: Render reframe używa hardware encoding NVIDIA NVENC (1× silnik na RTX 4090) dla H.264

### Captions (CAPS-XX)

- **CAPS-01**: System generuje napisy w formacie ASS (Advanced SubStation Alpha) — pozwala na kontrolę pozycji, koloru, fontu, animacji
- **CAPS-02**: Style domyślny ("Plain"): biały tekst, czarny outline, font Arial Bold, rozmiar 60 pt, pozycja: 75% od góry
- **CAPS-03**: Drugi styl bazowy ("Dynamic Bold"): jasnożółty tekst (#FFD700), aktualnie wymawiane słowo wyróżnione (highlight box), animacja word-by-word ("karaoke")
- **CAPS-04**: Opcjonalnie: Brand kit per projekt (font, kolor primary, kolor highlight) — pole tekstowe z ostrzeżeniem "Brand kits są feature, nie USP, planowane do pełnej kontroli w fazie 2"
- **CAPS-05**: Captions są palone (burned-in) na video w fazie renderingu — gwarantuje spójność na każdej platformie
- **CAPS-06**: Pozycja captions respektuje "safe zones" platform — np. dla TikTok dolne 20% i prawe 15% to strefa UI, captions ustawione poza
- **CAPS-07**: Word-level timestamps z forced alignment muszą mieć dokładność ≤120 ms (cel ≤50 ms — empiryczna walidacja)
- **CAPS-08**: User może edytować tekst captions w UI; zmiana wymusza re-render (sygnalizowany przyciskiem "Re-render z nowymi captions")
- **CAPS-09**: Brak Submagic-style emoji/B-roll auto-injection w MVP — to feature fazy 2

### Prompt-driven edit (PRMT-XX)

- **PRMT-01**: User wpisuje polecenie naturalnym językiem (PL lub EN) w pole "Prompt" — np. "zrób 3 shorty o automatyzacji AI, hook w pierwszej sekundzie, usuń pauzy, captions żółte"
- **PRMT-02**: System przesyła do LLM: pełna transkrypcja + metadata segmentów (scene changes, energy levels, face detections, speaker turns) + prompt + brand preset + JSON schema (z PDF)
- **PRMT-03**: LLM zwraca JSON zgodny z schematem: `{"goal": str, "clips": [{"source_segments": [...], "hook_strategy": str, "aspect_ratio": str, "captions": str, "reframe_target": str, "remove_fillers": bool, "cta": str}]}`
- **PRMT-04**: Backend waliduje JSON przeciw schemie (Pydantic); jeśli niezgodny — retry z error feedback do LLM (max 3 próby)
- **PRMT-05**: Renderer wykonuje plan na podstawie zwalidowanego JSON — nigdy nie wykonuje arbitralnych komend FFmpeg z LLM
- **PRMT-06**: User widzi JSON plan przed renderem ("preview plan") z opcją zatwierdzenia / edycji manualnej / odrzucenia
- **PRMT-07**: Prompt-driven edit jest **feature**, nie podstawowy workflow MVP — domyślny przepływ to klikanie w propozycje highlight, prompt-mode jest opcjonalnym akceleratorem dla zaawansowanych użytkowników

### Render & Export (RNDR-XX)

- **RNDR-01**: System renderuje finalny klip używając FFmpeg (H.264, AAC audio, faststart flag dla mobile)
- **RNDR-02**: Pipeline renderingu: cięcie segmentów → reframe → audio normalization (-14 LUFS, -1 dBFS peak) → captions burn-in → finalna kompresja
- **RNDR-03**: Captions burnowane przez Remotion (warstwa graficzna programatyczna) lub bezpośrednio FFmpeg z formatem ASS — wybór według złożoności efektów (MVP: ASS via FFmpeg)
- **RNDR-04**: Output: 1080p H.264 (faza 1), opcja 4K w fazie 2
- **RNDR-05**: Bitrate output: 8 Mbps dla 1080p, 25 Mbps dla 4K
- **RNDR-06**: Po zakończeniu renderingu: download link, copy-to-clipboard URL (dla integracji z innymi narzędziami w przyszłości), preview embedded player
- **RNDR-07**: Batch export: user może zaznaczyć wiele highlightów i wyrenderować wszystkie jednym kliknięciem (queue, FIFO)
- **RNDR-08**: Render queue ma priority — manual trigger (high), batch (normal), background re-renders (low)

### User accounts & auth (AUTH-XX) — minimal scope dla MVP

- **AUTH-01**: System wspiera 3–5 lokalnych kont użytkowników (basic auth + sesja w cookie)
- **AUTH-02**: Brak self-registration — admin (Janek) tworzy konta ręcznie w fazie 1
- **AUTH-03**: Każdy projekt jest własnością konkretnego usera; inni mogą zobaczyć tylko jeśli zostaną dodani jako collaborators (faza 2 feature, MVP: brak współpracy)
- **AUTH-04**: Hasła hashed bcrypt; sesje JWT z 24h TTL; renew on activity
- **AUTH-05**: Faza 2: Multi-tenancy z izolacją per klient; faza 3: SSO via Google Workspace dla zespołu Akademii

---

## 6. Non-Functional Requirements

### Performance (NFR-PERF)

- **NFR-PERF-01**: Throughput: minimum 60 minut input video / 1 godzina pracy (full pipeline na RTX 4090)
- **NFR-PERF-02**: ASR (faster-whisper) na 60-min nagraniu: ≤5 minut (target benchmark)
- **NFR-PERF-03**: Highlight detection (heurystyki + LLM): ≤3 minuty na 60-min nagranie z lokalnym Llama 3.3 8B
- **NFR-PERF-04**: Reframe + render 60-sek shorta z captions: ≤30 sekund
- **NFR-PERF-05**: Time-to-first-feedback (od uploadu do pierwszej propozycji highlight w UI): ≤8 minut dla 60-min input
- **NFR-PERF-06**: UI responsiveness: ≤200 ms dla zmiany widoku, ≤500 ms dla wczytania transkrypcji 60-min projektu

### Hardware (NFR-HW)

- **NFR-HW-01**: MVP działa na pojedynczej stacji z 1× RTX 4090 (24 GB VRAM), 64 GB RAM, 12-core CPU, 1 TB NVMe SSD
- **NFR-HW-02**: Storage: 1 TB SSD wystarczy na ~50–100 projektów (1 webinar 60 min ≈ 5–10 GB z proxy + transkrypcja + outputs)
- **NFR-HW-03**: Sieć: 1 Gbit/s lokalnie wystarczy; brak wymogu publicznego dostępu w fazie 1
- **NFR-HW-04**: Zasilanie: dedykowany PSU 1000W+ ATX 3.0 (RTX 4090 ma TDP 450W, transient spikes)
- **NFR-HW-05**: Backup strategy: codzienny snapshot Postgres + cotygodniowy backup MinIO na zewnętrzny dysk

### Reliability (NFR-REL)

- **NFR-REL-01**: System restartuje queue automatycznie po crash workera (Celery z retry policy: max 3 retries, exponential backoff)
- **NFR-REL-02**: Częściowe wyniki są zachowywane — jeśli render się crashe na klipie 5/10, klipy 1–4 są dostępne
- **NFR-REL-03**: Idempotentność operacji — re-upload tego samego pliku (hash match) używa cache transkrypcji i reframe
- **NFR-REL-04**: Logging: każde job ma trace ID, logi w JSON format do Postgres + opcjonalnie file system

### Security & Privacy (NFR-SEC)

- **NFR-SEC-01**: Dane (video, transkrypcje, generated clips) nigdy nie opuszczają serwera firmy w MVP
- **NFR-SEC-02**: LLM lokalny (Ollama) — domyślny tryb. API fallback wymaga explicit opt-in per projekt
- **NFR-SEC-03**: Brak telemetrii / analytics zewnętrznych w aplikacji
- **NFR-SEC-04**: GDPR: dane projektowe oznaczone właścicielem, mechanizm soft-delete z 30-dniowym oknem retencji, hard-delete na żądanie
- **NFR-SEC-05**: TLS dla wszystkich połączeń HTTP (self-signed cert w fazie 1, Let's Encrypt w fazie 2 jeśli ekspozycja zewnętrzna)

### Language & Localization (NFR-LANG)

- **NFR-LANG-01**: Język interfejsu: polski (default), angielski (opcja w settings)
- **NFR-LANG-02**: ASR primary: polski; fallback: angielski (auto-detect z opcją wymuszenia)
- **NFR-LANG-03**: WER PL na materiałach Akademii: target ≤10% (do empirycznej walidacji w fazie testów ASR)
- **NFR-LANG-04**: Captions wspierają polskie znaki diakrytyczne (ą, ę, ć, ł, ń, ó, ś, ź, ż) — UTF-8 throughout

### Browser & Device (NFR-BROW)

- **NFR-BROW-01**: Wsparcie: Chrome 120+, Firefox 115+, Safari 16+, Edge 120+
- **NFR-BROW-02**: Mobilne UI: nie priorytet w MVP (warning pokazany użytkownikom mobilnym)
- **NFR-BROW-03**: Minimalna rozdzielczość ekranu: 1280×720 (komfortowo: 1920×1080+)

---

## 7. User Flows

### Flow 1: Happy path — generowanie shortów z webinaru (najczęstszy use case)

1. Montażysta loguje się do Astoka w przeglądarce (URL lokalnej instancji firmy)
2. Klika "Nowy projekt" → wpisuje nazwę "Webinar Klient X — Maj 2026" → klika "Utwórz"
3. W projekcie klika "Dodaj materiał" → wybiera plik MP4 z dysku (60 min webinar) → upload startuje (progress bar)
4. Po zakończonym uploadzie (~3 min dla 5 GB lokalnie) system pokazuje proxy preview i status "Analizuję..."
5. Pipeline się uruchamia: ASR (4 min) → scene detection + face tracking (2 min) → highlight detection (3 min) — całość ~9 minut
6. UI aktualizuje się incremental — najpierw pojawia się transkrypcja, potem highlights w listy
7. Montażysta widzi 7 propozycji shortów posortowanych po score; każda z hookiem i uzasadnieniem
8. Klika w pierwszą propozycję → otwiera się timeline UI z preview klipu i edytorem captions
9. Akceptuje styl "Dynamic Bold" dla captions, klika "Render"
10. Render trwa ~25 sekund, pojawia się download link MP4 1080p 9:16
11. Klika Download, otrzymuje plik gotowy do publikacji na Reels
12. Wraca do projektu, akceptuje 3 kolejne shorty, robi batch render (~2 min na 3 klipy)
13. Odrzuca pozostałe 3 propozycje — znikają z głównego widoku, lądują w "Zarchiwizowane"

### Flow 2: Error path — yt-dlp fail / niewspierany URL

1. Montażysta wkleja link YouTube i klika "Pobierz"
2. System próbuje pobrać przez yt-dlp
3. yt-dlp zwraca błąd (np. "Video unavailable" lub "Private video")
4. UI pokazuje czytelny komunikat: "Nie udało się pobrać z YouTube. Możliwe przyczyny: prywatne wideo, region-locked, lub limit bot-detection. Spróbuj wgrać plik lokalnie."
5. Przycisk "Spróbuj ponownie" + "Wgraj plik zamiast tego"
6. Logging: error trace zapisany dla admin review
7. User wybiera lokalny upload — flow kontynuuje normalnie

### Flow 3: Power-user path — prompt-driven edit

1. Montażysta otwiera istniejący projekt z już przeanalizowanym webinarem
2. Klika "Prompt mode" w timeline UI
3. Wpisuje: "Zrób 5 shortów o ChatGPT, każdy maks 45 sekund, hook w pierwszej sekundzie, captions żółte, usuń pauzy"
4. System pokazuje "Generuję plan…" (3 sek dla lokalnego LLM)
5. Pojawia się JSON plan w czytelnym formacie (collapsed sections, edytowalne pola)
6. Montażysta widzi że jeden z proponowanych klipów jest poza tematem (LLM się pomylił) → odznacza go w UI
7. Klika "Renderuj 4 klipy" → batch render
8. Po 5 minutach 4 gotowe klipy MP4

### Flow 4: Edge case — zbyt długi materiał na MVP hardware

1. User próbuje wgrać 4-godzinne nagranie konferencji
2. INGEST-01 sprawdza długość — przekracza limit 90 min ASR
3. UI pokazuje warning: "Materiał >90 minut. Pipeline może nie zmieścić się w VRAM. Polecam pociąć materiał lub uruchomić w trybie 'chunk' (eksperymentalny)."
4. User wybiera "Chunk mode" → system dzieli na 3 części po ~80 min, procesuje sekwencyjnie
5. Highlights generowane per chunk; dedup wykrywa overlap między chunkami i mergeuje

---

## 8. Design and Technical Constraints

### Tech stack (zamrożony — z synthesis fazy researchu)

**Frontend:**
- Next.js 14 (App Router) — zgodne z PDF rekomendacją
- React 18 + TypeScript
- Tailwind CSS — utility-first, doskonale udokumentowany dla AI-assisted dev
- shadcn/ui — komponenty (extremely popular, AI generuje świetny code z nimi)
- Timeline UI: custom component (rozważyć react-konva lub fabric.js dla canvas-based timeline)

**Backend API:**
- FastAPI (Python 3.11+) — spójność językowa z fork base SamurAIGPT i modelami ML
- Pydantic dla schema validation (kluczowe dla prompt-to-JSON pipeline)
- SQLAlchemy 2.0 jako ORM dla Postgres

**Workers & Queue:**
- Celery 5 z Redis jako broker
- Dedykowane worker pools per typ jobu (ASR, render, LLM)
- Flower dla monitoringu queue (admin only)

**ML Stack (zamrożony):**
- Fork base: SamurAIGPT/AI-Youtube-Shorts-Generator (MIT) — łatwa adaptacja, mod 1 pliku do lokalnego LLM
- ASR engine: faster-whisper (CTranslate2, NIE whisper.cpp)
- ASR model: distil-whisper-large-v3-pl (Aspik101) lub Whisper-large-v3-turbo
- Word alignment: WhisperX + wav2vec2 forced alignment
- VAD: silero-vad
- Diarization (faza 2): pyannote.audio 3.1
- Scene detection: PySceneDetect
- Face/object detection: YOLOv11s (Ultralytics)
- Tracking: ByteTrack
- LLM (highlight reranking): Llama 3.3 8B Q4_K_M lub Qwen 2.5 14B przez Ollama
- LLM fallback (opcja): gpt-4o-mini lub gemini-flash via OpenAI-compatible API
- OCR (faza 2 dla screen share): PaddleOCR

**Render:**
- FFmpeg 7+ jako główny silnik (H.264 via NVENC, audio normalization, captions burn-in z formatu ASS)
- Remotion (faza 2) dla bardziej złożonych animacji captions / overlayów

**Storage & DB:**
- Postgres 16 dla metadata, transkrypcji, project state
- pgvector extension dla embeddings (opcjonalnie w MVP, faza 2 dla semantic search po transkrypcjach)
- MinIO (S3-compatible, lokalnie) dla plików video i renderów
- Local filesystem fallback dla MVP jeśli MinIO za ciężki

**Hardware (zamrożony):**
- MVP: pojedyncza stacja z 1× RTX 4090 (24 GB VRAM), 64 GB RAM, 12-core CPU (Ryzen 7 lub i7), 1 TB NVMe SSD
- Faza 2: dual RTX 4090 lub upgrade na L40S (48 GB VRAM, ECC) jeśli wolumen wymusi
- ⚠ Decision needed before scaling: licencja NVIDIA EULA dla GeForce w komercyjnym data center — wymagana weryfikacja prawna przed kolokacją

**Deployment:**
- Docker Compose dla lokalnego dev i pojedynczego serwera
- Traefik jako reverse proxy z TLS
- Brak Kubernetes w MVP (overkill dla 1 serwera)

### Anti-patterns do unikania (z research UX)

- **Per-minute pricing** → Astoka eliminuje z definicji (build własny, brak limitów)
- **Context blindness** w cięciach → adresujemy chunkingiem 20-min/60s overlap (z forka)
- **Algorithmic redundancy** → adresujemy mechanizmem deduplikacji segmentów (overlap > 50% = drop)
- **Bait-and-switch paywall** → nie dotyczy (wewnętrzne)
- **Resolution paywalling** → eliminujemy (natywne 1080p, 4K w fazie 2)
- **Loss of timeline control** → projektujemy multi-layer timeline z manual override
- **Workspace clutter** → projektujemy "Akceptuj/Odrzuć/Schowaj" z każdym wygenerowanym klipem
- **Text-video desync** → WhisperX forced alignment (≤120 ms)
- **Deploy chaos** → wewnętrzny pipeline, własne wersjonowanie, sandbox testy przed produkcją

### Design system (rekomendacja)

- **shadcn/ui + Tailwind** — najpopularniejsze w 2026, AI-friendly (Claude generuje świetny code), modulárne, customizowalne
- **Lucide icons** dla ikonografii
- **Polski font**: Inter (default), Geist Sans (alternatywa) — oba mają wsparcie polskich diakrytyków
- Kolory primary: TBD per brand Akademii (ustalić z R. Sienkiewiczem / J. Miklaszewskim)
- Tryb dark/light: oba supported (default: dark, montażyści preferują)

### Open dependencies / TBD

> ⚠ **Decision needed before implementation:**
> - **Branding visual** (kolory primary/secondary, logo) — do ustalenia z Sienkiewiczem/Miklaszewskim. Wpływa na UI ale nie blokuje development backend.
> - **Hardware procurement** (kupno serwera vs istniejąca stacja) — blocker dla testów MVP w realnym środowisku. Decyzja zarządu.
> - **Licencja NVIDIA EULA dla docelowego deploymentu** — krytyczne przed migracją z biura na kolokację. Wymaga konsultacji prawnej.

---

## 9. Edge Cases and Error Handling

| Scenariusz | Oczekiwane zachowanie |
|------------|----------------------|
| User uploaduje plik > 5 GB | UI pokazuje komunikat "Plik przekracza limit 5 GB. Skompresuj lub pociąć materiał." Upload nie startuje. |
| User uploaduje plik z corrupted audio | ASR detekuje brak audio stream → status job "Failed: no audio detected" + sugestia "Sprawdź czy plik zawiera ścieżkę dźwiękową" |
| YouTube URL jest private / region-locked | yt-dlp zwraca error → UI pokazuje czytelny komunikat + sugestia "Wgraj plik lokalnie zamiast tego" (Flow 2) |
| YouTube URL ma DRM (np. fragmenty filmów licencjonowanych) | yt-dlp odmawia pobrania → UI: "Materiał chroniony DRM. Niemożliwe do pobrania. Wgraj plik lokalnie jeśli masz prawa." |
| Materiał jest 4 godziny długi | Warning "może nie zmieścić się w pipeline", opcja "Chunk mode" (Flow 4) lub odmowa z prośbą o ręczne pocięcie |
| ASR generuje pusty wynik (cisza / brak rozpoznawalnego języka) | UI: "Nie udało się rozpoznać mowy. Sprawdź czy materiał ma dźwięk i język jest polski/angielski." |
| Materiał jest w nieistniejącym języku (np. fiński) | ASR auto-detect zwraca "fi" → warning "Wykryty język: fiński. Czy kontynuować z modelem multilingual? Jakość może być niższa." |
| LLM lokalny (Ollama) nie odpowiada (crash) | Worker retry z backoff (max 3); jeśli wszystkie failed — fallback do API (jeśli skonfigurowany) lub error "LLM service down, kontakt admin" |
| LLM zwraca invalid JSON dla highlight detection | Pydantic walidacja fail → retry z error feedback (max 3); jeśli persistent — fallback do pure heurystyki (energia + scene change + face) |
| FFmpeg crash podczas renderingu | Worker łapie SIGTERM → status "Failed at render step X/Y" + log; user widzi częściowo zakończone klipy (te przed crashem) |
| GPU OOM podczas concurrent jobs | Queue wymusza max 1 job per GPU type w MVP; jeśli OOM mimo to — restart workera, retry z mniejszym batch size |
| User uploaduje ten sam plik 2× | Hash check → użycie cache transkrypcji + reframe; UI: "Materiał już przeanalizowany — używam istniejących wyników" |
| Projekt ma 200+ wygenerowanych shortów | Pagination w UI (50 per page) + filter "tylko aktywne" / "tylko zaakceptowane" |
| User zamyka przeglądarkę podczas długiego renderingu | Job w Celery kontynuuje w tle; po wejściu na ten sam projekt user widzi status "Renderuję..." i progress |
| Disk full podczas renderingu | Pre-check przed rozpoczęciem rendera (estimated output size × 1.5); jeśli za mało — error "Brak miejsca na dysku, zwolnij min X GB" |
| Postgres connection lost | Retry z backoff w API layer; user widzi maksymalnie loading spinner przez 10s, potem "Connection lost — reconnecting" |
| Worker thread zombie po crashu | Healthcheck co 60s; martwe workery są re-spawned przez Celery beat |
| User próbuje edytować projekt którego nie jest właścicielem (faza 1: brak collab) | 403 Forbidden z message "Nie masz uprawnień do tego projektu" |
| Concurrent edit transkrypcji przez 2 userów (faza 2) | Optimistic locking — drugi user dostaje "Konflikt: ta transkrypcja została zmieniona przez kogoś innego, odśwież" |
| Polski filler word jest realnym słowem w kontekście (np. "no" jako zaprzeczenie) | EDIT-02 ma whitelist contextu — "no" przed pytajnikiem nie jest fillerem; user może override globalnie |
| Captions są dłuższe niż 1 linia | Auto-wrap z max 35 znakami per linia (TikTok safe), max 2 linie jednocześnie |
| Materiał ma wielu mówców (panel 3 osoby) | MVP: kadr na osobie najbliższej środka (heurystyka). UI ostrzega "Wielu mówców wykrytych — Active Speaker Detection w fazie 2" |

---

## 10. Success Metrics

### Adopcja (mierzone po 30 dniach od uruchomienia MVP)

- **MET-01**: Liczba projektów utworzonych w Astoka przez zespół: target ≥20
- **MET-02**: Liczba shortów wyeksportowanych: target ≥50
- **MET-03**: % użycia Astoka vs OpusClip/Submagic na nowych zleceniach: target ≥60%
- **MET-04**: Liczba aktywnych użytkowników (≥1 projekt utworzony / tydzień): target ≥2 (z 3 w MVP)

### Jakość

- **MET-05**: Acceptance rate auto-wygenerowanych highlightów: ≥40% (z 10 propozycji ≥4 akceptowane)
- **MET-06**: WER ASR na 5 testowych nagraniach Akademii: ≤10% (cel ≤8%)
- **MET-07**: Caption sync error: ≤120 ms (cel ≤50 ms)
- **MET-08**: Reframe quality (subjective NPS od montażysty 1-10): ≥7 średnio
- **MET-09**: Pipeline failure rate (jobs nie kończące się sukcesem): ≤5%

### Performance

- **MET-10**: Throughput rzeczywisty (input video minutes / godzina pracy): ≥60 min/h
- **MET-11**: Time-to-first-feedback (upload → pierwszy highlight w UI): ≤8 min dla 60-min input
- **MET-12**: Render time per 60-sek short z captions: ≤30 sek

### Biznesowe

- **MET-13**: Miesięczna oszczędność na subskrypcjach SaaS po pełnym przejściu: target ≥80% obecnych kosztów (do empirycznej walidacji — admin musi zebrać baseline)
- **MET-14**: ROI breakeven point: cel 6–12 miesięcy od deployu (build + hardware vs zaoszczędzone abonamenty)

### Acceptance criteria do go/no-go decyzji po MVP

**Go-conditions (wszystkie muszą być spełnione):**
- ≥40% acceptance rate na auto-highlights
- ≥60 min/h throughput
- ≤120 ms caption sync error
- WER PL ≤10%
- Min. 2 montażystów aktywnie używa narzędzia po 30 dniach
- Brak critical bugs blokujących core workflow

**No-go conditions (jakikolwiek z nich = pivot lub abandon):**
- Acceptance rate <20% — auto-highlight nieużyteczny, trzeba przeprojektować
- Throughput <30 min/h — hardware nie wystarczy, eskalacja do GPU upgrade lub re-architektura
- Montażyści wracają do OpusClipa po tygodniu — UX problem fundamentalny

---

## 11. Open Questions

1. **Wolumen rzeczywisty** — Ile minut wideo dziennie / tygodniowo Akademia + klienci faktycznie przerabiają? Bez tej liczby nie wiemy czy 1× RTX 4090 wystarczy. **Akcja**: Janek pyta zarząd / R. Sienkiewicza w pierwszym tygodniu implementacji.

2. **Realny WER PL na nagraniach Akademii** — benchmarki laboratoryjne (FLEURS PL 7.31%) ≠ realne webinary z Zoom z słabym mikrofonem klienta. **Akcja**: test ASR na 3-5 typowych nagraniach przed sprintami od EDIT-XX. Może wymusić zmianę modelu lub dodatkowe denoising preprocessing.

3. **Jakość lokalnego LLM dla highlight detection** — Llama 3.3 8B vs Qwen 2.5 14B — który da lepsze wyniki dla polskich transkryptów w kontekście niszy biznes/coaching/fitness? **Akcja**: A/B test na 5 webinarach po pierwszym tygodniu integracji LLM, decyzja z empirycznych danych.

4. **Active Speaker Detection w MVP czy fazie 2?** — Akademia często nagrywa wywiady 2-osobowe. Bez ASD reframe będzie skakał między osobami. Heurystyka "najbliższy środka" jest słaba. **Akcja**: zacząć od heurystyki, zbierać feedback po 2 tygodniach. Jeśli ASD krytyczne — przyspieszyć do MVP+.

5. **Workflow montażysty — odroczone do prototypu** — nie znamy dokładnego dziennego workflow. **Akcja**: po 2 tygodniach implementacji pokazać prototyp 2 montażystom i zrobić 30-min user testing. Tańsze niż wywiady na sucho.

6. **Branding & visual design** — czeka na wkład Sienkiewicza/Miklaszewskiego. Nie blokuje backend, blokuje finalne UI polish. **Akcja**: design tokeny ustalić w sprincie 3.

7. **Hardware procurement** — używamy istniejącej stacji czy kupno dedykowanego serwera? Decyzja zarządu. **Akcja**: pre-implementation, blocker dla rzeczywistych testów performance.

8. **NVIDIA EULA dla scale** — krytyczne przed migracją z biura na kolokację (faza 2). **Akcja**: konsultacja prawna w trakcie fazy 1, nie później.

9. **Caption styles count** — czy 2 style (Plain + Dynamic Bold) wystarczą dla MVP, czy wprowadzamy 3-5 stylów od razu? **Akcja**: feedback od montażystów na prototypie, decyzja w sprincie 4.

10. **Format JSON dla prompt-driven edit** — schema z PDF jest punkt startowy, ale może wymagać rozszerzenia (np. transitions, B-roll references w fazie 2). **Akcja**: stable interface od początku, additive changes only.

11. **Backup & disaster recovery** — co jeśli serwer GPU padnie fizycznie? Dane projektowe można zsynchronizować, ale jak szybko można odpalić pipeline na zapasowej maszynie? **Akcja**: dokumentacja DR w fazie 1 + test recovery w fazie 2.

12. **Roadmap dystrybucji do klientów (faza 2)** — jak będą uzyskiwać dostęp? Białe konta, link sharing per projekt, dedykowany subdomain? Wpływa na auth architecture. **Akcja**: design fazy 2 po zakończeniu MVP.

---

## Appendix A — Roadmap (orientacyjny)

**Faza 0 — Pre-implementation (1 tydzień)**
- Hardware setup (RTX 4090 stacja gotowa)
- Fork SamurAIGPT/AI-Youtube-Shorts-Generator
- Setup Postgres, MinIO, Redis, Ollama lokalnie
- Test ASR na 5 realnych nagraniach Akademii (otrzymaj liczby WER!)

**Faza 1 — MVP Core (6–10 tygodni przy 40h/tydz)**
- Sprint 1-2: Ingest + ASR + Project management (INGEST, PROJ, ASR-XX)
- Sprint 3: Text-based editing + filler removal (EDIT-XX)
- Sprint 4: Highlight detection (HIGH-XX)
- Sprint 5: Reframe 9:16 (REFR-XX)
- Sprint 6: Captions (CAPS-XX)
- Sprint 7: Render + Export + Batch (RNDR-XX)
- Sprint 8-9: Auth + Polish + Bug fixing (AUTH-XX)
- Sprint 10: User testing wewnętrzne, bug bash

**Faza 2 — Po walidacji MVP (3-6 miesięcy)**
- Multi-tenancy + klienci Akademii
- Brand kits + zaawansowane captions (Submagic-style)
- Active Speaker Detection (LoCoNet)
- Diarization w UI
- 4K render
- Prompt mode jako pierwszej klasy feature

**Faza 3 — Skalowanie (6-12 miesięcy)**
- Migracja na dedykowany serwer GPU (jeśli wolumen wymusi)
- Auto-scheduler social
- Mobile companion app
- Wielojęzyczne (Canary 1B v2)
- B-roll generation

---

## Appendix B — Stack summary card (one-pager dla developera)

```
Frontend:    Next.js 14 + TypeScript + Tailwind + shadcn/ui
Backend:     FastAPI (Python 3.11) + Pydantic + SQLAlchemy
Workers:     Celery 5 + Redis
DB:          Postgres 16 (+ pgvector dla faza 2)
Storage:     MinIO (S3-compatible) lokalnie
ASR:         faster-whisper + WhisperX (model: distil-whisper-large-v3-pl)
VAD:         silero-vad
Detection:   YOLOv11s + ByteTrack
Scenes:      PySceneDetect
LLM:         Llama 3.3 8B / Qwen 2.5 14B przez Ollama (lokalnie)
LLM API:     gpt-4o-mini fallback (opcjonalny opt-in)
Render:      FFmpeg 7 (NVENC) + format ASS dla captions
Hardware:    1× RTX 4090 (24 GB VRAM), 64 GB RAM, 12-core CPU
Fork base:   SamurAIGPT/AI-Youtube-Shorts-Generator (MIT)
Deployment:  Docker Compose + Traefik (lokalny serwer)
```

---

**Status: Draft v0.1 — gotowy do review i implementacji MVP.**

**Następne kroki:**
1. Review tego PRD przez Janka — spojrzenie świeżym okiem na każdą sekcję
2. Korekta nazwy projektu (Astoka → finalna)
3. Wypełnienie open questions tam gdzie to teraz możliwe (wolumen, branding)
4. Ustalenie sprintów (rekomendowany podział powyżej)
5. Setup repo, CI, dev env
6. Faza 0 — test ASR na realnych nagraniach (krytyczny gate przed dalszym dev)
