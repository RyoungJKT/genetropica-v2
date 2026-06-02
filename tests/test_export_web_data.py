import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data"


_EXPORTED = False


def _run():
    global _EXPORTED
    if _EXPORTED:
        return
    subprocess.run([sys.executable, str(ROOT / "scripts" / "export_web_data.py")], check=True)
    _EXPORTED = True


def test_export_produces_core_files():
    _run()
    for name in ["summary.json", "targets.json", "drugs.json"]:
        assert (OUT / name).exists(), f"missing {name}"


def test_summary_counts_match_db():
    _run()
    s = json.loads((OUT / "summary.json").read_text())
    assert s["drugs"] == 100
    assert s["targets"] == 6
    assert s["docking_runs"] == 594


def test_targets_have_validation_status():
    _run()
    t = json.loads((OUT / "targets.json").read_text())
    assert len(t) == 6
    assert all(x.get("validation_status") for x in t)
    ns5 = next(x for x in t if x["target_id"] == "DENV_NS5")
    assert "0.37" in ns5["validation_status"]


def test_drugs_shape_and_corrected_data():
    _run()
    d = {x["name"]: x for x in json.loads((OUT / "drugs.json").read_text())}
    assert len(d) == 100
    assert d["dasabuvir"]["heavy_atoms"] > 0
    # corrected structures: pibrentasvir's real MW is ~1113 Da, not the stale 597
    assert d["pibrentasvir"]["molecular_weight"] > 1000


def test_field_has_targets_and_corrected_ns5():
    _run()
    f = json.loads((OUT / "field.json").read_text())
    assert len(f) == 6 and "DENV_NS5" in f
    ns5 = f["DENV_NS5"]
    keys = ("name", "category", "indication", "mw", "ha", "le", "vina", "dl", "admet")
    assert all(all(k in p for k in keys) for p in ns5)
    druglike = [p for p in ns5 if p["dl"] == 1]
    assert druglike, "expected drug-like NS5 points"
    top = min(druglike, key=lambda p: p["vina"])
    assert top["name"] == "dasabuvir", f"expected dasabuvir as top drug-like NS5, got {top['name']}"
    names = {p["name"] for p in druglike}
    assert "velpatasvir" not in names and "grazoprevir" not in names


def test_admet_export():
    _run()
    a = json.loads((OUT / "admet.json").read_text())
    assert len(a) == 100
    assert "dasabuvir" in a
    assert all("pass" in v for v in a.values())


def test_binding_export():
    _run()
    idx = json.loads((OUT / "binding" / "index.json").read_text())
    assert len(idx) == 6 and "dasabuvir" in idx["DENV_NS5"]
    d = json.loads((OUT / "binding" / "DENV_NS5__dasabuvir.json").read_text())
    assert all("type" in c and "res" in c for c in d["contacts"])
    mol = (OUT / "binding" / "DENV_NS5__dasabuvir.mol").read_text()
    assert "V2000" in mol and " H " in mol  # all-atom molblock with hydrogens
    assert (OUT.parent / "structures" / "DENV_NS5.pdb").exists()


def test_md_export():
    _run()
    md = json.loads((OUT / "md.json").read_text())
    assert len(md["summary"]) == 3
    for d in ("celecoxib", "methotrexate", "dasabuvir"):
        s = md["series"][d]
        assert len(s["rmsd"]) > 50 and len(s["rmsf"]) > 100 and len(s["mindist"]) > 50


def test_conservation_export():
    _run()
    c = json.loads((OUT / "conservation.json").read_text())
    assert len(c["grades"]) > 800
    assert "DENV-2" in c["identity"] and "HCV" in c["identity"]
    assert len(c["key_residues"]) > 0
