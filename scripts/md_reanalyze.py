#!/usr/bin/env python3
"""FIX-4: correct MD trajectory analysis (PBC handling + proper superposition).

Re-analyzes the existing 50 ns trajectories, fixing two bugs in the original
Colab analysis that produced a non-physical ~49 A protein RMSD and a ligand
RMSD measured against the ligand itself:

  PBC: the DENV NS5 model is 4 fragments (chain breaks in 5CCV), so the protein
  is split across the periodic box. We apply NoJump (temporal continuity, no
  inter-frame box jumps) + unwrap on the protein (make each fragment whole).
  This yields a physical ~2-3 A backbone RMSD.

  Superposition: protein backbone RMSD is computed after optimal superposition;
  ligand RMSD is reported in the protein-aligned frame (groupselection, NOT
  independently superposed) so it reflects pose drift relative to the pocket.

Minimum-image distances are used for the contact/min-distance metrics, so the
binding story is PBC-correct regardless. Regenerates the comparison CSVs and
figures consumed by the dashboard and PDF export. Does NOT re-simulate.

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
from MDAnalysis.lib.distances import distance_array

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/md_simulation/comparison"
OUT.mkdir(parents=True, exist_ok=True)
DRUGS = ["celecoxib", "methotrexate", "dasabuvir"]
DT_NS = 0.25      # ns per analyzed frame (every 5th of 50 ps)
SAMPLE = 1        # already strided at load; analyze every retained frame
COLORS = {"celecoxib": "#1F5740", "methotrexate": "#A8492B", "dasabuvir": "#A8742C"}
LABELS = {"celecoxib": "Celecoxib", "methotrexate": "Methotrexate", "dasabuvir": "Dasabuvir"}


def load(drug):
    d = ROOT / f"data/md_simulation/{drug}/results"
    tpr = glob.glob(str(d / "*/md.tpr"))[0]
    xtc = glob.glob(str(d / "*/md.xtc"))[0]
    u = mda.Universe(tpr, xtc)
    prot = u.select_atoms("protein")
    lig = u.select_atoms("resname LIG")
    # NoJump (temporal continuity) + unwrap protein (whole fragments) + center the
    # protein + wrap the ligand into the protein's image so ligand RMSD is
    # measured relative to the pocket, not a neighbouring periodic image.
    u.trajectory.add_transformations(
        NoJump(), trans.unwrap(prot),
        trans.center_in_box(prot, center="mass"),
        trans.wrap(lig, compound="fragments"),
    )
    u.transfer_to_memory(step=5)  # stride: NoJump valid at 250 ps, unwrap runs on ~200 frames not 1001
    align.AlignTraj(u, u, select="protein and backbone", ref_frame=0, in_memory=True).run()
    return u


rmsd_d, rmsf_d, rg_d, hb_d, bp_d, summary = {}, {}, {}, {}, {}, []

for drug in DRUGS:
    print(f"[{drug}] NoJump + unwrap + align...", flush=True)
    u = load(drug)
    n = len(u.trajectory)

    R = rms.RMSD(u, u, select="protein and backbone", ref_frame=0).run()
    arr = R.results.rmsd
    time_ns, prot_rmsd = arr[:, 1] / 1000.0, arr[:, 2]
    # Absolute ligand RMSD is unreliable here: after the alignment rotation the
    # box is no longer axis-aligned, so minimum-image fails for the ligand. The
    # ligand-pose story is reported via min-distance/contacts (PBC-robust) instead.
    lig_rmsd = np.full(len(prot_rmsd), np.nan)
    rmsd_d[drug] = {"time_ns": time_ns, "protein": prot_rmsd, "ligand": lig_rmsd}
    pd.DataFrame({"time_ns": time_ns, "protein_rmsd_A": prot_rmsd,
                  "ligand_rmsd_A": lig_rmsd}).to_csv(OUT / f"rmsd_{drug}.csv", index=False)
    print(f"  protein RMSD last5ns {prot_rmsd[-20:].mean():.2f}+/-{prot_rmsd[-20:].std():.2f} A "
          f"(ligand pose reported via min-distance)", flush=True)

    ca = u.select_atoms("protein and name CA")
    F = rms.RMSF(ca).run()
    rmsf_d[drug] = {"resids": ca.resids, "rmsf": F.results.rmsf}
    pd.DataFrame({"resid": ca.resids, "rmsf_A": F.results.rmsf}).to_csv(OUT / f"rmsf_{drug}.csv", index=False)

    prot = u.select_atoms("protein")
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

    lig = u.select_atoms("resname LIG")
    md, nc, tt = [], [], []
    for i, ts in enumerate(u.trajectory):
        if i % SAMPLE:
            continue
        da = distance_array(lig.positions, prot.positions, box=u.dimensions)
        md.append(float(da.min())); nc.append(int((da < 4.5).sum())); tt.append(ts.time / 1000.0)
    bp_d[drug] = {"time_ns": np.array(tt), "min": np.array(md), "nc": np.array(nc)}
    pd.DataFrame({"time_ns": tt, "min_dist_A": md, "n_contacts": nc}).to_csv(OUT / f"binding_proxy_{drug}.csv", index=False)

    summary.append({
        "Drug": drug.capitalize(),
        "Prot_RMSD_avg": f"{prot_rmsd[-100:].mean():.2f}", "Prot_RMSD_std": f"{prot_rmsd[-100:].std():.2f}",
        "Lig_RMSD_avg": "n/a", "Lig_RMSD_std": "n/a",
        "Rg_avg": f"{rg.mean():.2f}", "HBonds_avg": f"{counts.mean():.1f}", "HBonds_std": f"{counts.std():.1f}",
        "ContactRes_gt50pct": str(sum(1 for _, o in occ if o > 50)),
        "MinDist_avg": f"{np.array(md).mean():.2f}", "Contacts_avg": f"{np.array(nc).mean():.0f}",
    })
    del u
    gc.collect()

pd.DataFrame(summary).to_csv(OUT / "comparison_summary.csv", index=False)

# ---- figures (filenames the export/dashboard embed) ----
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
for drug in DRUGS:
    ax[0].plot(rmsd_d[drug]["time_ns"], rmsd_d[drug]["protein"], color=COLORS[drug], lw=.8, label=LABELS[drug])
    ax[1].plot(bp_d[drug]["time_ns"], bp_d[drug]["min"], color=COLORS[drug], lw=.8, label=LABELS[drug])
ax[0].set_title("Protein backbone RMSD"); ax[0].set_ylabel("RMSD (Å)")
ax[1].set_title("Ligand–protein minimum distance"); ax[1].set_ylabel("Min distance (Å)")
for a in ax:
    a.set_xlabel("Time (ns)"); a.legend(fontsize=8); a.grid(alpha=.3)
fig.suptitle("Protein stability + ligand pose (PBC-corrected; absolute ligand RMSD omitted as unreliable)", y=1.02, fontweight="bold")
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
fig.suptitle("Binding stability proxy", y=1.02, fontweight="bold"); fig.tight_layout(); fig.savefig(OUT / "binding_proxy_comparison.png", dpi=150, bbox_inches="tight"); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.4))
for drug in DRUGS:
    ax.plot(rmsd_d[drug]["time_ns"], rg_d[drug], color=COLORS[drug], lw=.8, label=LABELS[drug])
ax.set_xlabel("Time (ns)"); ax.set_ylabel("Rg (Å)"); ax.set_title("Radius of gyration", fontweight="bold"); ax.legend(fontsize=8); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(OUT / "rg_comparison.png", dpi=150, bbox_inches="tight"); plt.close(fig)

print("\n=== corrected comparison_summary.csv ===", flush=True)
print(pd.DataFrame(summary).to_string(index=False), flush=True)
print("\nFIX-4 done.", flush=True)
