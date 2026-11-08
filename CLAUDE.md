# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

```
python3 -m http.server 8000
```

Then open http://localhost:8000. The CSV must be served over HTTP — opening `index.html` directly as a `file://` URL will fail to load `cellar.csv`.

## Architecture

This is a single-file app: all HTML, CSS, and JavaScript live in `index.html`. There is no build step, bundler, or package manager.

**Data source:** `cellar.csv` — columns are `Producer, Wine, Vintage, Quantity, Format_cl, Type, Grapes` (Vintage is `NV` for non-vintage; grapes are separated by ` / `). Parsed at runtime by PapaParse.

**Mapping:** Leaflet 1.9.4 with CARTO Voyager tiles. CARTO requires an API key: the production key (restricted to `tompersona.github.io`) is inline in `index.html`; for local dev, create a gitignored `config.local.js` containing `window.CARTO_LOCAL_KEY = '...';` with a key restricted to `localhost`/`127.0.0.1`. Markers are `L.divIcon` elements styled via `.wine-marker`.

**Producers:** `producers.json`, keyed by producer name exactly as in `cellar.csv`. Each entry has `lat`, `lng`, optional `village` and `subregion`, `region` (the wine region a drinker would name, e.g. Burgundy, Ribera del Duero, Hawke's Bay) and `country`. Optional `about` (producer paragraph) and `wines` (wine name → paragraph) feed the detail panel. Notes can tag quiz-worthy facts as `{{answer|kind}}` (kinds: `person`, `place`, `year`, `number`, `grape`, `term`, `org`, listed in `FACT_KINDS`); `stripFacts()` shows just the answer in the panel and warns in the console about unknown kinds. Adding a new producer to `cellar.csv` requires a matching entry here or it will be skipped (logged to console as a warning). `check_geocodes.py` compares coordinates against OpenStreetMap; its suggestions are often wrong name matches, so treat them as hints.

**Popup styling:** Leaflet's default popup chrome (`.leaflet-popup-content-wrapper`, `.leaflet-popup-close-button`, etc.) is overridden in the `<style>` block using `!important` where needed to beat Leaflet's specificity. The popup content itself is built by `buildPopup()` and uses `.popup-inner` and related classes.

**Sidebar:** Populated dynamically after CSV load — producer count, wine count, bottle count, and a country breakdown sorted by bottle count.

**Special case:** "Rhys" and "Rhys Vineyards" are merged into a single map pin in `render()`.
