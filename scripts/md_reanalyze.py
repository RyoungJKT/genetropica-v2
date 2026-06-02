#!/usr/bin/env python3
"""FIX-4 + FIX-14: correct MD trajectory analysis and honest ligand RMSD.

Re-analyzes the existing 50 ns trajectories, fixing the original Colab analysis
(which reported a non-physical ~49 A protein RMSD and a meaningless ligand RMSD)
and correcting a system-setup discovery:

  PBC (FIX-4): the DENV NS5 model is 4 fragments (chain breaks in 5CCV), so the
  protein is split across the periodic box. NoJump (temporal continuity) + unwrap
  on the protein (make each fragment whole) yields a physical ~2-3 A backbone RMSD.

  Setup discovery (FIX-14): the production runs did NOT start from the docked pose.
  The MD system was built by combining a protein and a docked ligand that were in
  different coordinate frames (the docked .mol2 sits in the original 5CCV crystal
  frame near the docking grid centre; the MD protein was renumbered and recentred),
  so the ligand starts ~30 A away in solvent. These are therefore unbiased
  association simulations, not bound-pose-stability runs. We report them as such.

  Ligand RMSD: because the ligand starts in solvent, RMSD against frame 0 is
  meaningless. We reference it to the ligand's own mean pose over the stable bound
  window (min protein-ligand distance < BOUND_CUT for the trajectory tail). If the
  ligand never forms a stable bound pose, the RMSD is left undefined (NaN) rather
  than fabricated. The ligand is made whole and placed in its true minimum-image
  position relative to the protein (triclinic-aware) before alignment.

Minimum-image distances drive the association timeline (PBC-robust). Regenerates
the comparison CSVs and figures consumed by the dashboard and PDF export. Does NOT
re-simulate.

Run: python scripts/md_reanalyze.py
"""
import gc
import glob
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import MDAnalysis as mda
from MDAnalysis import transformations as trans
from MDAnalysis.transformations.nojump import NoJump
from MDAnalysis.analysis import align, rms
from MDAnalysis.analysis.hydrogenbonds.hbond_analysis import HydrogenBondAnalysis as HBA
from MDAnalysis.lib.distances import distance_array, minimize_vectors

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/md_simulation/comparison"
OUT.mkdir(parents=True, exist_ok=True)
DRUGS = ["celecoxib", "methotrexate", "dasabuvir"]
DT_NS = 0.25       # ns per analyzed frame (every 5th of 50 ps)
SAMPLE = 1         # already strided at load; analyze every retained frame
BOUND_CUT = 3.5    # A: a frame counts as "bound" if the ligand is within this of the protein
STABLE_MIN = 20    # frames (= 5 ns): minimum stable bound window to define a ligand RMSD
COLORS = {"celecoxib": "#1F5740", "methotrexate": "#A8492B", "dasabuvir": "#A8742C"}
LABELS = {"celecoxib": "Celecoxib", "methotrexate": "Methotrexate", "dasabuvir": "Dasabuvir"}


def place_ligand(lig, prot):
    """Transformation: make the (whole) ligand sit in the periodic image nearest the
    protein, anchored to the closest protein atom via a triclinic-aware minimum-image
    shift. The shift is always a whole-box translation, so it only fixes the image and
    never distorts the ligand's true position relative to the protein. Robust to the
    4-fragment protein (a centre-of-mass anchor would average fragments across images)."""
    la = lig.atoms
    pa = prot.atoms
    def wrapped(ts):
        box = ts.dimensions
        com = la.center_of_mass()
        d = distance_array(com.reshape(1, 3), pa.positions, box=box)
        anchor = pa.positions[int(d.argmin())]
        miv = minimize_vectors((com - anchor).reshape(1, 3), box)[0]
        la.translate((anchor + miv) - com)
        return ts
    return wrapped


def load(drug):
    d = ROOT / f"data/md_simulation/{drug}/results"
    tpr = glob.glob(str(d / "*/md.tpr"))[0]
    xtc = glob.glob(str(d / "*/md.xtc"))[0]
    u = mda.Universe(tpr, xtc)
    prot = u.select_atoms("protein")
    lig = u.select_atoms("resname LIG")
    # NoJump (temporal continuity) + unwrap protein (whole fragments) + center the
    # protein; the ligand is unwrapped (made whole) and placed in its true minimum-image
    # position relative to the protein, before alignment, while the box is still in its
    # original (un-rotated) frame where the minimum image is valid.
    u.trajectory.add_transformations(
        NoJump(), trans.unwrap(prot), trans.unwrap(lig),
        trans.center_in_box(prot, center="mass"),
        place_ligand(lig, prot),
    )
    u.transfer_to_memory(step=5)  # stride: NoJump valid at 250 ps, unwrap runs on ~200 frames not 1001
    align.AlignTraj(u, u, select="protein and backbone", ref_frame=0, in_memory=True).run()
    return u


rmsd_d, rmsf_d, rg_d, hb_d, bp_d, summary = {}, {}, {}, {}, {}, []

for drug in DRUGS:
    print(f"[{drug}] NoJump + unwrap + align...", flush=True)
    u = load(drug)
    n = len(u.trajectory)
    prot = u.select_atoms("protein")
    lig = u.select_atoms("resname LIG")

    R = rms.RMSD(u, u, select="protein and backbone", ref_frame=0).run()
    arr = R.results.rmsd
    time_ns, prot_rmsd = arr[:, 1] / 1000.0, arr[:, 2]

    # Single pass: protein-aligned ligand positions + PBC-correct min-distance/contacts.
    ligpos = np.zeros((n, len(lig), 3))
    mind = np.zeros(n)
    ncont = np.zeros(n, dtype=int)
    for i, ts in enumerate(u.trajectory):
        ligpos[i] = lig.positions
        da = distance_array(lig.positions, prot.positions, box=ts.dimensions)
        mind[i] = float(da.min())
        ncont[i] = int((da < 4.5).sum())

    # Ligand RMSD vs the ligand's own mean bound pose (these are association runs; the
    # ligand starts in solvent, so frame 0 is not a pose). Undefined if it never settles.
    bound = mind < BOUND_CUT
    stable_start = next((i for i in range(n) if bound[i] and bound[i:].mean() >= 0.8), -1)
    if stable_start >= 0 and (n - stable_start) >= STABLE_MIN:
        ref_pose = ligpos[stable_start:].mean(axis=0)
        diff = ligpos - ref_pose
        lig_rmsd = np.sqrt((diff * diff).sum(axis=2).mean(axis=1))
        lig_avg = f"{lig_rmsd[stable_start:].mean():.2f}"
        lig_std = f"{lig_rmsd[stable_start:].std():.2f}"
        assoc = f"{time_ns[stable_start]:.0f}"
        print(f"  protein RMSD {prot_rmsd[-20:].mean():.2f} A | associates at {assoc} ns | "
              f"ligand RMSD vs bound pose {lig_avg}+/-{lig_std} A", flush=True)
    else:
        lig_rmsd = np.full(n, np.nan)
        lig_avg = lig_std = "no stable pose"
        assoc = "n/a"
        print(f"  protein RMSD {prot_rmsd[-20:].mean():.2f} A | no stable bound pose "
              f"(min-dist median {np.median(mind):.1f} A)", flush=True)

    rmsd_d[drug] = {"time_ns": time_ns, "protein": prot_rmsd, "ligand": lig_rmsd}
    pd.DataFrame({"time_ns": time_ns, "protein_rmsd_A": prot_rmsd,
                  "ligand_rmsd_A": lig_rmsd}).to_csv(OUT / f"rmsd_{drug}.csv", index=False)

    ca = u.select_atoms("protein and name CA")
    F = rms.RMSF(ca).run()
    rmsf_d[drug] = {"resids": ca.resids, "rmsf": F.results.rmsf}
    pd.DataFrame({"resid": ca.resids, "rmsf_A": F.results.rmsf}).to_csv(OUT / f"rmsf_{drug}.csv", index=False)

    rg = np.array([prot.radius_of_gyration() for _ in u.trajectory])
    rg_d[drug] = rg

    counts = np.zeros(n)
    for don, acc in [("protein", "resname LIG"), ("resname LIG", "protein")]:
        try:
            h = HBA(universe=u, donors_sel=don, acceptors_sel=acc, d_a_cutoff=3.5, d_h_a_angle_cutoff=120)
            h.run()
            for hb in h.results.hbonds:
                fi = int(hb[0])
                if fi < n:
                    counts[fi] += 1
        except Exception as e:
            print(f"  hbond ({don}) warn: {e}", flush=True)
    hb_d[drug] = {"time": np.arange(n) * DT_NS, "counts": counts}
    pd.DataFrame({"time_ns": np.arange(n) * DT_NS, "n_hbonds": counts}).to_csv(OUT / f"hbonds_{drug}.csv", index=False)

    rescount, nsamp = {}, 0
    for i, _ in enumerate(u.trajectory):
        if i % SAMPLE:
            continue
        nsamp += 1
        for r in set(u.select_atoms("protein and around 4.5 (resname LIG)").resids):
            rescount[r] = rescount.get(r, 0) + 1
    occ = sorted(((r, c / nsamp * 100) for r, c in rescount.items()), key=lambda x: -x[1])
    pd.DataFrame(occ, columns=["resid", "occupancy_pct"]).to_csv(OUT / f"contacts_{drug}.csv", index=False)

    bp_d[drug] = {"time_ns": time_ns, "min": mind, "nc": ncont}
    pd.DataFrame({"time_ns": time_ns, "min_dist_A": mind, "n_contacts": ncont}).to_csv(OUT / f"binding_proxy_{drug}.csv", index=False)

    summary.append({
        "Drug": drug.capitalize(),
        "Prot_RMSD_avg": f"{prot_rmsd[-100:].mean():.2f}", "Prot_RMSD_std": f"{prot_rmsd[-100:].std():.2f}",
        "Lig_RMSD_avg": lig_avg, "Lig_RMSD_std": lig_std, "Assoc_ns": assoc,
        "Rg_avg": f"{rg.mean():.2f}", "HBonds_avg": f"{counts.mean():.1f}", "HBonds_std": f"{counts.std():.1f}",
        "ContactRes_gt50pct": str(sum(1 for _, o in occ if o > 50)),
        "MinDist_avg": f"{mind.mean():.2f}", "Contacts_avg": f"{ncont.mean():.0f}",
    })
    del u
    gc.collect()

pd.DataFrame(summary).to_csv(OUT / "comparison_summary.csv", index=False)

# ---- figures (filenames the export/dashboard embed) ----
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
for drug in DRUGS:
    ax[0].plot(rmsd_d[drug]["time_ns"], rmsd_d[drug]["protein"], color=COLORS[drug], lw=.8, label=LABELS[drug])
    ax[1].plot(rmsd_d[drug]["time_ns"], rmsd_d[drug]["ligand"], color=COLORS[drug], lw=.8, label=LABELS[drug])
ax[0].set_title("Protein backbone RMSD"); ax[0].set_ylabel("RMSD (Å)")
ax[1].set_title("Ligand RMSD vs its bound pose"); ax[1].set_ylabel("RMSD (Å)")
for a in ax:
    a.set_xlabel("Time (ns)"); a.legend(fontsize=8); a.grid(alpha=.3)
fig.suptitle("Protein stability and ligand association (unbiased MD: ligand starts ~30 Å away in solvent)",
             y=1.02, fontweight="bold")
fig.tight_layout(); fig.savefig(OUT / "rmsd_comparison.png", dpi=150, bbox_inches="tight"); plt.close(fig)

fig, ax = plt.subplots(figsize=(13, 4.4))
for drug in DRUGS:
    ax.plot(rmsf_d[drug]["resids"], rmsf_d[drug]["rmsf"], color=COLORS[drug], lw=.8, label=LABELS[drug])
ax.set_xlabel("Residue"); ax.set_ylabel("RMSF (Å)"); ax.set_title("Per-residue RMSF (Cα, aligned)", fontweight="bold")
ax.legend(fontsize=8); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(OUT / "rmsf_comparison.png", dpi=150, bbox_inches="tight"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
for drug in DRUGS:
    c = hb_d[drug]["counts"]; w = max(1, len(c) // 50)
    sm = np.convolve(c, np.ones(w) / w, mode="valid")
    ax[0].plot(np.arange(len(sm)) * DT_NS, sm, color=COLORS[drug], lw=.9, label=LABELS[drug])
ax[0].set_title("Drug–protein H-bonds (running avg)"); ax[0].set_xlabel("Time (ns)"); ax[0].set_ylabel("H-bonds"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
means = [hb_d[d]["counts"].mean() for d in DRUGS]; stds = [hb_d[d]["counts"].std() for d in DRUGS]
ax[1].bar(range(3), means, yerr=stds, color=[COLORS[d] for d in DRUGS], capsize=5, alpha=.85)
ax[1].set_xticks(range(3)); ax[1].set_xticklabels([LABELS[d] for d in DRUGS]); ax[1].set_title("Mean H-bonds"); ax[1].grid(alpha=.3, axis="y")
fig.suptitle("Hydrogen bonds", y=1.02, fontweight="bold"); fig.tight_layout(); fig.savefig(OUT / "hbonds_comparison.png", dpi=150, bbox_inches="tight"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
for drug in DRUGS:
    ax[0].plot(bp_d[drug]["time_ns"], bp_d[drug]["min"], color=COLORS[drug], lw=.8, label=LABELS[drug])
    ax[1].plot(bp_d[drug]["time_ns"], bp_d[drug]["nc"], color=COLORS[drug], lw=.8, label=LABELS[drug])
ax[0].set_title("Ligand–protein min distance"); ax[0].set_xlabel("Time (ns)"); ax[0].set_ylabel("Min distance (Å)"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
ax[1].set_title("Atom–atom contacts (<4.5 Å)"); ax[1].set_xlabel("Time (ns)"); ax[1].set_ylabel("Contacts"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
fig.suptitle("Binding association (unbiased: ligand starts in solvent and may or may not bind)", y=1.02, fontweight="bold")
fig.tight_layout(); fig.savefig(OUT / "binding_proxy_comparison.png", dpi=150, bbox_inches="tight"); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.4))
for drug in DRUGS:
    ax.plot(rmsd_d[drug]["time_ns"], rg_d[drug], color=COLORS[drug], lw=.8, label=LABELS[drug])
ax.set_xlabel("Time (ns)"); ax.set_ylabel("Rg (Å)"); ax.set_title("Radius of gyration", fontweight="bold"); ax.legend(fontsize=8); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(OUT / "rg_comparison.png", dpi=150, bbox_inches="tight"); plt.close(fig)

print("\n=== corrected comparison_summary.csv ===", flush=True)
print(pd.DataFrame(summary).to_string(index=False), flush=True)
print("\nFIX-4 + FIX-14 done.", flush=True)
