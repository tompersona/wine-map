# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

```
python3 -m http.server 8000
```

Then open http://localhost:8000. The CSV must be served over HTTP — opening `index.html` directly as a `file://` URL will fail to load `cellar.csv`.

## Architecture

This is a single-file app: all HTML, CSS, and JavaScript live in `index.html`. There is no build step, bundler, or package manager.

**Data source:** `cellar.csv` — columns are `Producer, Wine, Vintage, Quantity, Format_cl`. Parsed at runtime by PapaParse.

**Mapping:** Leaflet 1.9.4 with CARTO Voyager tiles (no API key required). Markers are `L.divIcon` elements styled via `.wine-marker`.

**Producer geocodes:** Hardcoded in the `PRODUCERS` object near the top of the `<script>` block (~line 365). Each entry has `lat`, `lng`, `region`, and `country`. Adding a new producer to `cellar.csv` requires a matching entry here or it will be silently skipped (logged to console as a warning).

**Popup styling:** Leaflet's default popup chrome (`.leaflet-popup-content-wrapper`, `.leaflet-popup-close-button`, etc.) is overridden in the `<style>` block using `!important` where needed to beat Leaflet's specificity. The popup content itself is built by `buildPopup()` and uses `.popup-inner` and related classes.

**Sidebar:** Populated dynamically after CSV load — producer count, wine count, bottle count, and a country breakdown sorted by bottle count.

**Special case:** "Rhys" and "Rhys Vineyards" are merged into a single map pin in `render()`.
