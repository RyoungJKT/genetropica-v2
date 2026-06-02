# GeneTropica - React + three.js Dashboard Rebuild (Design Spec)

**Owner:** Russell Young, British School Jakarta.
**Date:** 2026-06-02. Canonical repo: `/Users/darwin/Developer/genetropica-v2`.
**Status:** design approved in principle; this spec is for review before the implementation plan.

## 1. Goal
Replace the 9-page Streamlit dashboard with a single, fast, editorial React application that presents the full GeneTropica dataset (the corrected, post-remediation data), with selective three.js for the genuinely-3D set-pieces. The result should be impressive and motion-interactive while staying accessible, performant, and honest (the project's credibility theme extends to the UI).

## 2. Locked decisions
- **Data delivery:** static JSON, exported from the cleaned database at build time. No runtime backend.
- **Hosting:** Vercel (same platform as the existing landing page).
- **Scope:** full rebuild of all nine tools, shipped in phases; the Streamlit app is retired at cutover (Phase 7).
- **Motion:** hybrid. Framer Motion for UI/reveals/counters; GSAP + ScrollTrigger for the showpiece scroll sequences; react-three-fiber's own loop + react-spring for 3D. All motion respects `prefers-reduced-motion`.
- **Stack:** React + Vite + TypeScript; React Router (SPA, Vercel rewrite to `index.html`); TanStack Query for data fetching/caching; react-three-fiber + drei for 3D; visx (D3 scales + React SVG) for 2D charts.

## 3. Non-negotiable correctness rules (carried from the data remediation)
- The app reads ONLY the corrected data. Dasabuvir leads NS5; the oversized HCV DAAs (velpatasvir, grazoprevir, pibrentasvir) are out of the top ranks. The mockup's hardcoded drug list is discarded.
- No fabricated values. Where a value is undefined (for example dasabuvir's MD ligand RMSD, "no stable pose"), the UI shows that state, it does not invent a number.
- Honesty surfaces are first-class UI, not footnotes: the NS5 AUC 0.37 result, the "ML score is a target-agnostic prior" caveat, validation status per target, "predicted from docked pose" labels, evidence tiers on literature, and the unbiased-association framing of MD.
- No AI-tool references anywhere in the repo or UI. No em dashes in prose; no section-sign symbol.

## 4. Architecture and data flow
```
cleaned SQLite DB  +  existing data/*.json
        |
        v
scripts/export_web_data.py   (reproducible build step; part of data-integrity discipline)
        |
        v
web/public/data/*.json       (static, versioned, committed)
        |
        v
React app on Vercel          (fetch on load via TanStack Query)
```
The export script is the single bridge from data to UI. It is re-run whenever the database changes, and its output is committed so the deployed app is always reproducible from the repo.

## 5. Data export contract (first cut)
Small/global files are fetched once on app load; large/per-entity files are fetched on demand.

- `summary.json` - counts and the headline stats, all computed from data at runtime of the export (drugs, targets, diseases, docking runs completed).
- `targets.json` - the 6 targets: id, name, disease, PDB id, UniProt, structure source, biological role, `validation_status`, grid center/box/exhaustiveness/modes.
- `drugs.json` - the 100 drugs: name, category, indication, MW, heavy atoms, InChIKey, structure source.
- `rankings/{target_id}.json` - per target: each drug's best Vina score, ligand efficiency, `vina_rank`, `le_rank`, `is_druglike`, ADMET `overall_pass`.
- `interactions/{target_id}__{drug}.json` - FIX-9 chemistry-aware contacts for a docked pose (residue, number, chain, type, distance), with the predicted-from-pose flag.
- `admet.json` - per drug ADMET descriptors and pass/flag.
- `conservation.json` - ConSurf grades by residue + summary (from existing `data/conservation/...`).
- `validation.json` - ROC/enrichment results, AUC 0.37, model metadata (RandomForest, ChEMBL training).
- `md/*.json` - already exist under `data/md_simulation/comparison/` (rmsd, rmsf, hbonds, binding_proxy, contacts, summary); the export copies/normalises them.
- `literature.json` - per link: drug, target, PMID, evidence tier, verified, title-match flag, confidence.

## 6. Information architecture (routes)
- `/` - editorial overview (hero, animated stats, how-it-works, the 3D candidate field, target cards, honesty band).
- `/explore` - Drug Explorer (filter/sort all 100 drugs per target; dual-metric ranks; per-drug profile).
- `/binding` - 3D Binding Viewer (docked pose in pocket + contact residues).
- `/md` - MD Simulation (association story; protein/ligand RMSD, RMSF, Rg, H-bonds, min-distance).
- `/admet` - ADMET Profiling (Lipinski, tox flags, drug-likeness).
- `/conservation` - Conservation (ConSurf grades, heatmap).
- `/insights` - AI Insights (the ML prior: what it is and is not, AUC 0.37 honesty).
- `/methods` - Methods and reproducibility (docking grid, engine, ML, data sources).
- `/validation` - Methodology Validation (ROC, enrichment).
- `/diseases` - Disease Overview (the three diseases and six targets).

## 7. Design system
Ported from the approved mockup and the landing page into CSS variables and a small component kit.
- **Tokens:** paper `#F4F0E6` / `#ECE6D8` / `#E4DCC9`; ink `#1C1A17` / soft `#544F45` / faint `#8A8273`; green `#1F5740` / bright `#2E7D5B`; clay `#A8492B`; gold `#A8742C`; line `#D8D0BD`; teal `#2C6E6B`; slate `#5B5470`.
- **Type:** Fraunces (serif display), Hanken Grotesk (sans body), Spline Sans Mono (labels/eyebrows). Paper-grain texture overlay.
- **Components:** Header/nav, Section scaffold, StatStrip, Card, TargetCard, Tooltip, Toggle (plain/scientific language), eyebrow/mono type, HonestyBand, reveal wrapper.
- **Voice and copy:** the dashboard adopts the landing page's voice exactly: plain-English-first, warm, editorial, honest, readable by a non-expert, with scientific precision available on demand. The current Streamlit copy (terse and technical) is rewritten to match. A global plain/scientific toggle switches registers app-wide: plain-English labels and one-line explanations by default, exact terms and units (kcal/mol, Angstrom, AUC, ligand efficiency) when toggled. Example: an axis reads "grips the protein harder ->" (plain) vs "AutoDock Vina (kcal/mol) ->" (scientific); an MD panel reads "did the drug stay stuck?" vs "ligand RMSD vs bound pose (A)". Every chart, metric, and section carries a plain-English read, not just a technical label.

## 8. 3D islands (R3F)
Each is an isolated `<Canvas>`, rendered on demand (paused when off-screen), reduced-motion aware.
- **Hero molecule** - ambient rotating abstract molecule (ported from mockup).
- **Candidate field** - the centerpiece: 100 drugs as a single `InstancedMesh` for performance, positioned by Vina (x), ligand efficiency (y), MW (z); ADMET encodes opacity; a ring marks drug-like; OrbitControls; hover tooltip; a 6-target switcher that springs spheres to new positions. Wired to corrected `rankings/{target}.json`.
- **Binding viewer** - receptor pocket + docked-pose ball-and-stick (accurate elements/bonds), contact residues from the interactions file, camera glide-in.
- **Atom / molecule builder** - the existing accurate VSEPR/CPK ball-and-stick builder, ported.

## 9. Animation approach
- **GSAP + ScrollTrigger:** the pinned/scrubbed scroll sequences on `/` (hero assemble, candidate-field fly-in and orbit, then hand-off to interactive). Used surgically, not everywhere.
- **Framer Motion:** section reveals, number counters, list/table stagger, layout transitions on filter/sort, page transitions.
- **R3F `useFrame` + react-spring:** in-scene 3D motion (idle rotation, camera tweens to a selected drug, target-switch morphs).
- **Chart and diagram entrance motion (a standard, applies to every chart):** each chart animates in when it scrolls into view, then settles. Bars grow up from zero; lines (RMSD, RMSF, ROC) draw on left-to-right (animated SVG path length); scatter and heatmap points fade and scale in with a short stagger; radial/donut charts sweep; numbers count up. Implemented by animating visx's scales and paths via Framer Motion / react-spring, triggered on view with an IntersectionObserver, played once per entry (debounced so it does not replay on every scroll). On-hover and on-filter changes also tween (bars and points ease to new values rather than snapping).
- **Accessibility:** a global reduced-motion guard disables scrubbed/auto/entrance motion and snaps every chart and scene straight to its final state.

## 10. Repo structure and deployment
- New `web/` Vite app at the repo root. Separate Vercel project rooted at `web/`.
- Static data committed under `web/public/data/`.
- The existing `landing/` page stays live and untouched until the Phase 1 React overview is ready to supersede it; the landing-vs-overview merge/redirect is a deferred decision (see Open questions).

## 11. Phasing (each phase ships something live)
- **Phase 0 - foundation:** scaffold `web/`; port design system + base components; build `scripts/export_web_data.py` and the typed data layer; deploy an empty shell to Vercel. Acceptance: shell live; `summary.json`/`targets.json`/`drugs.json` generated and loading.
- **Phase 1 - flagship overview:** the editorial home + the 3D candidate field on corrected data, with the GSAP scroll sequence. Acceptance: `/` live, candidate field interactive and correct, reduced-motion verified.
- **Phase 2 - Drug Explorer:** filter/sort all 100 drugs per target; dual-metric ranks; per-drug profile; ADMET flags. Acceptance: parity with Streamlit page 02 on corrected data.
- **Phase 3 - 3D Binding Viewer:** docked pose + contact residues with predicted-from-pose labeling. Acceptance: parity with page 03; viewer performant.
- **Phase 4 - MD Simulation:** the honest association story and all MD charts. Acceptance: parity with page 09; "no stable pose" handled; association framing present.
- **Phase 5 - ADMET + Conservation:** pages 08 and 07. Acceptance: heatmaps + tables match data.
- **Phase 6 - AI Insights + Methods + Validation + Disease Overview:** pages 04, 05, 06, 01, with the ML-prior and AUC 0.37 honesty, grid coords, ROC. Acceptance: parity; honesty surfaces present.
- **Phase 7 - cutover:** make the React app primary; redirect/retire Streamlit; full a11y + responsive + visual-polish pass. Acceptance: one polished app; Streamlit decommissioned.

## 12. Out of scope
- The reportlab PDF export stays a Python script (the professor artifact, generated on demand); it is not reimplemented in React.
- No new science; this is a presentation rebuild of existing, corrected data.

## 13. Risks and mitigations
- **3D performance** with 100 instanced spheres + scroll-synced scene: use `InstancedMesh`, on-demand frameloop, and pause off-screen.
- **Scroll-sync complexity** (GSAP + R3F): isolate each set-piece; provide a reduced-motion static fallback from day one.
- **Data drift** between the export and the DB: the export script is reproducible and committed; re-run it as part of any data change.
- **Scope creep** across nine tools: the phase acceptance criteria are parity-with-Streamlit, not redesign-every-chart.

## 14. Open questions (deferred, not blocking Phase 0)
- Landing page: fold the existing `landing/` into the React app as `/`, or keep it separate and redirect later.
- Custom domain / subdomain for the dashboard vs the current Railway URL.
- (Resolved) The plain/scientific language toggle applies app-wide and the dashboard voice matches the landing page; the entrance-motion standard applies to every chart. See sections 7 and 9.
