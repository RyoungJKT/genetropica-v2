# Colab — NS5 retrospective enrichment (property-matched decoys)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RyoungJKT/genetropica-v2/blob/main/colab/ns5_enrichment_validation.ipynb)

A self-contained Google Colab notebook that re-validates the dengue **NS5** docking on a
**standard property-matched (DUD-E-style) decoy set** — the rigorous version of the project's
original benchmark, using the same receptor (`5CCV_clean.pdbqt`) and the same grid box, so the
result is directly comparable to the AUC 0.37 already reported.

## Run it
1. Click **Open in Colab** above.
2. **Runtime → Run all** (no GPU needed; AutoDock Vina runs on CPU).
3. It loads the 8 known NS5 inhibitors, pulls a drug-like pool from ChEMBL, picks decoys matched
   to each active on size / logP / H-bonding / charge but topologically dissimilar (true decoys,
   not analogues), docks everything (~1–3 h, **checkpointed/resumable** — a disconnect won't lose
   progress, just re-run the docking cell), and reports ROC-AUC + enrichment factors.
4. It downloads `ns5_enrichment_result.json` — send that back and it gets added to the dashboard's
   Validation tab as a "property-matched decoy benchmark".

## Honest scope
- **NS5-only.** It is the one target with protein-specific known actives; the others have only
  whole-virus phenotypic data, which cannot be used for docking enrichment.
- **Report the AUC honestly, whatever it is.** The value here is the rigorous, standard decoy
  methodology, which makes the benchmark defensible — not a guaranteed better number.

## Files
- `ns5_enrichment_validation.ipynb` — the notebook.
- `5CCV_clean.pdbqt` — the project's prepared NS5 receptor (the notebook fetches it from the repo).
- `_build_nb.py` — regenerates the notebook (`python3 colab/_build_nb.py`).
