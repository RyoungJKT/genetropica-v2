# MD Trajectory Animator, Design Spec

**Date:** 2026-06-10
**Status:** Approved design, ready for implementation planning
**Page:** Molecular Dynamics (Tool 03), `web/src/pages/MD.tsx`

## Goal

Add a data-driven 3D animation to the top of the MD page that lets a viewer watch each
candidate drug associate (or fail to associate) with dengue NS5 over the 50 ns simulation.
Every moving element is driven frame-by-frame from the real `md.json` series. The protein
shape and the drug's exact 3D path are stylized and clearly labeled as illustrative, because
the full atomic trajectory was not stored.

## Why this is honest and feasible

The MD runs are 50 ns unbiased association simulations of three drugs (celecoxib,
methotrexate, dasabuvir) with NS5 (PDB 5CCV). Each drug starts about 30 Angstrom away in
solvent and either finds the protein and grips, or does not:

- Celecoxib associates at about 3 ns and stays.
- Methotrexate associates at about 14 ns and remains mobile.
- Dasabuvir never forms a stable bound pose within 50 ns.

We have, per drug, real per-frame series and real per-residue fluctuation, but no stored
per-frame atomic coordinates. So the animation faithfully reproduces the *quantities* that
were recorded (approach distance, timing, flexibility, contacts, H-bonds) on a *stylized*
geometry, rather than replaying atom positions we do not have. react-three-fiber, three,
drei and react-spring/three are already dependencies, so no new packages are needed.

## Data source

No new data. Uses the existing `web/public/data/md.json`, loaded via the existing
`useMd()` hook. Relevant shape, per drug in `series` (keys `celecoxib`, `methotrexate`,
`dasabuvir`):

| series      | shape (per point)                  | length | meaning |
|-------------|------------------------------------|--------|---------|
| `mindist`   | `[t_ns, distance_A]`               | 201    | ligand-protein minimum distance over time |
| `rmsd`      | `[t_ns, protein_rmsd, ligand_rmsd]`| 201    | protein and ligand RMSD (ligand col may be null for dasabuvir) |
| `hbonds`    | `[t_ns, n]`                        | 201    | drug-protein H-bond count over time |
| `ncontacts` | `[t_ns, n]`                        | 201    | close contacts (< 4.5 A) over time |
| `rmsf`      | `[residue_index, rmsf_A]`          | 849    | per-residue flexibility |
| `contacts`  | `[resid, occupancy_pct]`           | 15     | top contact residues |

The 201-frame series span 0 to 50 ns (the time is carried in column 0 of each point).
`summary` (list of 3) carries the per-drug averages already shown in the page table;
`Lig_RMSD_avg` is the string `"no stable pose"` for dasabuvir.

## Architecture and files

New files:

- `web/src/lib/mdMotion.ts`, pure mapping functions with no React or three imports:
  - `distanceAt(series, tNs): number`, interpolates `mindist` between stored frames.
  - `proteinRmsdAt(series, tNs): number` and `ligandRmsdAt(series, tNs): number | null`.
  - `hbondsAt(series, tNs): number`, rounded count.
  - `ncontactsAt(series, tNs): number`.
  - `rmsfFor(series, residueIndex): number`.
  - `frameReadout(series, tNs)`, returns `{ tNs, distance, hbonds, ncontacts }` for the live readout.
  - `DURATION_NS = 50`.
- `web/src/lib/mdLayout.ts`, deterministic stylized geometry (seeded, no real coordinates):
  - `residueNodes(count): { pos: [x,y,z], coreness: number }[]`, a stable globular cloud.
  - `pocketAnchor(): [x,y,z]` and `approachVector(): [x,y,z]`, fixed direction the ligand travels in.
  - Maps `contacts` residue numbers to nodes nearest the pocket so named contacts light up there.
- `web/src/components/md/MdAnimator.tsx`, the container. Owns clock state
  (`tNs`, `playing`, `speed`), the drug selector, play/pause, the scrub slider, the live
  readout, and the honesty caption. Renders `MdScene` and passes `tNs` down. Lifts `tNs`
  up to the page so the charts can show a synced playhead.
- `web/src/components/md/MdScene.tsx`, the R3F `<Canvas>`. Renders the residue-node cloud
  (one `instancedMesh`), the ligand cluster, contact highlights and H-bond lines, all
  reading the current `tNs` in `useFrame`.
- `web/src/lib/mdMotion.test.ts`, unit tests for the mapping functions.

Modified files:

- `web/src/pages/MD.tsx`, mount `<MdAnimator>` directly under the association callout,
  above the summary table. Hold `tNs` in page state and pass an `playheadX` to the three
  time-based charts (RMSD, min-distance, contacts) so a synced line tracks the animation.
- `web/src/components/MultiLineChart.tsx`, add an optional `playheadX?: number` prop
  (data-space x value). When set, draw a thin vertical guide line at that x. Backward
  compatible: undefined renders nothing, existing call sites unchanged.

## The motion engine (driven by real data)

At animation time `tNs` (0 to 50), for the selected drug's `series`:

1. **Drug approach.** Position the ligand on the fixed `approachVector` at radius
   `distanceAt(series, tNs)` from the pocket. Celecoxib falls from about 30 A to about
   2.9 A and locks; dasabuvir stays far and never reaches the pocket. This is the headline
   and it is the literal recorded distance.
2. **Protein flexibility.** Each residue node `i` jitters around its layout position with
   amplitude proportional to `rmsfFor(series, i)` (a small idle oscillation, deterministic
   per node so it reads as shimmer, not noise).
3. **Contacts.** When the ligand is near the pocket, the named top-contact residues
   brighten; the number lit scales with `ncontactsAt(series, tNs)`.
4. **H-bonds.** Draw `round(hbondsAt(series, tNs))` dashed lines between the ligand and
   nearby pocket residues.
5. **Breathing.** Apply a subtle global scale or drift from `proteinRmsdAt`, and once
   associated a small ligand wobble from `ligandRmsdAt` (skipped when null).

## Stylized scene

- Protein: one instanced sphere per residue in `rmsf` (about 849), on a deterministic
  globular shell (illustrative geometry, not the real fold), so residue `i`'s node carries
  `rmsf[i]` exactly. Core nodes darker and stiller, periphery lighter and more flexible. A
  visible pocket region. On mobile the node count is subsampled for performance, the RMSF
  mapping is preserved on the rendered subset.
- Ligand: a small stylized cluster of a few spheres in the drug's accent color.
- Palette and type reuse the dashboard tokens (`--ink`, `--ink-soft`, `--line`, `--paper`,
  `--mono`, the per-drug accent colors already defined in `MD.tsx`).
- Lighting and camera follow the calm, slightly top-down idiom used elsewhere in the project.

## Interaction

- Drug selector: three pills (Celecoxib, Methotrexate, Dasabuvir), default celecoxib.
- Transport: play/pause toggle and a 0 to 50 ns scrub slider. Optional 1x/2x speed toggle.
  Playback loops.
- Live readout (monospace): time (ns), min-distance (A), H-bonds, contacts, all read from
  the real series at the current frame.
- Chart sync: a thin vertical playhead at the current ns on the RMSD, min-distance and
  contacts charts below.

## Honesty and labeling

Caption directly under the scene:

> Stylized view. The approach distance and timing, the per-residue flexibility, the H-bonds
> and the contacts are taken frame-by-frame from the real 50 ns simulation. The protein's
> shape and the drug's exact 3D path are illustrative; the full atomic trajectory was not
> stored.

Plus a "Schematic, not to scale" tag consistent with the rest of the dashboard. No fabricated
numbers enter the scene; everything visible traces to a value in `md.json`.

## Accessibility, performance, mobile

- Respect `prefers-reduced-motion`: no autoplay, render a representative associated frame,
  scrub still works.
- One canvas, one `instancedMesh` for residues, cheap per-frame updates. Interpolate
  `mindist` between stored frames for smooth approach.
- Mobile: smaller canvas height and a reduced node count; controls wrap. Desktop layout
  unchanged from its larger form.

## Testing

- Unit tests in `mdMotion.test.ts` pin landmark values from the real data, for example:
  celecoxib `distanceAt` is large near t=0 and drops below about 3.5 A after about 3 ns;
  dasabuvir `distanceAt` stays well above the pocket radius throughout; `hbondsAt` and
  `ncontactsAt` return values within the series range; `ligandRmsdAt` is null for dasabuvir.
- `tsc -b` and `npm run build` green.
- Visual confirmation is by deploy review (the preview sandbox cannot reach this repo), as
  was done for the property-matched benchmark.

## Non-goals

- No real atomic-trajectory replay (coordinates were not stored). If wanted later, that is a
  separate compute job to re-run MD and export frames, analogous to the docking notebook.
- No new MD runs, drugs, or targets. No changes to the existing charts beyond the optional
  playhead prop.
- No three-up multi-canvas comparison in this version (a possible later add).
