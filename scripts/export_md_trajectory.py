#!/usr/bin/env python3
"""Export the real 50 ns MD trajectories for the Dynamics tab's 3D view.

Reads the local GROMACS trajectories (data/md_simulation/*/results/*/md.xtc, gitignored)
and writes, per drug, a small JSON header plus a binary coordinate file into
web/public/data/md_traj/:

  <drug>.json  ligand heavy-atom elements and bonds, per-residue secondary structure,
               per-frame contacts, hydrogen bonds and minimum distance, and the frames
               where the drug switches to a different periodic copy of the protein
  <drug>.bin   Int16 coordinates, 0.01 A units: every frame's 849 protein C-alpha atoms,
               then every frame's ligand heavy atoms

Frames are every 0.25 ns (every 5th saved frame), the same 201 frames the charts use.

Loading mirrors md_reanalyze.load (NoJump, unwrap, centre, nearest-image ligand placement,
backbone alignment to frame 0), so the protein sits still and the drug moves relative to it.
The ligand placement adds one step: after md_reanalyze's anchor-based placement it tries the
27 neighbouring periodic images and keeps the one truly closest to the protein. When the drug
is far out in solvent it sits between the protein and a periodic copy, and the anchor (the
protein atom nearest the ligand's centre) can pick the slightly farther copy.

Also deliberate: every distance here is measured in that
aligned frame WITHOUT the periodic box. md_reanalyze passes the original box to
distance_array after AlignTraj has rotated the coordinates, and a minimum-image
correction against an unrotated box is invalid for rotated coordinates; when the drug
is far from the protein that produces false short distances. Here the protein is whole
and the ligand was placed in its nearest image before alignment, so plain Euclidean
distances in the aligned frame are the true ones. The script checks this against a
box-aware distance on the raw, unrotated coordinates and stops if they disagree.

Does NOT re-simulate. Run: python scripts/export_md_trajectory.py [drug ...]
"""
import glob
import json
import warnings
from pathlib import Path

import numpy as np
import MDAnalysis as mda
from MDAnalysis import transformations as trans
from MDAnalysis.transformations.nojump import NoJump
from MDAnalysis.analysis import align
from MDAnalysis.analysis.dssp import DSSP
from MDAnalysis.analysis.hydrogenbonds.hbond_analysis import HydrogenBondAnalysis as HBA
from MDAnalysis.lib.distances import distance_array, minimize_vectors

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/public/data/md_traj"
DRUGS = ["celecoxib", "methotrexate", "dasabuvir"]
STRIDE = 5          # 50 ps frames -> 0.25 ns
CONTACT_CUT = 4.5   # A, same cutoff as the published contact counts
SCALE = 100         # Int16 units per A
CHECK_TOL = 0.01    # A, allowed disagreement with the raw box-aware distance


def place_ligand(lig, prot):
    """Identical to md_reanalyze.place_ligand."""
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


def nearest_image(lig, prot):
    """Transformation, after place_ligand: move the whole ligand to whichever of the 27
    neighbouring periodic images has the smallest ligand-protein distance. Whole-box
    translations only, so it never changes the ligand's shape or its true position."""
    la = lig.atoms
    pa = prot.atoms
    shifts = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)])

    def wrapped(ts):
        vecs = shifts @ ts.triclinic_dimensions
        pos = la.positions
        best = min(vecs, key=lambda v: distance_array(pos + v, pa.positions).min())
        la.translate(best)
        return ts
    return wrapped


def record_ligand_centre(lig, store, key):
    """Transformation: remember the ligand centre for this frame, so the periodic shift
    that place_ligand + nearest_image applied can be recovered afterwards."""
    la = lig.atoms

    def wrapped(ts):
        store.setdefault(ts.frame, {})[key] = la.center_of_geometry().copy()
        return ts
    return wrapped


def paths(drug):
    d = ROOT / f"data/md_simulation/{drug}/results"
    return glob.glob(str(d / "*/md.tpr"))[0], glob.glob(str(d / "*/md.xtc"))[0]


def load_aligned(drug):
    """md_reanalyze.load plus the nearest_image step (see module docstring).
    Also returns the saved-frame indices where the ligand is shown next to a different
    periodic copy of the protein than in the previous saved frame (an image switch)."""
    tpr, xtc = paths(drug)
    u = mda.Universe(tpr, xtc)
    prot = u.select_atoms("protein")
    lig = u.select_atoms("resname LIG")
    centres = {}
    u.trajectory.add_transformations(
        NoJump(), trans.unwrap(prot), trans.unwrap(lig),
        trans.center_in_box(prot, center="mass"),
        record_ligand_centre(lig, centres, "before"),
        place_ligand(lig, prot), nearest_image(lig, prot),
        record_ligand_centre(lig, centres, "after"),
    )
    u.transfer_to_memory(step=STRIDE)
    align.AlignTraj(u, u, select="protein and backbone", ref_frame=0, in_memory=True).run()
    frames = sorted(centres)
    assert len(frames) == len(u.trajectory), "one recorded placement per saved frame"
    shifts = [centres[f]["after"] - centres[f]["before"] for f in frames]
    # Placement only ever moves the ligand by whole box vectors (over 100 A here), so any
    # change above 1 A between consecutive saved frames is an image switch.
    jumps = [i for i in range(1, len(shifts)) if np.linalg.norm(shifts[i] - shifts[i - 1]) > 1.0]
    return u, jumps


def raw_min_dist(drug):
    """Reference: box-aware minimum distance on the untouched, unrotated coordinates."""
    tpr, xtc = paths(drug)
    u = mda.Universe(tpr, xtc)
    prot = u.select_atoms("protein")
    lig = u.select_atoms("resname LIG")
    return np.array([distance_array(lig.positions, prot.positions, box=ts.dimensions).min()
                     for ts in u.trajectory[::STRIDE]])


def element(name):
    n = name.upper()
    if n.startswith("CL"):
        return "Cl"
    if n.startswith("BR"):
        return "Br"
    return n[0]


def export(drug):
    u, image_jumps = load_aligned(drug)
    n = len(u.trajectory)
    assert len(image_jumps) < n
    prot = u.select_atoms("protein")
    ca = u.select_atoms("protein and name CA")
    lig = u.select_atoms("resname LIG")
    lig_heavy = lig.select_atoms("not name H*")
    heavy_index = {a.index: i for i, a in enumerate(lig_heavy)}
    res_of_atom = np.searchsorted(ca.resids, prot.resids)  # protein atom -> 0-based residue

    bonds = sorted({tuple(sorted((heavy_index[b.atoms[0].index], heavy_index[b.atoms[1].index])))
                    for b in lig_heavy.bonds
                    if b.atoms[0].index in heavy_index and b.atoms[1].index in heavy_index})

    # Secondary structure of the starting frame, for the ribbon's helix and strand widths.
    # DSSP wants one atom named O per residue; the four chain-break C-termini carry OC1/OC2
    # instead, so it runs on a throwaway copy with OC1 renamed.
    u.trajectory[0]
    ref = mda.Universe(paths(drug)[0])
    ref.atoms.positions = u.atoms.positions
    ref.select_atoms("protein and name OC1").names = "O"
    ss = "".join(DSSP(ref.select_atoms("protein and name N CA C O")).run().results.dssp[0])

    ca_xyz = np.zeros((n, len(ca), 3))
    lig_xyz = np.zeros((n, len(lig_heavy), 3))
    min_dist = np.zeros(n)
    n_contacts = np.zeros(n, dtype=int)
    contacts = []
    for i, _ in enumerate(u.trajectory):
        ca_xyz[i] = ca.positions
        lig_xyz[i] = lig_heavy.positions
        da = distance_array(lig.positions, prot.positions)  # aligned frame, no box: see docstring
        min_dist[i] = float(da.min())
        n_contacts[i] = int((da < CONTACT_CUT).sum())
        close = np.unique(res_of_atom[np.where(da < CONTACT_CUT)[1]])
        contacts.append([int(r) for r in close])

    ref = raw_min_dist(drug)
    worst = float(np.abs(ref - min_dist).max())
    if worst > CHECK_TOL:
        raise SystemExit(f"[{drug}] aligned-frame distance disagrees with the raw box-aware "
                         f"distance by {worst:.3f} A; refusing to export")

    # Hydrogen bonds: nitrogen or oxygen donors carrying a real hydrogen (within 1.2 A),
    # nitrogen or oxygen acceptors, D-A 3.5 A, D-H-A 120 deg. md_reanalyze passed whole
    # residues as donors_sel/acceptors_sel ("protein", "resname LIG"), so every atom,
    # carbons and hydrogens included, counted as a donor or acceptor, and water hydrogens
    # were paired with protein carbons; its H-bond counts are not used here.
    # HBA applies the box, so each pair is re-measured in the aligned frame and kept only
    # if truly within 3.5 A.
    polar = "(name N* or name O*)"
    hb = [[] for _ in range(n)]
    for don, hyd, acc in [
        (f"protein and {polar}", "protein and name H*", f"resname LIG and {polar}"),
        (f"resname LIG and {polar}", "resname LIG and name H*", f"protein and {polar}"),
    ]:
        h = HBA(universe=u, donors_sel=don, hydrogens_sel=hyd, acceptors_sel=acc,
                d_a_cutoff=3.5, d_h_a_angle_cutoff=120)
        h.run()
        for fr, d_ix, _h_ix, a_ix, _dist, _ang in h.results.hbonds:
            hb[int(fr)].append((int(d_ix), int(a_ix)))
    hbonds = []
    for i, _ in enumerate(u.trajectory):
        pos = u.atoms.positions
        frame = []
        for d_ix, a_ix in hb[i]:
            if np.linalg.norm(pos[d_ix] - pos[a_ix]) > 3.5:
                continue
            lig_ix, prot_ix = (d_ix, a_ix) if d_ix in heavy_index else (a_ix, d_ix)
            if lig_ix not in heavy_index:
                continue
            ends = {u.atoms[lig_ix].name[0], u.atoms[prot_ix].name[0]}
            if not ends <= {"N", "O"}:
                raise SystemExit(f"[{drug}] H-bond between non-polar atoms {ends}; refusing to export")
            frame.append([heavy_index[lig_ix], *[round(float(c), 2) for c in pos[prot_ix]]])
        hbonds.append(frame)

    # Centre everything on the protein's starting centroid so the scene orbits the protein.
    origin = ca_xyz[0].mean(axis=0)
    ca_xyz -= origin
    lig_xyz -= origin
    for frame in hbonds:
        for h_ in frame:
            h_[1:] = [round(h_[1] - origin[0], 2), round(h_[2] - origin[1], 2), round(h_[3] - origin[2], 2)]

    q = np.round(np.concatenate([ca_xyz.ravel(), lig_xyz.ravel()]) * SCALE)
    if np.abs(q).max() >= 32767:
        raise SystemExit(f"[{drug}] coordinates overflow Int16 at 0.01 A")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{drug}.bin").write_bytes(q.astype("<i2").tobytes())

    meta = {
        "drug": drug,
        "frames": n,
        "dt_ns": 0.25,
        "scale": SCALE,
        "n_residues": len(ca),
        "n_ligand_atoms": len(lig_heavy),
        "ligand_elements": [element(a.name) for a in lig_heavy],
        "ligand_bonds": [list(b) for b in bonds],
        "secondary_structure": ss,
        "min_dist": [round(float(x), 2) for x in min_dist],
        "n_contacts": [int(x) for x in n_contacts],
        "contacts": contacts,
        "hbonds": hbonds,
        "image_jumps": image_jumps,
    }
    (OUT / f"{drug}.json").write_text(json.dumps(meta, separators=(",", ":")))
    print(f"[{drug}] {n} frames, {len(ca)} residues, {len(lig_heavy)} ligand heavy atoms, "
          f"{len(bonds)} bonds; distance check max diff {worst:.4f} A; "
          f"H-bonds per frame {np.mean([len(f) for f in hbonds]):.2f}; "
          f"image switches {len(image_jumps)}; "
          f"bin {q.size * 2 / 1e6:.2f} MB", flush=True)


if __name__ == "__main__":
    import sys
    for drug in sys.argv[1:] or DRUGS:
        export(drug)
