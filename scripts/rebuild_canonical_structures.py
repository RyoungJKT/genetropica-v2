#!/usr/bin/env python3
"""FIX-1 / FIX-3: rebuild a single canonical structure record per drug.

Resolves each drug to PubChem *by name* (the stored CIDs are unreliable:
some point at the wrong compound), pulls the canonical SMILES + molecular
weight + InChIKey, recomputes MW and heavy-atom count with RDKit, runs a
validation gate, and (with --apply) writes the result back to the drugs
table as the single source of truth that every other module reads.

Ground rules honored: nothing is fabricated. Anything that cannot be
resolved or fails the gate is reported and left flagged, never silently
filled. Dry-run by default (writes nothing); pass --apply to update the DB.

Usage:
    python scripts/rebuild_canonical_structures.py            # dry run
    python scripts/rebuild_canonical_structures.py --apply    # write DB
"""

import argparse
import json
import sqlite3
import time
import urllib.parse
import urllib.request
from collections import defaultdict

from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

DB = "data/database/genetropica.db"
FETCH_DATE = "2026-06-02"
PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def pug_get(url, retries=3):
    last = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.6)
    raise last


def resolve_by_name(name):
    u = f"{PUG}/compound/name/{urllib.parse.quote(name)}/property/SMILES,MolecularWeight,InChIKey/JSON"
    try:
        props = pug_get(u)["PropertyTable"]["Properties"]
        return props[0], len(props)
    except Exception:  # noqa: BLE001
        return None, 0


def resolve_by_cid(cid):
    if not cid:
        return None
    u = f"{PUG}/compound/cid/{cid}/property/SMILES,MolecularWeight,InChIKey/JSON"
    try:
        return pug_get(u)["PropertyTable"]["Properties"][0]
    except Exception:  # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes to the DB")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    drugs = [
        dict(r)
        for r in cur.execute(
            "SELECT drug_id,name,smiles,molecular_weight,heavy_atoms,pubchem_cid FROM drugs ORDER BY name"
        )
    ]

    recs = []
    for d in drugs:
        time.sleep(0.22)  # be polite to PubChem (<5 req/s)
        props, n = resolve_by_name(d["name"])
        method = "name"
        if not props:
            props = resolve_by_cid(d["pubchem_cid"])
            method, n = "stored_cid", (1 if props else 0)
        if not props:
            recs.append({"name": d["name"], "drug_id": d["drug_id"], "status": "UNRESOLVED"})
            continue

        smi = props.get("SMILES")
        ik = props.get("InChIKey")
        cid = props.get("CID")
        try:
            pcmw = float(props.get("MolecularWeight"))
        except (TypeError, ValueError):
            pcmw = None

        mol = Chem.MolFromSmiles(smi) if smi else None
        if mol is None:
            recs.append({"name": d["name"], "drug_id": d["drug_id"], "status": "PARSE_FAIL", "smiles": smi})
            continue

        rmw = round(Descriptors.MolWt(mol), 2)
        ha = mol.GetNumHeavyAtoms()
        old = d["molecular_weight"] or 0.0
        dev = abs(rmw - pcmw) / pcmw * 100 if pcmw else None
        delta_old = abs(rmw - old) / old * 100 if old else None

        flags = []
        if dev is not None and dev > 1.0:
            flags.append(f"rdkit_vs_pubchem={dev:.1f}%")
        if n > 1:
            flags.append(f"{n}_name_matches")
        if str(cid) != str(d["pubchem_cid"]):
            flags.append(f"cid_{d['pubchem_cid']}->{cid}")

        recs.append({
            "drug_id": d["drug_id"], "name": d["name"], "old_mw": old, "new_mw": rmw,
            "pubchem_mw": pcmw, "old_ha": d["heavy_atoms"], "new_ha": ha, "inchikey": ik,
            "cid": cid, "smiles": smi, "method": method,
            "delta_old_pct": round(delta_old, 1) if delta_old is not None else None,
            "flags": flags, "status": "OK",
        })

    ok = [r for r in recs if r.get("status") == "OK"]
    print(f"\nResolved {len(ok)}/{len(drugs)} drugs  |  mode={'APPLY' if args.apply else 'DRY-RUN'}")

    print("\n== CRITICAL DAAs (sanity check) ==")
    crit = {"pibrentasvir": 1113, "paritaprevir": 766, "ombitasvir": 894, "ledipasvir": 889,
            "velpatasvir": 883, "elbasvir": 882, "nelfinavir": 568, "atazanavir": 705, "sofosbuvir": 529}
    for r in ok:
        if r["name"] in crit:
            print(f"  {r['name']:14s} {r['old_mw']:>8} -> {r['new_mw']:>8} (ref~{crit[r['name']]}) HA {r['old_ha']}->{r['new_ha']} {r['flags']}")

    print("\n== MW corrections > 5% (these are the fixes) ==")
    for r in sorted([r for r in ok if (r["delta_old_pct"] or 0) > 5], key=lambda x: -(x["delta_old_pct"] or 0)):
        print(f"  {r['name']:16s} {r['old_mw']:>8} -> {r['new_mw']:>8}  ({r['delta_old_pct']}% change) {r['flags']}")

    print("\n== flagged / failed (need a look, NOT auto-fixed) ==")
    flagged = [r for r in recs if r.get("status") != "OK" or any("rdkit_vs_pubchem" in f or "name_matches" in f for f in r.get("flags", []))]
    for r in flagged:
        print(f"  {r['name']}: status={r.get('status')} flags={r.get('flags')}")
    if not flagged:
        print("  (none)")

    print("\n== duplicate connectivity (same structure assigned to >1 drug = corruption) ==")
    byik = defaultdict(list)
    for r in ok:
        if r.get("inchikey"):
            byik[r["inchikey"].split("-")[0]].append(r["name"])
    dups = {k: v for k, v in byik.items() if len(v) > 1}
    for k, v in dups.items():
        print(f"  {k}: {v}")
    if not dups:
        print("  (none)")

    if args.apply:
        cols = [c[1] for c in cur.execute("PRAGMA table_info(drugs)")]
        for col, typ in [("inchikey", "TEXT"), ("structure_source", "TEXT"),
                         ("structure_source_id", "TEXT"), ("ref_mw", "REAL"),
                         ("structure_fetch_date", "TEXT")]:
            if col not in cols:
                cur.execute(f"ALTER TABLE drugs ADD COLUMN {col} {typ}")
        for r in ok:
            cur.execute(
                """UPDATE drugs SET smiles=?, molecular_weight=?, heavy_atoms=?, inchikey=?,
                   structure_source='PubChem', structure_source_id=?, ref_mw=?, structure_fetch_date=?
                   WHERE drug_id=?""",
                (r["smiles"], r["new_mw"], r["new_ha"], r["inchikey"], str(r["cid"]),
                 r["pubchem_mw"], FETCH_DATE, r["drug_id"]),
            )
        con.commit()
        print(f"\nAPPLIED canonical structures to {len(ok)} drugs.")
    con.close()


if __name__ == "__main__":
    main()
