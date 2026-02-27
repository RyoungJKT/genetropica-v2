"""Run full ADMET profiling on all drugs in the database."""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)

from src.admet.profiles import profile_all_drugs, save_profiles


def main():
    profiles = profile_all_drugs()
    print(f"Profiled {len(profiles)} drugs")

    lipinski_pass = sum(1 for p in profiles if p["lipinski"]["pass"])
    veber_pass = sum(1 for p in profiles if p["veber"]["pass"])
    ghose_pass = sum(1 for p in profiles if p["ghose"]["pass"])
    egan_pass = sum(1 for p in profiles if p["egan"]["pass"])
    pains_clean = sum(1 for p in profiles if len(p["pains_alerts"]) == 0)
    brenk_clean = sum(1 for p in profiles if len(p["brenk_alerts"]) == 0)
    gi_high = sum(1 for p in profiles if p["gi_absorption"] == "High")
    bbb_yes = sum(1 for p in profiles if p["bbb_permeant"] == "Yes")

    n = len(profiles)
    print(f"\nDrug-Likeness Filter Pass Rates:")
    print(f"  Lipinski: {lipinski_pass}/{n} ({100*lipinski_pass/n:.0f}%)")
    print(f"  Veber:    {veber_pass}/{n} ({100*veber_pass/n:.0f}%)")
    print(f"  Ghose:    {ghose_pass}/{n} ({100*ghose_pass/n:.0f}%)")
    print(f"  Egan:     {egan_pass}/{n} ({100*egan_pass/n:.0f}%)")
    print(f"\nStructural Alerts:")
    print(f"  PAINS clean: {pains_clean}/{n} ({100*pains_clean/n:.0f}%)")
    print(f"  Brenk clean: {brenk_clean}/{n} ({100*brenk_clean/n:.0f}%)")
    print(f"\nPharmacokinetics:")
    print(f"  High GI absorption: {gi_high}/{n} ({100*gi_high/n:.0f}%)")
    print(f"  BBB permeant:       {bbb_yes}/{n} ({100*bbb_yes/n:.0f}%)")

    top = [p for p in profiles if p["drug_likeness_score"] == 5]
    print(f"\nTop Candidates (5/5 filters): {len(top)}")
    for p in sorted(top, key=lambda x: x["name"]):
        d = p["descriptors"]
        print(f"  {p['name']:25s} MW={d['mw']:6.1f}  LogP={d['logp']:5.2f}  TPSA={d['tpsa']:6.1f}")

    path = save_profiles(profiles)
    print(f"\nProfiles saved to {path}")


if __name__ == "__main__":
    main()
