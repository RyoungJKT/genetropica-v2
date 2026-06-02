import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data"


def _run():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "export_web_data.py")], check=True)


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
