# React Dashboard - Phase 1 (Flagship Overview + 3D Candidate Field) Plan

> **For agentic workers:** implement task-by-task; build must stay green (`npm run build`) and the data must be the corrected data.

**Goal:** Build out the editorial overview home page and the rotatable 3D candidate field (all drugs positioned by binding strength, efficiency, and size), on the corrected data, with reveal + scroll motion.

**Architecture:** Extend `scripts/export_web_data.py` to emit `field.json` (per-target drug points). Add R3F `CandidateField` and editorial overview sections to the React app. Buckets/insight/scales are frontend constants ported from the mockup but fed corrected numbers.

**Stack:** react-three-fiber + drei (3D), framer-motion (reveals), gsap + ScrollTrigger (field fly-in), visx not needed this phase.

---

## Data contract: `web/public/data/field.json`
Keyed by target id; each value is the drug points for that target.
```
{ "DENV_NS5": [ { "name","category","indication","mw","ha","le","vina","dl","admet" }, ... ], ... }
```
- `vina` = best (min) docking score for that drug+target; `le` = ligand_efficiency; `dl` = is_druglike (0/1); `admet` = overall_pass (0/1); `mw`, `ha` from drugs. Only drugs with a docking result for that target are included.

## File structure (Phase 1)
```
scripts/export_web_data.py        (extend: + field.json)
tests/test_export_web_data.py     (extend: + field.json checks)
web/src/data/types.ts             (+ FieldPoint, Field)
web/src/data/api.ts               (+ useField)
web/src/lib/buckets.ts            (category -> bucket {label,color}; insight(point); plain/sci axis copy)
web/src/three/CandidateField.tsx  (R3F scene: instanced spheres, OrbitControls, hover tooltip, target switcher)
web/src/three/HeroMolecule.tsx    (R3F ambient molecule for the hero)
web/src/components/{Steps,TargetCards,HonestyBand,Footer,FieldPanel}.tsx
web/src/pages/Overview.tsx        (rebuild: hero + stats + steps + field + targets + honesty + footer)
web/src/hooks/useScrollFlyIn.ts   (gsap ScrollTrigger; reduced-motion aware)
```

## Tasks
1. **Export `field.json`** + tests. Per target: join `ml_scores` (le, dl) + best `docking_results.vina_score` + `drugs` (mw, ha, category, indication) + `admet.overall_pass`. Test: NS5 top by vina is dasabuvir; velpatasvir/grazoprevir/pibrentasvir are NOT in the NS5 drug-like top set; every point has the 9 keys.
2. **Frontend data layer:** `FieldPoint`/`Field` types, `useField` hook, `buckets.ts` (BUCKETS, CAT2BUCKET, bucketOf, insight, axis copy plain/sci).
3. **`CandidateField.tsx`:** `<Canvas frameloop="demand">` with on-demand invalidate on control change; spheres via `<Instances>`/`<Instance>` from drei (radius ~ heavy atoms, color = bucket, opacity = admet, green torus ring if drug-like); OrbitControls (damping, autorotate until hover); hover via R3F pointer events -> set hovered point -> HTML tooltip (drei `<Html>` or a DOM overlay); a 6-target `<select>`/segmented switcher that springs positions (react-spring) on change. Scales: x = -vina (stronger right), y = le, z = mw, normalized.
4. **`HeroMolecule.tsx`:** small ambient rotating molecule (nodes + bonds), `frameloop="always"` capped, reduced-motion stops rotation.
5. **Overview sections:** Steps (3 how-it-works cards, plain/sci copy), TargetCards (grouped by disease from `targets.json`, with validation note), HonestyBand (AUC 0.37, control, two-metric, caveats), Footer, FieldPanel (read-it-like-this + legend + axis labels reacting to register). Rebuild `Overview.tsx` to compose: hero (HeroMolecule + headline + stats) -> Steps -> CandidateField + FieldPanel -> TargetCards -> HonestyBand -> Footer.
6. **Motion:** `useScrollFlyIn` (gsap ScrollTrigger scrubs the field spheres from a scattered start into position as the section scrolls in; disabled and snapped under reduced-motion). framer-motion `Reveal` wraps text sections.
7. **Verify + ship:** `npm run build` green; commit; merge to `main` (auto-deploys); screenshot the live candidate field to confirm correct data and interactivity.

## Acceptance
- Overview renders hero, stats, three steps, the 3D field, six target cards (grouped by disease, NS5 flagged validated/AUC 0.37, others hypothesis-only), honesty band, footer.
- Candidate field: rotates, hover shows a plain-English read per drug, target switcher changes the cloud; for NS5 dasabuvir is prominent and the oversized HCV DAAs are absent from the drug-like set.
- Plain/scientific toggle changes axis labels and the read copy.
- Reduced-motion: no autorotate/scrub; field shown static in final positions; numbers shown final.
- Build green; live on the Vercel URL.

## Out of scope (later phases)
Per-drug detail pages, the Drug Explorer table (Phase 2), binding viewer (Phase 3). The field hover links toward `/explore` but that page stays a stub until Phase 2.
