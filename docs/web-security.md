# Web: migracja zależności i audyt

Stan zweryfikowany 3 listopada 2026 r. Web korzysta z Next.js 16.4.4,
React/React DOM 19.3.1 i Node.js 24 LTS. Next.js 14 nie otrzymuje już
standardowego wsparcia; linia 16 ma status Active LTS.

Migracja obejmuje stabilne `typedRoutes`, generowanie typów tras przed `tsc`,
automatyczny JSX runtime i flat config ESLint. `next lint` został usunięty
z Next.js 16, dlatego CI uruchamia ESLint CLI oddzielnie od buildu.
Zachowano konfigurację Core Web Vitals, reguły React i dostępności oraz
naprawiono wykryte problemy hooków zamiast wyłączać reguły.

Vitest, plugin React dla Vite i Playwright usunięto z deklaracji zależności,
ponieważ repo nie zawiera ich konfiguracji ani testów web/E2E. `make test`
uruchamia istniejące testy Python. Frontend weryfikują lint, typy i build;
nie oznacza to pokrycia zachowania UI testami automatycznymi.

## Zakres i pozostałe zgłoszenie

`pnpm audit --prod --audit-level=low` nie wykazał znanych podatności
produkcyjnych zależności web. Ten sam check jest wymagany przez CI.
Pełny `pnpm audit` nadal zgłasza **GHSA-g3hv-75wg-m249 / CVE-2026-118764**
(moderate) dla `minimatch` 10.2.6 i 3.1.5 w narzędziach ESLint.

Upstream opisuje przeciążenie CPU/pamięci przez specjalnie przygotowany
wzorzec glob przy `optimizationLevel >= 2` i wskazuje poprawkę 11.0.1.
Baza npm oznacza szerszy zakres `<11.0.1` niż pole affected w komunikacie
autora. `minimatch` jest tutaj zależnością developerską: nie obsługuje
żądań HTTP i nie należy do produkcyjnego grafu zależności aplikacji.
Narzędzia lintujące nadal przetwarzają pliki i konfigurację repozytorium,
więc pełnego audytu nie należy opisywać jako czystego.

Nie zastosowano globalnego override na `minimatch` 11. Pluginy import,
React i jsx-a11y wymagają wywoływalnego eksportu z linii 3, a linia 11
usuwa również `makeRe()` i zmienia reprezentację matcherów.
Takie wymuszenie mogłoby uszkodzić lint lub zmienić zakres sprawdzanych
plików. Zgłoszenie pozostaje widoczne do czasu zgodnej aktualizacji upstream;
nie dodano listy ignorowanych advisory ani wyłączeń reguł.

ESLint 10 jest utrzymywaną linią. Next.js 16.4.4 dokumentuje jego obsługę,
ale część dołączonych pluginów nadal deklaruje peer range kończący się na 9.
Instalacja pnpm może wypisać te ostrzeżenia; lint sprawdzono z ESLint 10.

## Ponowna weryfikacja

```bash
pnpm install --frozen-lockfile
pnpm audit --prod --audit-level=low
pnpm audit
pnpm --filter @astoka/web lint
pnpm --filter @astoka/web type-check
pnpm --filter @astoka/web build
```

Audyt obejmuje znane zgłoszenia z bazy zależności w chwili sprawdzenia.
Nie obejmuje obrazów kontenerów, zależności Python ani testu całego
przepływu przetwarzania wideo i modeli. Dockerfile web nadal uruchamia
serwer developerski zgodnie z przeznaczeniem lokalnego snapshotu.

## Źródła

- [Polityka wsparcia Next.js](https://nextjs.org/support-policy)
- [Migracja do Next.js 15](https://nextjs.org/docs/app/guides/upgrading/version-15)
- [Migracja do Next.js 16](https://nextjs.org/docs/app/guides/upgrading/version-16)
- [Komunikat bezpieczeństwa Next.js z 14 października 2026](https://nextjs.org/blog/nextjs-security-update-october-14-2026)
- [Konfiguracja i zgodność ESLint z Next.js](https://nextjs.org/docs/app/api-reference/config/eslint)
- [Wsparcie wersji ESLint](https://eslint.org/version-support/)
- [Komunikat autora minimatch](https://github.com/isaacs/minimatch/security/advisories/GHSA-g3hv-75wg-m249)
- [Zmiany API minimatch](https://github.com/isaacs/minimatch/blob/main/changelog.md)
