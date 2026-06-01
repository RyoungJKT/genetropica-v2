# Deploying GeneTropica to Streamlit Community Cloud

A step-by-step guide to publishing the dashboard. The repository is already
pushed and clean; the main thing to get right is **shipping the data**, because
the dashboard reads a local database that is normally gitignored.

---

## 1. Ship the data the dashboard reads (the critical step)

A fresh clone (which is what Streamlit Cloud builds from) does **not** contain
the populated database or result files, because they are gitignored. Without
them, every page shows "No data loaded." Commit the dashboard's data so the
deployed app shows the real results.

```bash
cd /path/to/genetropica-v2

# Force-add the populated database and the precomputed result files the
# dashboard reads (these are small; the 2.4 GB raw MD trajectories stay out).
git add -f data/database/genetropica.db
git add -f data/admet/ data/validation/ data/conservation/ md_analysis_results/

# Sanity-check the total size you are about to commit (should be a few MB):
du -sh data/database/genetropica.db data/admet data/validation data/conservation md_analysis_results

git commit -m "Ship dashboard data (database + result files) for deployment"
git push origin main
```

If you would rather keep data out of git, the alternative is to let the app
seed demonstration data on first run (`python scripts/generate_mock_data.py`),
but then the deployed app shows synthetic numbers, not your real results. For a
portfolio deployment, shipping the real data is recommended.

---

## 2. Confirm the app is deploy-ready

- **Entry point:** `app/Home.py`
- **Dependencies:** `requirements.txt` (already present). Heavy or
  system-level packages (AutoDock Vina, GROMACS, Open Babel) are pipeline-only
  and are **not** needed to serve the dashboard. If a Streamlit Cloud build
  fails on one of them, move it out of `requirements.txt` (the dashboard imports
  only Streamlit, pandas, plotly, py3Dmol, rdkit, biopython).
- **Theme:** `.streamlit/config.toml` is committed.
- **Secrets:** none required (see `.streamlit/secrets.toml.example`).

---

## 3. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with the GitHub account that
   owns the repo (RyoungJKT).
2. Click **New app** -> **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `RyoungJKT/genetropica-v2`
   - **Branch:** `main`
   - **Main file path:** `app/Home.py`
4. (Optional) **Advanced settings -> Secrets:** paste anything from
   `.streamlit/secrets.toml.example` only if you plan to re-run the pipeline.
5. Click **Deploy**. First build takes a few minutes (rdkit can be slow).
6. Note the public URL it assigns (e.g. `https://genetropica.streamlit.app`).

---

## 4. After it is live: screenshots and README

1. Visit each of the 9 pages on the live app (or run locally:
   `streamlit run app/Home.py`).
2. Capture a screenshot of each and save into `docs/screenshots/` using the
   filenames the README already references:
   `home.png`, `disease_overview.png`, `drug_explorer.png`,
   `binding_viewer.png`, `ai_insights.png`, `methods.png`.
3. In `README.md`, replace the line "Screenshots will be added after
   deployment." and add the live URL near the top.
4. Commit and push:
   ```bash
   git add docs/screenshots/ README.md
   git commit -m "Add dashboard screenshots and live URL"
   git push origin main
   ```

---

## Rollback

A pre-rewrite mirror of the repository is kept at
`~/genetropica-v2-prerewrite-backup-2026-06-01.git`. If anything about the
published history needs reverting, that mirror has the original commits.
