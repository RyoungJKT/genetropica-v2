# React Dashboard - Phase 2 (Drug Explorer) Plan

**Goal:** A full Drug Explorer at `/explore`: a sortable, filterable table of all drugs for a chosen target (dual-metric ranks, ADMET, drug-like), plus a per-drug detail panel (class, indication, structure, scores across all targets, ADMET breakdown, plain-English read).

**Architecture:** Extend `scripts/export_web_data.py` to add dual ranks to `field.json` and a new `admet.json`. New React page composes a target selector, a filter toolbar, a sortable table, and a slide-in detail panel. All client-side over static JSON.

## Data contract additions
- `field.json` points gain `vrank` (vina_rank), `lrank` (le_rank).
- `admet.json`: `{ name: { lipinski, hepatotox, herg, bioavail, pass } }` per drug (raw values from the `admet` table; render as pass/flag or low/high).

## File structure
```
scripts/export_web_data.py        (extend: field ranks + admet.json)
tests/test_export_web_data.py     (extend: ranks + admet checks)
web/src/data/types.ts             (+ vrank/lrank on FieldPoint; AdmetRow, Admet)
web/src/data/api.ts               (+ useAdmet)
web/src/components/DrugTable.tsx  (sortable/filterable table)
web/src/components/DrugDetail.tsx (per-drug slide-in profile)
web/src/pages/Explore.tsx         (compose: target selector + toolbar + table + detail)
```

## Tasks
1. **Export:** add `vrank`/`lrank` to field points; write `admet.json`. Tests: every NS5 point has integer `vrank`/`lrank`; admet.json has 100 entries with a `pass` field.
2. **Data layer:** extend `FieldPoint` (vrank, lrank); add `AdmetRow`/`Admet` types and `useAdmet` hook.
3. **DrugTable:** props {points, onSelect}. Columns: rank (by current sort), name, class (color dot), MW, Vina, ligand efficiency, drug-like, ADMET. Click a column header to sort (asc/desc); default sort = vina asc. Sticky header, editorial styling, row hover, click row -> onSelect(drug).
4. **Toolbar + filters (in Explore):** text search by name; toggles for "drug-like only" and "ADMET pass only"; a drug-class filter (all / one bucket). Target selector (the 6 targets). Filters applied before passing rows to DrugTable; show the filtered count.
5. **DrugDetail:** props {point, admet, field, onClose}. Slide-in right panel: name, class, indication; structure (MW, heavy atoms, InChIKey, source); this-target Vina + ligand efficiency + dual ranks; ADMET breakdown (lipinski/hepatotox/herg/bioavailability/overall); a compact "binding across all 6 targets" mini-bar list (from field across targets); the plain-English insight. Esc / backdrop closes.
6. **Explore page:** header + register-aware intro; target selector; toolbar; `<DrugTable>`; `<DrugDetail>` when a drug is selected.
7. **Verify + ship:** `npm run build` green; verify on the stable deploy; commit; push.

## Acceptance
- `/explore` lists all drugs for the chosen target in a sortable table; switching target re-lists; filters (search, drug-like, ADMET, class) narrow the set with a live count.
- Sorting by Vina puts the oversized antivirals on top but they are clearly marked not drug-like; sorting by efficiency surfaces small efficient drugs; dual ranks shown.
- Clicking a drug opens a detail panel with its full profile incl. ADMET breakdown and cross-target binding.
- Visibility is not gated on any scroll/JS animation (lesson from Phase 1: no opacity-0 Reveal around data).
- Build green; live on Vercel.

## Notes
- Reuse `bucketOf`/`insight` from `lib/buckets`. Keep the editorial design tokens. No 3D here (this is a data tool).
- Do NOT wrap the table/detail in the `whileInView` Reveal (it can strand content invisible in throttled tabs).
