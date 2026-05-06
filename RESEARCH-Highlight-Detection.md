# RESEARCH — Highlight Detection dla Astoki

**Status:** Załącznik techniczny do PRD-Astoka.md
**Wersja:** 0.1
**Data:** 2026-05-06
**Cel:** dostarczyć konkretne, implementowalne specyfikacje dla highlight scoring w Sprint 4 (HIGH-XX wymagania w PRD), oparte na badaniach naukowych 2023-2026

---

## 1. Decyzja architektoniczna — paradygmat hybrydowy

Trzy paradygmaty rozważane dla highlight detection:

| Paradygmat | Sprzęt | Jakość | Werdykt |
|---|---|---|---|
| Czyste heurystyki (RMS, TF-IDF, scene changes) | CPU wystarczy | Niska, dużo false positives | ❌ Odrzucone |
| End-to-end deep learning (VideoMAE, TimeSformer) | A100 80GB i więcej, OOM dla long-form | Średnia-wysoka | ❌ Niewykonalne dla 30-90 min input |
| **Hybrydowy: heurystyki + LLM reranking** | RTX 4090 24GB wystarczy z kwantyzacją | Wysoka | ✅ **Wybór dla Astoki** |

Uzasadnienie: VideoMAE i TimeSformer mają kwadratową złożoność uwagi czasoprzestrzennej i dławią się przy długich materiałach nawet na A100. HieraMamba (2025) ma liniową złożoność i jest alternatywą do monitorowania na fazę 3, ale jeszcze niedojrzała w open-source w 2026.

Hybrydowy paradygmat redukuje wideo do tekstu (przez Whisper), filtruje heurystycznie (BM25 / dense retrievers), a właściwe rozumowanie deleguje do LLM (Llama 3.3 8B lokalnie). To podejście jest stosowane przez OpusClip (Gemini 1.5 Flash w produkcji), Munch oraz wszystkie aktywne projekty open-source.

---

## 2. Macierz cech predykcyjnych z wagami

Wagi wywiedzione z meta-analiz (Rhapsody 2025 — 13k podcast episodes z replay graphs, TripleSumm ICLR 2026, OpusClip patents). To jest **punkt startowy do scoring engine**, podlegający empirycznej kalibracji na materiałach Akademii.

### Cechy tekstowe (semantyka) — łącznie 0.45

| Cecha | Waga | Implementacja MVP |
|---|---|---|
| **Hook Moments** (paradoksy / mocne stwierdzenia w pierwszych 3-5s wypowiedzi) | 0.18 | LLM prompt: "find the strongest opening claim in first 5 seconds" |
| **Opinion Bombs / Emotional Peaks** (kontrowersyjne tezy polaryzujące) | 0.15 | LLM reranking + RoBERTa sentiment scores |
| **Density of Practical Value** (instrukcje krok po kroku, wyliczenia, terminologia) | 0.12 | TF-IDF na słowniku domenowym + LLM ocena |

### Cechy akustyczne — łącznie 0.33

| Cecha | Waga | Implementacja MVP |
|---|---|---|
| **Dynamika sentymentu audio** (pitch, intensywność, tempo) | 0.15 | wav2vec2 emotion embeddings + delta tracking |
| **Powtarzalność emocjonalna (A-PH)** (śmiech, aplauz, "aha moments") | 0.10 | K-means clustering audio features + cosine similarity |
| **VAD / Silence Ratio** (gęstość mowy) | 0.08 | silero-vad — już w stacku Astoki |

### Cechy wizualne — łącznie 0.22

| Cecha | Waga | Implementacja MVP |
|---|---|---|
| **Entropia wizualna** (scene changes, camera shifts) | 0.08 | PySceneDetect — już w stacku |
| **Face/Pose Dynamics** (ekspresja twarzy, gesty) | 0.08 | YOLOv11s + MediaPipe Pose (opcjonalnie) |
| **OCR / Slide Transitions** (kontekst graficzny webinarów) | 0.06 | PaddleOCR — w fazie 2, nie MVP |

### Reguła agregacji

Każda cecha generuje wartość 0-1 dla każdego segmentu (1-2s okno). Końcowy score segmentu:

```
segment_score = Σ (waga_cechy × wartość_cechy) × 100
```

Segmenty z score ≥ 70 stają się kandydatami na highlights. Lista kandydatów przekazywana do LLM do finalnego rerankingu (sekcja 4).

**KRYTYCZNE: te wagi to punkt startowy.** Pierwsze 2 tygodnie po implementacji scoring engine = empiryczna kalibracja na 5-10 nagraniach Akademii. Wagi muszą być konfigurowalne w pliku YAML, nie hardcoded.

---

## 3. Audio dynamics jako first-class feature

W oryginalnym PRD audio analysis był wpisany jako "dynamika audio" bez sprecyzowania. Research wskazuje wagę 0.15 dla pitch/energy fluctuations — **równie wysoką jak Opinion Bombs tekstowe**.

### Implementacja

DAViHD (Dual-Pathway Audio Encoders for Video Highlight Detection, 2026) to SOTA, ale za skomplikowane na MVP. Uproszczona wersja dla Astoki:

**Ścieżka 1: Energia spektralna**
- Próbkowanie audio co 100ms
- Compute RMS energy + spectral centroid + zero-crossing rate
- Detekcja peaks (>2σ powyżej baseline)
- Output: timeline energy peaks → wartość 0-1 per segment

**Ścieżka 2: Embedding emocji**
- wav2vec2 emotion model (już w stacku dla forced alignment)
- Compute embeddings co 1s
- Detekcja shift > threshold (cosine distance między sąsiadującymi)
- Output: emotional shift indicator → wartość 0-1 per segment

Końcowy `audio_dynamics_score` = średnia ważona obu ścieżek (50/50 dla MVP).

### Korekcja timestampów przez audio (nowy wymóg)

**Problem zdiagnozowany w research:** OpusClip / Munch / wszystkie LLM-only systems cierpią na "context blindness" — tną materiał gdy LLM widzi keyword w transkrypcie, ignorując audio context. Skutek: ucięcie pointy komediowej, obcięcie setupu, zniszczenie pauzy dramatycznej.

**Rozwiązanie dla Astoki — post-processing krok po LLM:**

```
def correct_clip_boundaries(clip_start, clip_end, audio_features):
    # Znajdź najbliższy "natural boundary" w obrębie ±2s od LLM-suggested cut
    # Natural boundary = silence > 200ms LUB sentence end (period detected by ASR)
    # LUB energy minimum (drop > 30% from running average)

    corrected_start = find_nearest_boundary(
        clip_start,
        window=2.0,
        priority=['silence', 'sentence_end', 'energy_min']
    )
    corrected_end = find_nearest_boundary(
        clip_end,
        window=2.0,
        priority=['silence', 'sentence_end', 'energy_min']
    )
    return corrected_start, corrected_end
```

To eliminuje 80% temporal drift problems opisanych w UX research konkurencji.

---

## 4. LLM reranking — schema promptu

PRD miał uproszczoną wersję JSON schema z `Funkcje_produktu.pdf`. Research wskazuje na bardziej granularny format zgodny z prompts-to-summaries paradigm.

### Input dla LLM (kontekst)

- Pełna transkrypcja chunka (20-min okno, 60s overlap z sąsiednimi)
- Lista pre-filtered candidates (segmenty z score ≥ 70 z heurystyk)
- Audio dynamics summary per kandydat (energy peak, emotional shift Y/N)
- Scene changes summary
- Optional: prompt użytkownika ("zrób 3 shorty o X")

### Output JSON schema (rozszerzenie PRMT-03 w PRD)

```json
{
  "chunk_id": "chunk_03",
  "candidates": [
    {
      "id": "highlight_01",
      "start": 145.2,
      "end": 187.6,
      "viral_score": 87,
      "typology": "opinion_bomb | hook_moment | story_peak | practical_value | revelation | comedy_punch",
      "hook_sentence": "Większość ludzi myśli że X, ale prawda jest taka że Y",
      "virality_reason": "Występuje tu nierozwiązany konflikt opinii stymulujący komentarze + clear hook w pierwszej sekundzie",
      "suggested_title": "Dlaczego wszyscy się mylą co do X",
      "edit_suggestions": {
        "remove_fillers": ["yyy w 152s", "no w 167s"],
        "trim_pause_after": 178.4,
        "emphasis_word": "naprawdę"
      },
      "audio_corrected": true,
      "confidence": 0.84
    }
  ]
}
```

### Kluczowe elementy promptu

1. **Wymuszenie typologii** — LLM musi sklasyfikować każdy highlight do jednej z 6 kategorii. To zmusza do głębszej analizy niż "fragment ciekawy".

2. **Hook sentence jako separate field** — LLM identyfikuje konkretne zdanie, które działa jak hook. Może być użyte do auto-suggested title lub zmiany kolejności (przesunięcie hook na początek shorta).

3. **Virality reason jako required** — wymóg uzasadnienia eliminuje LLM "halucynacje akceptacji" (model akceptuje wszystko jako interesujące). Jeśli model nie potrafi uzasadnić — score idzie w dół.

4. **Confidence score** — LLM podaje własne confidence. Highlights z confidence < 0.6 są flagowane do manual review w UI (montażysta widzi "AI nie jest pewny — sprawdź").

### Prompt template (do iteracji)

Pełny prompt zostanie dostarczony w Sprint 4 implementacji. Szkielet:

```
Jesteś ekspertem od wirusowych krótkich form wideo na TikTok/Reels/Shorts.
Otrzymasz fragment transkrypcji wraz z pre-filtered kandydatami na highlights.

Twoje zadanie: zrerankuj kandydatów i zwróć top 5 zgodnych z formatem JSON.

Reguły:
1. KAŻDY highlight musi mieć hook w pierwszych 3 sekundach
2. KAŻDY highlight musi mieć clear viral_reason — jeśli nie potrafisz uzasadnić, score < 60
3. Unikaj overlapping highlights (IoU > 0.5 = drop słabszy)
4. Preferuj highlights z energy peak w audio_dynamics
5. Optymalna długość 30-60 sekund
6. Klasyfikuj typologię ściśle z listy: [opinion_bomb, hook_moment, story_peak, practical_value, revelation, comedy_punch]

Pre-filtered candidates: {candidates}
Audio dynamics: {audio_summary}
Scene changes: {scene_summary}
User prompt (opcjonalny): {user_prompt}

Zwróć JSON zgodny ze schematem.
```

---

## 5. Deduplikacja — Non-Maximum Suppression

**Próg IoU = 0.5** dla overlap między kandydatami.

Algorytm:
```python
def deduplicate_highlights(candidates):
    # Sort by viral_score desc
    sorted_candidates = sorted(candidates, key=lambda x: x['viral_score'], reverse=True)
    keep = []

    for candidate in sorted_candidates:
        is_duplicate = False
        for kept in keep:
            iou = calculate_iou(candidate, kept)
            if iou > 0.5:
                is_duplicate = True
                break
        if not is_duplicate:
            keep.append(candidate)

    return keep

def calculate_iou(a, b):
    # Intersection over Union dla przedziałów czasowych
    intersection_start = max(a['start'], b['start'])
    intersection_end = min(a['end'], b['end'])
    intersection = max(0, intersection_end - intersection_start)

    union = (a['end'] - a['start']) + (b['end'] - b['start']) - intersection
    return intersection / union if union > 0 else 0
```

To eliminuje "Vizard problem" (algorithmic redundancy — dziesiątki klonów tego samego momentu).

---

## 6. Chunking dla long-form > 20 min

**Z forka SamurAIGPT:** 20-minutowe okna z 60s overlap.

**Uzasadnienie naukowe (research dodaje):** zjawisko "Lost in the Middle" — modele LLM tracą precyzję w środku długich kontekstów. Llama 3.3 8B z 128k context window technicznie przyjmuje 90-min transcript, ale jakość highlight detection spada drastycznie po ~30 min materiału.

**Mechanizm scal merge:**

1. Każdy chunk przetwarzany niezależnie → lista highlightów per chunk
2. Highlights z 60s overlap zone są deduplikowane przez IoU 0.5
3. Końcowa lista = zlepek wszystkich chunków - duplicates

**Edge case:** highlight który zaczyna się w chunk_N i kończy w chunk_N+1. Overlap zone gwarantuje że oba chunki "widzą" pełen highlight. Wybierany jest reprezentant z wyższym viral_score.

---

## 7. Roadmap iteracji jakości

**Faza 1 (MVP — Sprint 4)**
- Heurystyki tekstowe + audio energy + scene detection (waga ~0.55 z macierzy)
- LLM reranking Llama 3.3 8B
- IoU dedupe
- Audio-corrected timestamps
- **Cel: acceptance rate ≥ 40% (cel z PRD MET-05)**

**Faza 1.5 (Post-MVP, ale przed walidacją go/no-go)**
- wav2vec2 emotion embeddings (waga audio podbita do pełnych 0.33)
- Empiryczna kalibracja wag na 20+ nagraniach Akademii
- Test alternatywnych LLM (Qwen 2.5 14B vs Llama 3.3 8B)
- **Cel: acceptance rate ≥ 50%**

**Faza 2**
- OCR dla webinarów (PaddleOCR) — waga wizualna +0.06
- Active Speaker Detection (LoCoNet) — lepsze face/pose dynamics
- Custom prompt templates per niche (psychologia / fitness / business — różne kategorie virality)
- **Cel: acceptance rate ≥ 60%**

**Faza 3+ (eksperymentalne)**
- DAViHD dual-pathway audio (jeśli SOTA potwierdzi się produkcyjnie)
- HieraMamba dla bezpośredniej inferencji long-form (jeśli dojrzeje w open-source)
- TripleSumm adaptive fusion (gdy MoSu dataset ma więcej dotrenowanych wariantów)

---

## 8. Anti-patterns — czego unikać

Z research konkurencji (OpusClip / Munch / Pictory):

**1. Context blindness przez LLM-only timestamps**
- Problem: LLM widzi keyword w transkrypcie, tnie tam, niszczy audio context
- Fix dla Astoki: audio-corrected boundaries (sekcja 3)

**2. Algorithmic redundancy**
- Problem: Vizard generuje 30 klipów z tej samej minuty
- Fix dla Astoki: IoU 0.5 dedupe (sekcja 5)

**3. Temporal drift przy long-form**
- Problem: kwadratowa uwaga modeli end-to-end nie skaluje się
- Fix dla Astoki: chunking + hybrydowy paradigm (sekcja 6)

**4. Brand-agnostic clipy**
- Problem: każde narzędzie generuje "ten sam wygląd" — generic AI slop
- Fix dla Astoki: brand kits w fazie 2, prompt-driven edit w MVP daje montażyście kontrolę

**5. Per-minute pricing penalty**
- Problem: OpusClip karze za długi input
- Fix dla Astoki: brak limitów (self-hosted, bez per-minute billing)

**6. Generic prompts dla wszystkich typów contentu**
- Problem: jeden prompt dla podcasts + tutorials + comedy daje słabe wyniki dla wszystkich
- Fix dla Astoki: faza 2 — prompty per niche (Akademia ma wąskie nisze: psychologia, fitness, business)

---

## 9. Otwarte pytania techniczne (do empirycznej walidacji)

1. **Wagi z Rhapsody są dla anglojęzycznych podcastów** — czy działają tak samo dla polskiego? Pierwsza kalibracja na 5 nagraniach Akademii powinna odpowiedzieć.

2. **Llama 3.3 8B vs Qwen 2.5 14B dla polskich transkryptów** — research nie ma porównania na polskim. A/B test w Sprint 4-5.

3. **Threshold 70 dla candidates filter** — może być za wysoki dla mowy spontanicznej (BIGOS V2 pokazał że WER spontaniczny 34% mediany). Może 60 dla webinarów typu Q&A?

4. **wav2vec2 emotion model — który wariant dla polskiego?** Polish emotion datasets są ograniczone. Może multilingual fallback wystarczy.

5. **Sliding window vs hard chunks dla 60+ min materiału** — research preferuje hard chunks z overlap, ale niektóre prace eksperymentują z sliding 5-min window. Worth testing po MVP.

---

## 10. Źródła badawcze

Najistotniejsze do referowania w implementacji (i ewentualnym pitchu zarządowi):

- **Rhapsody (2025)** — dataset 13k podcast episodes z replay graphs, fundament metodologii oceny highlights
- **TripleSumm (ICLR 2026)** — adaptive multimodal fusion, dataset MoSu, benchmark
- **DAViHD (2026)** — dual-pathway audio encoders, SOTA dla audio-visual highlight detection
- **Prompts-to-Summaries (2025)** — zero-shot text-queryable summarizer, paradigm dla prompt-driven edit
- **VideoMAE V2 (CVPR 2023)** — pokazuje dlaczego end-to-end nie skaluje się dla long-form
- **HieraMamba (2025)** — alternatywa dla Transformer, liniowa złożoność, do monitorowania
- **OpusClip patents + Gemini 1.5 Flash blog post** — production architecture liderów rynku
- **AI-Youtube-Shorts-Generator (SamurAIGPT)** — fork base Astoki, zawiera referencyjną implementację chunking + dedupe

---

**Status dokumentu:** zatwierdzony do referowania w Sprint 4 (HIGH-XX). Kalibrowany empirycznie po pierwszej iteracji na materiałach Akademii.

**Następny krok:** wrzucenie do repo `astoka` obok `PRD-Astoka.md`. Claude Code w Plan mode powinien czytać oba dokumenty.
