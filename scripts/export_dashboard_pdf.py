#!/usr/bin/env python3
"""Export every dashboard tab's data into a single review-ready PDF.

Reads the SQLite database and all result files, renders supporting figures,
and lays out a complete report that mirrors the 9 dashboard pages while
preserving the project's honest-framing language verbatim.

Usage:  python scripts/export_dashboard_pdf.py
Output: ~/Downloads/GeneTropica_Dashboard_Data_Export_<date>.pdf
"""

import json
import os
import sqlite3
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image, KeepTogether, LongTable, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

# ------------------------------------------------------------------ paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "database", "genetropica.db")
DATE = "2026-06-02"
OUT = os.path.expanduser(f"~/Downloads/GeneTropica_Dashboard_Data_Export_{DATE}.pdf")
FIGS = tempfile.mkdtemp(prefix="gt_figs_")

# ------------------------------------------------------------------ palette
GREEN = colors.HexColor("#1F5740")
GREEN2 = colors.HexColor("#2E7D5B")
CLAY = colors.HexColor("#A8492B")
GOLD = colors.HexColor("#A8742C")
INK = colors.HexColor("#1C1A17")
INKSOFT = colors.HexColor("#544F45")
PAPER2 = colors.HexColor("#ECE6D8")
PAPER3 = colors.HexColor("#E4DCC9")
LINE = colors.HexColor("#D8D0BD")
ROWALT = colors.HexColor("#F4F0E6")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

def q(sql, params=()):
    return [dict(r) for r in cur.execute(sql, params)]

def load_json(rel):
    p = os.path.join(ROOT, rel)
    return json.load(open(p)) if os.path.exists(p) else None

def load_csv(rel):
    import csv as _csv
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return [], []
    with open(p) as f:
        rows = list(_csv.reader(f))
    return rows[0], rows[1:]

# ------------------------------------------------------------------ styles
ss = getSampleStyleSheet()
def style(name, **kw):
    base = kw.pop("parent", ss["Normal"])
    return ParagraphStyle(name, parent=base, **kw)

S_TITLE = style("t", fontName="Helvetica-Bold", fontSize=26, leading=30, textColor=GREEN)
S_SUB = style("s", fontName="Helvetica", fontSize=13, leading=18, textColor=INKSOFT)
S_H1 = style("h1", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=GREEN, spaceBefore=4, spaceAfter=8)
S_H2 = style("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=CLAY, spaceBefore=10, spaceAfter=4)
S_BODY = style("b", fontName="Helvetica", fontSize=9.7, leading=14.5, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6)
S_CAP = style("c", fontName="Helvetica-Oblique", fontSize=8.2, leading=11, textColor=INKSOFT, spaceAfter=4)
S_CELL = style("cell", fontName="Helvetica", fontSize=7.2, leading=8.6, textColor=INK)
S_CELLB = style("cellb", fontName="Helvetica-Bold", fontSize=7.2, leading=8.6, textColor=colors.white)
S_CAVEAT = style("cv", fontName="Helvetica", fontSize=9, leading=13, textColor=INK)
S_CAVEATH = style("cvh", fontName="Helvetica-Bold", fontSize=9.5, leading=13, textColor=CLAY)
S_SMALL = style("sm", fontName="Helvetica", fontSize=8, leading=11, textColor=INKSOFT)

story = []
def P(t, s=S_BODY): story.append(Paragraph(t, s))
def SP(h=6): story.append(Spacer(1, h))

def caveat(title, body):
    inner = [[Paragraph(title, S_CAVEATH)], [Paragraph(body, S_CAVEAT)]]
    t = Table(inner, colWidths=[16.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F6EEE8")),
        ("BOX", (0, 0), (-1, -1), 0.8, CLAY),
        ("LINEBEFORE", (0, 0), (0, -1), 3, CLAY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(t)
    SP(8)

def table(headers, rows, widths, fontsize=7.2, wrapcols=(), repeat=True, align_right=()):
    head = [Paragraph(f"<b>{h}</b>", S_CELLB) for h in headers]
    data = [head]
    for r in rows:
        cells = []
        for i, v in enumerate(r):
            txt = "" if v is None else str(v)
            if i in wrapcols:
                cells.append(Paragraph(txt, S_CELL))
            else:
                cells.append(Paragraph(txt, S_CELL))
        data.append(cells)
    TBL = LongTable if len(rows) > 28 else Table
    t = TBL(data, colWidths=widths, repeatRows=1 if repeat else 0)
    st = [
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROWALT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("FONTSIZE", (0, 0), (-1, -1), fontsize),
    ]
    for c in align_right:
        st.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(st))
    story.append(t)
    SP(6)

def fig(path, width_cm=16.5, cap=None):
    if not os.path.exists(path):
        return
    from PIL import Image as PILImage
    iw, ih = PILImage.open(path).size
    w = width_cm * cm
    h = w * ih / iw
    story.append(Image(path, width=w, height=h))
    if cap:
        P(cap, S_CAP)
    SP(6)

# ============================================================ figures
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#8A8273",
    "axes.titlesize": 11, "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.grid": True, "grid.color": "#E4DCC9", "grid.linewidth": 0.6,
})
HEX = {"green": "#1F5740", "green2": "#2E7D5B", "clay": "#A8492B", "gold": "#A8742C", "slate": "#5B5470"}

def make_roc():
    series = [("Docking (Vina)", "data/validation/roc_docking.csv", HEX["clay"]),
              ("ML rescoring", "data/validation/roc_gnn.csv", HEX["green"]),
              ("Consensus", "data/validation/roc_consensus.csv", HEX["gold"])]
    aucs = load_json("data/validation/roc_results/validation_summary.json") or {}
    key = {"Docking (Vina)": "docking", "ML rescoring": "gnn", "Consensus": "consensus"}
    fig_, ax = plt.subplots(figsize=(6.6, 4.6))
    ax.plot([0, 1], [0, 1], "--", color="#9A9384", lw=1, label="Random (AUC 0.50)")
    for name, rel, col in series:
        hdr, rows = load_csv(rel)
        if not rows:
            continue
        fpr = [float(r[0]) for r in rows]; tpr = [float(r[1]) for r in rows]
        a = aucs.get(key[name], {}).get("auc")
        lbl = f"{name} (AUC {a:.2f})" if a is not None else name
        ax.plot(fpr, tpr, color=col, lw=2, label=lbl)
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("Retrospective ROC: DENV NS5 RdRp (10 actives vs 89 library decoys)")
    ax.legend(loc="lower right", fontsize=8); ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    p = os.path.join(FIGS, "roc.png"); fig_.tight_layout(); fig_.savefig(p, dpi=150); plt.close(fig_)
    return p

def make_conservation_heatmap():
    d = load_json("data/conservation/consurf/analysis_results.json")
    if not d:
        return None
    pi = d["pairwise_identity"]; labels = list(pi.keys())
    M = np.array([[pi[a][b] for b in labels] for a in labels])
    fig_, ax = plt.subplots(figsize=(6.4, 5.2))
    im = ax.imshow(M, cmap="YlGn", vmin=0, vmax=100)
    ax.set_xticks(range(len(labels))); ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8); ax.set_yticklabels(labels, fontsize=8)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center",
                    color="white" if M[i, j] > 55 else "#1C1A17", fontsize=6.5)
    ax.set_title("NS5 RdRp pairwise sequence identity (%)")
    fig_.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.grid(False)
    p = os.path.join(FIGS, "cons_heat.png"); fig_.tight_layout(); fig_.savefig(p, dpi=150); plt.close(fig_)
    return p

def make_conservation_track():
    hdr, rows = load_csv("data/conservation/consurf/conservation_scores.csv")
    if not rows:
        return None
    pos = [int(r[0]) for r in rows]; grade = [int(r[2]) for r in rows]
    fig_, ax = plt.subplots(figsize=(7.4, 2.8))
    ax.bar(pos, grade, width=1.0, color=[plt.cm.RdYlBu((g - 1) / 8) for g in grade])
    ax.set_xlabel("Residue position (DENV-2 NS5)"); ax.set_ylabel("ConSurf grade")
    ax.set_title("Per-position evolutionary conservation (9 = most conserved)")
    ax.set_ylim(0, 9.5)
    p = os.path.join(FIGS, "cons_track.png"); fig_.tight_layout(); fig_.savefig(p, dpi=150); plt.close(fig_)
    return p

def make_ns5_scatter():
    rows = q("""SELECT d.name, d.molecular_weight mw, m.ligand_efficiency le, a.overall_pass admet,
                 (SELECT MIN(vina_score) FROM docking_results dr WHERE dr.drug_id=d.drug_id AND dr.target_id='DENV_NS5') vina
                FROM ml_scores m JOIN drugs d ON d.drug_id=m.drug_id
                LEFT JOIN admet a ON a.drug_id=d.drug_id
                WHERE m.target_id='DENV_NS5' AND m.ligand_efficiency IS NOT NULL""")
    rows = [r for r in rows if r["vina"] is not None]
    if not rows:
        return None
    fig_, ax = plt.subplots(figsize=(6.8, 4.6))
    for pas, col, lbl in [(1, HEX["green"], "ADMET pass"), (0, HEX["clay"], "ADMET flag")]:
        xs = [-r["vina"] for r in rows if (r["admet"] or 0) == pas]
        ys = [r["le"] for r in rows if (r["admet"] or 0) == pas]
        sz = [max(15, (r["mw"] or 300) / 6) for r in rows if (r["admet"] or 0) == pas]
        ax.scatter(xs, ys, s=sz, c=col, alpha=0.7, edgecolors="white", linewidths=0.5, label=lbl)
    ax.set_xlabel("Binding strength  |Vina|  (kcal/mol, higher = stronger)")
    ax.set_ylabel("Ligand efficiency (per heavy atom)")
    ax.set_title("DENV NS5: binding vs efficiency (point size = molecular weight)")
    ax.legend(fontsize=8)
    p = os.path.join(FIGS, "ns5_scatter.png"); fig_.tight_layout(); fig_.savefig(p, dpi=150); plt.close(fig_)
    return p

# ============================================================ build
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(INKSOFT)
    canvas.drawString(1.8 * cm, 1.0 * cm, "GeneTropica  ·  Dashboard data export  ·  Russell Young, British School Jakarta")
    canvas.drawRightString(19.2 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.setStrokeColor(LINE); canvas.line(1.8 * cm, 1.35 * cm, 19.2 * cm, 1.35 * cm)
    canvas.restoreState()

TARGETS = q("SELECT target_id, name, disease, pdb_id, uniprot_id, structure_source, validation_status FROM targets")
TARGET_ROLES = {
    "DENV_NS3": "Cleaves the viral polyprotein into functional components. Essential for dengue virus replication; blocking this enzyme halts the viral life cycle.",
    "DENV_NS5": "RNA-dependent RNA polymerase that copies the viral genome. The primary replication engine of dengue virus and a high-priority drug target.",
    "DENV_E": "Mediates host cell entry through membrane fusion. Inhibiting this protein could prevent the virus from infecting new cells.",
    "CHIKV_nsP2": "Processes the nonstructural polyprotein of chikungunya virus. Critical for viral replication and a validated drug target.",
    "CHIKV_nsP1": "Caps viral mRNA to enable translation by host ribosomes. A unique enzymatic activity that makes it an attractive target for selective inhibitors.",
    "LEPTO_LipL32": "Outer membrane lipoprotein that triggers the host immune response. The most abundant surface protein of pathogenic Leptospira and a key virulence factor.",
}
ORDER = ["DENV_NS5", "DENV_NS3", "DENV_E", "CHIKV_nsP2", "CHIKV_nsP1", "LEPTO_LipL32"]
TGT = {t["target_id"]: t for t in TARGETS}

# ----- title page
story.append(Spacer(1, 2.4 * cm))
P("GeneTropica", S_TITLE)
P("Complete Dashboard Data Export", style("st2", parent=S_TITLE, fontSize=16, textColor=INK))
SP(10)
P("Computational drug repurposing for neglected tropical diseases. A full export of the data shown across all nine dashboard tabs, prepared for academic review.", S_SUB)
SP(6)
P(f"Russell Young · British School Jakarta · {DATE}", S_SMALL)
P('Live dashboard: https://genetropica-production.up.railway.app/ · Source: github.com/RyoungJKT/genetropica-v2', S_SMALL)
SP(18)
caveat("How to read this report (scope and limits)",
       "This project screens 100 FDA-approved drugs against 6 protein targets from 3 neglected tropical diseases using AutoDock Vina docking, a ChEMBL-trained machine-learning prior, ADMET filtering, evolutionary conservation analysis, and 50 ns molecular dynamics. "
       "These are <b>computational predictions, a starting hypothesis for a scientist, not treatments or clinical claims.</b> Key honesty points carried throughout: the machine-learning score is a <b>target-agnostic activity prior</b> (the same drug scores identically for every target), not a per-target predictor; candidates are ranked by <b>two metrics</b> (Vina score and ligand efficiency) over drug-like molecules to control for docking's size bias; sofosbuvir is included as a <b>known-active positive control</b>, not a discovery; retrospective validation for dengue NS5 gave a docking <b>AUC of 0.37 (below random)</b>, reported openly; and <b>MM-PBSA binding free energy was not computed</b> (the molecular dynamics are short unbiased runs that test spontaneous association, not absolute affinity).")
SP(8)
P("Contents: 1. Project overview  ·  2. Disease overview and targets  ·  3. Drug candidate explorer (per target)  ·  4. Scoring and AI insights  ·  5. Methodology validation  ·  6. Evolutionary conservation  ·  7. ADMET profiling  ·  8. Molecular dynamics  ·  9. Methods and reproducibility  ·  Appendices.", S_SMALL)

# ----- 1. overview
story.append(PageBreak())
P("1. Project overview", S_H1)
n_drugs = cur.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
n_dock = cur.execute("SELECT COUNT(*) FROM docking_results").fetchone()[0]
n_admet_pass = cur.execute("SELECT COUNT(*) FROM admet WHERE overall_pass=1").fetchone()[0]
P(f"GeneTropica screens <b>{n_drugs} FDA-approved drugs</b> against <b>6 protein targets</b> drawn from <b>3 neglected tropical diseases</b> (dengue, chikungunya, leptospirosis). The pipeline runs molecular docking ({n_dock} docking results recorded), a machine-learning activity prior, ADMET safety filtering, evolutionary conservation analysis, and molecular-dynamics refinement. The goal is to surface which already-approved, safe medicines are worth a closer experimental look for these under-funded diseases.")
SP(4)
# pipeline + category reference
cats = q("SELECT category, COUNT(*) n FROM drugs GROUP BY category ORDER BY n DESC")
P("Drug library by selection category", S_H2)
table(["Category", "Drugs"], [[c["category"], c["n"]] for c in cats], [13 * cm, 3 * cm], fontsize=8)
P("Categories encode why each drug was chosen (mechanism classes, published-dengue leads, tropical-disease drugs, and deliberate negative/positive controls). Controls are included so the screen can be checked against known answers.", S_CAP)

# ----- 2. disease overview + targets
story.append(PageBreak())
P("2. Disease overview and protein targets", S_H1)
P("Three neglected tropical diseases endemic to Indonesia, with their disease burden context. Dengue has no specific antiviral (supportive care only); chikungunya has no widely available approved antiviral or vaccine; leptospirosis is a bacterial zoonosis where new options could reduce late-stage mortality.", S_BODY)
P("The six protein targets", S_H2)
trows = []
for tid in ORDER:
    t = TGT[tid]
    trows.append([t["disease"], t["name"], t["pdb_id"], t["uniprot_id"], t.get("structure_source", ""), TARGET_ROLES.get(tid, "")])
table(["Disease", "Target", "PDB", "UniProt", "Structure", "Biological role"],
      trows, [2.2 * cm, 3.2 * cm, 1.3 * cm, 1.6 * cm, 1.7 * cm, 6.5 * cm], fontsize=7.4, wrapcols=(1, 5))
P("Retrospective validation status", S_H2)
P("Whether each target's docking has been checked against known actives and inactives. Only NS5 has been retrospectively validated, and it scored below random; every other target is unvalidated, so its rankings are hypothesis-generating only.", S_CAP)
vrows = [[TGT[tid]["name"], TGT[tid].get("validation_status") or "not recorded"] for tid in ORDER]
table(["Target", "Validation status"], vrows, [5.0 * cm, 11.8 * cm], fontsize=7.6, wrapcols=(1,))
caveat("Honest framing on this page",
       "Disease burden figures are real public-health context. Repurposing is attractive here mainly because approved drugs already have established human safety, lowering the regulatory barrier; it does not imply any of these drugs is an effective treatment.")

# ----- 3. drug candidate explorer per target
story.append(PageBreak())
P("3. Drug candidate explorer (per target)", S_H1)
P("For each target, drug-like candidates (molecular weight 250 to 600) ranked by binding strength (AutoDock Vina, more negative = stronger). Ligand efficiency (binding energy per heavy atom) is shown alongside to control for the fact that larger molecules tend to score more strongly. The ML prior is a target-agnostic ligand score, shown as a supporting signal only. ADMET is the overall safety-filter pass/flag; Refs counts PubMed references linking that drug to that target.", S_BODY)
caveat("Ranking caveat (applies to every table below)",
       "Candidates are ranked by AutoDock Vina score and by ligand efficiency, shown side by side, over drug-like candidates. The ML score is a target-agnostic activity prior, not a per-target prediction. For dengue NS5 specifically, retrospective docking accuracy was poor (AUC 0.37), so mechanism and published literature should carry more weight than the docking score for that target.")
fig(make_ns5_scatter(), 14.5, "Figure: the size-bias story for DENV NS5. The strongest raw binders tend to be the largest molecules (low efficiency); drug-like candidates that balance both metrics are the more credible leads.")

for tid in ORDER:
    t = TGT[tid]
    rows = q("""SELECT d.name, d.original_indication ind, d.molecular_weight mw,
                 m.ligand_efficiency le, m.ml_binding_score ml, a.overall_pass admet, a.lipinski_pass lip,
                 (SELECT MIN(vina_score) FROM docking_results dr WHERE dr.drug_id=d.drug_id AND dr.target_id=?) vina,
                 (SELECT COUNT(*) FROM literature l WHERE l.drug_id=d.drug_id AND l.target_id=?) lit
                FROM ml_scores m JOIN drugs d ON d.drug_id=m.drug_id
                LEFT JOIN admet a ON a.drug_id=d.drug_id
                WHERE m.target_id=? AND m.is_druglike=1""", (tid, tid, tid))
    rows = [r for r in rows if r["vina"] is not None]
    rows.sort(key=lambda r: r["vina"])
    total = cur.execute("SELECT COUNT(*) FROM ml_scores WHERE target_id=?", (tid,)).fetchone()[0]
    story.append(Spacer(1, 4))
    P(f"{t['disease']} — {t['name']}  ({tid}, PDB {t['pdb_id']})", S_H2)
    P(f"{len(rows)} drug-like candidates of {total} screened against this target. Ranked by Vina (strongest first).", S_SMALL)
    body = []
    for i, r in enumerate(rows, 1):
        body.append([i, r["name"], r["ind"], f"{r['mw']:.0f}", f"{r['vina']:.2f}",
                     f"{r['le']:.3f}" if r["le"] is not None else "",
                     f"{r['ml']:.2f}" if r["ml"] is not None else "",
                     "Pass" if r["admet"] == 1 else "Flag", r["lit"]])
    table(["#", "Drug", "Original use", "MW", "Vina", "Lig.Eff", "ML", "ADMET", "Refs"],
          body, [0.9 * cm, 3.1 * cm, 4.2 * cm, 1.1 * cm, 1.2 * cm, 1.4 * cm, 1.0 * cm, 1.4 * cm, 1.0 * cm],
          fontsize=7.0, wrapcols=(1, 2), align_right=(3, 4, 5, 6, 8))

# ----- 3b. binding interactions (Binding Viewer tab)
story.append(PageBreak())
P("3b. Representative binding interactions", S_H1)
P("The dashboard's 3D Binding Viewer shows each docked pose inside its protein pocket. A static PDF cannot carry the interactive 3D scene, so the underlying contact data is tabulated here: for the top-ranked drug-like candidate at each target, the protein residues its best pose is predicted to contact, with interaction type and distance. All contacts are predicted from the docked pose, not experimentally observed (see the note below the tables).", S_BODY)
for tid in ORDER:
    t = TGT[tid]
    top = q("""SELECT d.drug_id, d.name,
                (SELECT MIN(vina_score) FROM docking_results dr WHERE dr.drug_id=d.drug_id AND dr.target_id=?) vina
               FROM ml_scores m JOIN drugs d ON d.drug_id=m.drug_id
               WHERE m.target_id=? AND m.is_druglike=1""", (tid, tid))
    top = [r for r in top if r["vina"] is not None]
    if not top:
        continue
    top.sort(key=lambda r: r["vina"])
    lead = top[0]
    inter = q("""SELECT residue_name, residue_number, chain, interaction_type, distance
                 FROM interactions WHERE drug_id=? AND target_id=? AND pose_rank=1
                 ORDER BY distance ASC LIMIT 14""", (lead["drug_id"], tid))
    P(f"{t['disease']} — {t['name']}: top candidate {lead['name']} (Vina {lead['vina']:.2f} kcal/mol)", S_H2)
    if inter:
        table(["Residue", "Number", "Chain", "Interaction type", "Distance (Angstrom)"],
              [[r["residue_name"], r["residue_number"], r["chain"], r["interaction_type"],
                f"{r['distance']:.2f}" if r["distance"] is not None else ""] for r in inter],
              [3 * cm, 2.5 * cm, 2 * cm, 5 * cm, 4 * cm], fontsize=7.6, align_right=(1, 4))
    else:
        P("No tabulated interaction fingerprint recorded for this complex.", S_SMALL)
caveat("How these contacts were derived (read before interpreting)",
       "All contacts are PREDICTED from the single best docked pose (MODEL 1), not observed in an experimental co-crystal structure. Detection is geometric and chemistry-aware: a contact is labelled ionic or salt bridge only when the ligand actually carries an ionizable group of the opposite charge to the residue, so neutral ligands correctly show none; hydrogen bonds require a polar residue atom (N, O, S) within 3.5 Angstrom, hydrophobic contacts a nonpolar carbon within 4.5 Angstrom, and pi-stacking an aromatic residue within 5.5 Angstrom. Residue numbers and chain IDs follow the deposited PDB structure for each target. Read these together with the validation caveats; the docked pose for NS5 in particular may not reflect the true binding mode.")

# ----- 4. scoring + AI insights
story.append(PageBreak())
P("4. Scoring methods and AI insights", S_H1)
P("Two complementary, partially overlapping signals score each drug: a physics-based docking score (AutoDock Vina) and a machine-learning prior (a RandomForest trained on 166 ChEMBL compounds, cross-validated AUC 0.875). They are not fully independent: the normalised Vina score is itself one of the RandomForest's input features, so the ML prior is a complementary signal, not a separate line of evidence. The legacy weighted consensus (0.4 x Vina + 0.6 x ML) is kept in the database for reference but is deliberately not the headline ranking, because weighting the target-agnostic ML term heavily made one molecule top nearly every target.", S_BODY)
caveat("The dengue NS5 validation failure, reported openly",
       "An initial ROC against 8 known DENV NS5 inhibitors and only 78 weakly-matched decoys gave a suspicious AUC of 1.000. On a fairer, library-based test, Vina actually scored AUC = 0.37 for NS5 (below random, a size-bias artifact: the true small-molecule inhibitors are nucleoside analogues that dock weakly versus large protease inhibitors). That failure is reported openly, and it is why, for NS5, mechanism and published literature carry more weight than the docking score.")
# ADMET pass + novel candidates
P("Library-wide ADMET and literature signal", S_H2)
nlit = cur.execute("SELECT COUNT(DISTINCT drug_id) FROM literature").fetchone()[0]
P(f"Of {n_drugs} drugs, {n_admet_pass} pass the overall ADMET safety filter. {nlit} drugs have at least one linked PubMed reference, though most of these links are weak or keyword-only tier and several have PMID title mismatches (every link's evidence tier and NCBI verification are listed in Appendix A, so weak references cannot quietly inflate a candidate's standing). Drugs that score well yet have no prior literature for a target are flagged in the dashboard as candidate (novel) repurposing ideas, to be read with the validation caveats above.", S_BODY)
# category mean vina at NS5
cs = q("SELECT category, mean_vina_score, mean_ml_score, drug_count FROM category_stats WHERE target_id='DENV_NS5' ORDER BY mean_vina_score ASC")
if cs:
    P("Mean scores by drug category at DENV NS5", S_H2)
    table(["Category", "Mean Vina", "Mean ML", "Drugs"],
          [[c["category"], f"{c['mean_vina_score']:.2f}" if c["mean_vina_score"] is not None else "",
            f"{c['mean_ml_score']:.2f}" if c["mean_ml_score"] is not None else "", c["drug_count"]] for c in cs],
          [9 * cm, 2.6 * cm, 2.6 * cm, 2 * cm], fontsize=7.6, align_right=(1, 2, 3))
P("Docking vs ML agreement per target (Pearson r)", S_H2)
corr_rows = []
for tid in ORDER:
    rr = q("""SELECT m.ml_binding_score ml,
               (SELECT MIN(vina_score) FROM docking_results dr WHERE dr.drug_id=m.drug_id AND dr.target_id=?) vina
              FROM ml_scores m WHERE m.target_id=? AND m.ml_binding_score IS NOT NULL""", (tid, tid))
    pairs = [(r["vina"], r["ml"]) for r in rr if r["vina"] is not None]
    if len(pairs) > 2:
        v = np.array([p[0] for p in pairs]); ml = np.array([p[1] for p in pairs])
        rv = float(np.corrcoef(v, ml)[0, 1])
    else:
        rv = float("nan")
    corr_rows.append([TGT[tid]["name"], len(pairs), f"{rv:.2f}" if rv == rv else "n/a"])
table(["Target", "n drugs", "Vina-ML Pearson r"], corr_rows, [9 * cm, 3 * cm, 4.8 * cm], fontsize=8.2, align_right=(1, 2))
P("Low or even negative correlation is expected and not a defect: docking is target-specific physics, while the ML prior is a single target-agnostic ligand score. They are complementary signals, not the same measurement.", S_CAP)

# ----- 5. validation
story.append(PageBreak())
P("5. Methodology validation", S_H1)
vs = load_json("data/validation/roc_results/validation_summary.json") or {}
meta = vs.get("metadata", {})
P(f"Retrospective, library-based validation on the dengue NS5 RdRp target (PDB {meta.get('target_pdb','5CCV')}). The test asks whether the pipeline can separate {meta.get('n_actives','10')} known RdRp inhibitors from {meta.get('n_decoys','89')} unrelated library drugs ({meta.get('n_total','99')} compounds total). ROC AUC of 1.0 is perfect, 0.5 is random.", S_BODY)
fig(make_roc(), 13.5, "Figure: retrospective ROC curves for the three scoring methods on DENV NS5.")
auc_rows = [
    ["Docking (Vina)", f"{vs.get('docking',{}).get('auc',0):.4f}", "Below random (size-bias artifact)"],
    ["ML (RandomForest)", f"{vs.get('gnn',{}).get('auc',0):.4f}", "Near random"],
    ["Consensus (0.4 Vina + 0.6 ML)", f"{vs.get('consensus',{}).get('auc',0):.4f}", "Below acceptable (verdict POOR)"],
    ["Random baseline", "0.5000", "Reference"],
]
table(["Method", "ROC AUC", "Interpretation"], auc_rows, [6.5 * cm, 2.5 * cm, 7.8 * cm], fontsize=8.4, wrapcols=(2,))
ef = vs
P("Enrichment factors (as shown in the dashboard validation tab)", S_H2)
table(["Method", "EF @ 1%", "EF @ 5%", "EF @ 10%"],
      [[{"docking": "Docking (Vina)", "gnn": "ML (RandomForest)", "consensus": "Consensus"}[m],
        f"{ef.get(m,{}).get('ef_1pct',0):.2f}", f"{ef.get(m,{}).get('ef_5pct',0):.2f}", f"{ef.get(m,{}).get('ef_10pct',0):.2f}"]
       for m in ("docking", "gnn", "consensus")],
      [6 * cm, 3 * cm, 3 * cm, 3 * cm], fontsize=8.4, align_right=(1, 2, 3))
# known actives
hdr, drows = load_csv("data/validation/roc_results/docking_scores.csv")
actives = [r for r in drows if str(r[1]).lower() == "true"]
if actives:
    P(f"Known actives in the validation set ({len(actives)})", S_H2)
    table(["Known active (RdRp inhibitor)", "Docking score (kcal/mol)"],
          [[r[0], r[2]] for r in actives], [10 * cm, 6 * cm], fontsize=8, align_right=(1,))
caveat("Validation verdict",
       f"Verdict: <b>{vs.get('verdict','POOR')}</b>. Vina scoring correlates negatively with true RdRp-inhibitor activity here, because the genuine inhibitors are small nucleoside analogues that dock more weakly than large molecules. This is a known limitation of physics-based scoring and is the reason the NS5 ranking should be read alongside mechanism and literature, not the docking score alone. Only DENV NS5 was retrospectively validated; the other five targets do not have an equivalent retrospective test.")

# ----- 6. conservation
story.append(PageBreak())
P("6. Evolutionary conservation", S_H1)
P("How conserved the dengue NS5 polymerase is across related viruses. Highly conserved, functionally essential residues make better drug targets (a higher barrier to resistance) and hint at broad-spectrum potential across flaviviruses.", S_BODY)
fig(make_conservation_heatmap(), 12, "Figure: pairwise sequence identity (%) across 4 dengue serotypes and 5 related viruses, including distantly related HCV.")
fig(make_conservation_track(), 16.5, "Figure: per-position ConSurf conservation grade along the NS5 reference sequence (9 = most conserved).")
cd = load_json("data/conservation/consurf/analysis_results.json") or {}
kr = cd.get("key_residues", [])
if kr:
    P("Key catalytic / binding-site residues across 9 viruses", S_H2)
    viruses = ["DENV-1", "DENV-2", "DENV-3", "DENV-4", "ZIKV", "YFV", "WNV", "JEV", "HCV"]
    krows = []
    for r in kr:
        krows.append([r.get("residue_number"), r.get("reference_aa")] + [r.get(v, "") for v in viruses])
    table(["Resid", "Ref"] + viruses, krows,
          [1.3 * cm] + [1.0 * cm] + [1.55 * cm] * 9, fontsize=7.2, align_right=tuple(range(2, 11)))
mw = cd.get("mann_whitney", {})
if mw:
    P(f"Binding-site residues mean conservation grade {mw.get('binding_mean','?')}/9 vs non-binding {mw.get('nonbinding_mean','?')}/9 "
      f"(Mann-Whitney one-sided p = {mw.get('p_value',0):.3f}, n binding = {mw.get('n_binding','?')}). "
      f"{'Statistically significant.' if mw.get('significant') else 'A strong trend, not significant at p<0.05 given the small binding-residue set.'}", S_BODY)
caveat("Conservation framing",
       "The catalytic GDD motif (Asp663, Asp664) and Arg737 are reported as 100% conserved across all 9 viruses, including HCV. Sofosbuvir, which targets the conserved HCV NS5B RdRp active site, is cited as precedent for the broad-spectrum hypothesis. This supports why a conserved-site RdRp strategy is plausible; it is not itself evidence that any screened drug works against dengue.")

# ----- 7. ADMET
story.append(PageBreak())
P("7. ADMET profiling", S_H1)
prof = load_json("data/admet/profiles.json") or []
P(f"Computed drug-likeness and absorption/distribution properties for {len(prof)} profiled drugs (RDKit descriptors and rule-based filters). Favourable profiles are expected here because these are approved drugs with established pharmacokinetics; the value is in flagging the few that violate rules or carry structural alerts.", S_BODY)
def flag_pass(v):
    if isinstance(v, dict):
        return v.get("pass", v.get("passed"))
    return v
prows = []
for pr in sorted(prof, key=lambda x: -(x.get("drug_likeness_score") or 0)):
    d = pr.get("descriptors", {})
    prows.append([
        pr.get("name", ""),
        f"{d.get('mw',0):.0f}" if d.get("mw") is not None else "",
        f"{d.get('logp',0):.2f}" if d.get("logp") is not None else "",
        f"{d.get('tpsa',0):.0f}" if d.get("tpsa") is not None else "",
        d.get("hbd", ""), d.get("hba", ""), d.get("rotatable_bonds", ""),
        "Yes" if flag_pass(pr.get("lipinski")) else "No",
        "Yes" if pr.get("gi_absorption") in (True, "High", "high") else ("High" if pr.get("gi_absorption")=="High" else "No"),
        "Yes" if pr.get("bbb_permeant") else "No",
        len(pr.get("pains_alerts", []) or []) + len(pr.get("brenk_alerts", []) or []),
        f"{pr.get('drug_likeness_score',0)}",
    ])
table(["Drug", "MW", "LogP", "TPSA", "HBD", "HBA", "RotB", "Lipinski", "GI abs", "BBB", "Alerts", "DL score"],
      prows, [3.0*cm,1.0*cm,1.0*cm,1.0*cm,0.8*cm,0.8*cm,0.9*cm,1.4*cm,1.3*cm,1.0*cm,1.1*cm,1.3*cm],
      fontsize=6.8, wrapcols=(0,), align_right=(1,2,3,4,5,6,10,11))
P("TPSA = topological polar surface area (Angstrom squared). HBD/HBA = hydrogen-bond donors/acceptors. RotB = rotatable bonds. DL score = composite drug-likeness (higher is better). Alerts = count of PAINS + Brenk structural alerts.", S_CAP)

# ----- 8. MD
story.append(PageBreak())
P("8. Molecular dynamics simulation", S_H1)
P("50 ns all-atom molecular dynamics of three candidates with dengue NS5 RdRp (PDB 5CCV, chain A). Force field AMBER99SB-ILDN + GAFF2, TIP3P water, 300 K, 1 bar. Run with GROMACS 2024.4 (NVIDIA H100), analysed with MDAnalysis.", S_BODY)
P("Important framing: the simulation system was built without placing the ligand in the docked pose, so each drug starts about 30 Angstrom away in solvent. These are therefore unbiased association runs (does the drug spontaneously find and hold a binding site?), not docked-pose-stability runs. Celecoxib associates at about 3 ns and stays; methotrexate associates at about 14 ns and remains mobile; dasabuvir never forms a stable bound pose within 50 ns. A single short run is anecdotal and reports neither affinity nor binding free energy.", S_BODY)
hdr, mrows = load_csv("data/md_simulation/comparison/comparison_summary.csv")
if mrows := mrows if False else mrows:
    pass
if mrows:
    table(hdr, mrows, [3.0 * cm] + [(13.5/(len(hdr)-1)) * cm] * (len(hdr) - 1), fontsize=7.0, align_right=tuple(range(1, len(hdr))))
    P("Columns: Prot RMSD = average backbone deviation; Lig RMSD = ligand deviation from its own mean bound pose over the stable binding window (Angstrom, with standard deviation; shown as 'no stable pose' when the drug never settles); Assoc = time the ligand first stably associates; Rg = radius of gyration; HBonds = average hydrogen bonds; plus contact metrics. Ligand RMSD is small only after the drug has bound, and is not referenced to the docked pose, which the run did not start from.", S_CAP)
md_dir = "data/md_simulation/comparison"
for png, cap in [("rmsd_comparison.png", "Left: protein backbone RMSD. Right: ligand RMSD vs its bound pose; the high early values are the drug still in solvent before it associates."),
                 ("hbonds_comparison.png", "Hydrogen-bond count over time and average comparison."),
                 ("rmsf_comparison.png", "Per-residue flexibility (RMSF) along the protein."),
                 ("binding_proxy_comparison.png", "Ligand-protein minimum distance and atom-atom contacts over time.")]:
    fig(os.path.join(ROOT, md_dir, png), 16.0, "Figure: " + cap)
# top contact residues per drug
P("Most persistent contact residues (occupancy over the trajectory)", S_H2)
for drug in ["celecoxib", "methotrexate", "dasabuvir"]:
    hdr2, crows = load_csv(f"{md_dir}/contacts_{drug}.csv")
    if not crows:
        continue
    crows = sorted(crows, key=lambda r: -float(r[1]))[:10]
    txt = ", ".join(f"res {r[0]} ({float(r[1]):.0f}%)" for r in crows)
    P(f"<b>{drug.capitalize()}:</b> {txt}", S_SMALL)
caveat("Molecular dynamics framing",
       "Three candidates were simulated as examples; this is not the full library. The reported metrics (RMSD, RMSF, hydrogen bonds, contacts, minimum distance) are <b>stability proxies</b>. <b>MM-PBSA or other binding free-energy calculations were not performed</b>, and the simulations were not validated against experimental binding data. A large ligand RMSD for a given drug means its pose was not stably maintained during the simulation.")

# ----- 9. methods
story.append(PageBreak())
P("9. Methods and reproducibility", S_H1)
P("Molecular docking", S_H2)
table(["Parameter", "Value"], [
    ["Docking engine", "AutoDock Vina 1.2.7"],
    ["Ligand preparation", "Open Babel 3.1 + RDKit ETKDG conformers"],
    ["Search box", "25 x 25 x 25 Angstrom"],
    ["Exhaustiveness", "8"],
    ["Poses per run", "3 (energy range 3 kcal/mol)"],
    ["Docking runs", "594 of 600 completed (auranofin failed: gold atom unsupported)"],
], [5 * cm, 11.8 * cm], fontsize=8.4, wrapcols=(1,))
P("Per-target docking grid (reproducibility)", S_H2)
GP = {r["target_id"]: r for r in q("SELECT * FROM docking_parameters")}
grows = []
for tid in ORDER:
    g = GP.get(tid)
    if not g:
        continue
    grows.append([TGT[tid]["name"],
                  f"({g['grid_center_x']:.1f}, {g['grid_center_y']:.1f}, {g['grid_center_z']:.1f})",
                  f"{g['grid_size_x']:.0f} x {g['grid_size_y']:.0f} x {g['grid_size_z']:.0f}",
                  str(g["exhaustiveness"]), str(g["num_modes"])])
table(["Target", "Grid center (x, y, z) Angstrom", "Box (Angstrom)", "Exhaust.", "Modes"],
      grows, [4.4 * cm, 5.0 * cm, 3.4 * cm, 1.9 * cm, 1.7 * cm], fontsize=7.6, wrapcols=(0,))
P("Grid centers sit on each target's catalytic or active-site region; the 25 Angstrom cubic box fully encloses the pocket. Publishing these coordinates makes every docking run reproducible.", S_CAP)
P("Machine-learning prior", S_H2)
table(["Parameter", "Value"], [
    ["Model", "scikit-learn RandomForest"],
    ["Features", "2048-bit Morgan fingerprint + normalised Vina score"],
    ["Training data", "166 compounds from ChEMBL (RdRp activity)"],
    ["Cross-validated AUC", "0.875 +/- 0.094"],
    ["Nature", "Target-agnostic ligand prior (same score for all targets)"],
], [5 * cm, 11.8 * cm], fontsize=8.4, wrapcols=(1,))
P("Ranking and consensus", S_H2)
P("Headline ranking: drug-like candidates (MW 250 to 600) ranked by AutoDock Vina score and by ligand efficiency, shown side by side, to control for docking's size bias. A legacy weighted consensus (0.4 x Vina + 0.6 x ML) is retained in the database for reference but is not the headline ranking.", S_BODY)
P("Data sources", S_H2)
table(["Source", "Used for"], [
    ["DrugBank", "FDA-approved drug structures, indications, SMILES"],
    ["PubChem / ZINC15", "Molecular properties, 3D conformers"],
    ["RCSB PDB", "Experimental protein structures"],
    ["UniProt / AlphaFold DB", "Sequences and predicted structures"],
    ["PubMed (E-utilities)", "Keyword literature evidence"],
    ["ChEMBL", "RdRp activity data for the ML prior"],
], [4.5 * cm, 12.3 * cm], fontsize=8.4, wrapcols=(1,))
P("Reproducibility", S_H2)
P("Source code and full pipeline: github.com/RyoungJKT/genetropica-v2. Suggested citation: Russell Young (2026). GeneTropica: drug repurposing for neglected tropical diseases. British School Jakarta.", S_BODY)
caveat("Overall honest summary for the reviewer",
       "GeneTropica is an honest computational screen, not a discovery claim. Its strengths are breadth (100 approved drugs x 6 targets), a transparent two-metric ranking, and openly reported limitations. Its main documented weaknesses are: docking under-ranks the true small-molecule NS5 inhibitors (validated AUC 0.37); the ML prior is target-agnostic; only one target was retrospectively validated; literature linking is keyword-based; and the molecular dynamics are short unbiased association runs (the ligand was not started in the docked pose) that report whether a drug spontaneously binds, not binding free energy (no MM-PBSA). Sofosbuvir appears as a positive control, not a result.")

# ----- appendix A: literature evidence
story.append(PageBreak())
P("Appendix A. Literature evidence (all linked references)", S_H1)
lit = q("""SELECT d.name dn, l.target_id tid, l.pmid, l.relationship rel, l.confidence conf, l.title,
                  l.evidence_tier tier, l.verified ver, l.title_match tmatch
           FROM literature l JOIN drugs d ON d.drug_id=l.drug_id ORDER BY d.name, l.target_id""")
TIER_LABEL = {
    "direct_target": "direct target evidence",
    "mechanistic": "mechanistic",
    "same_pathogen_phenotypic": "same-pathogen phenotypic",
    "related_organism": "related-organism",
    "computational_only": "computational only",
    "weak_keyword": "weak / keyword-only",
}
tier_ct = {}
for r in lit:
    k = r["tier"] or "untiered"
    tier_ct[k] = tier_ct.get(k, 0) + 1
n_mismatch = sum(1 for r in lit if r["tmatch"] == 0)
n_weak = tier_ct.get("weak_keyword", 0) + tier_ct.get("computational_only", 0)
P(f"{len(lit)} drug-target literature links, found by a keyword PubMed search (not a trained relation extractor). Every PMID was checked against NCBI and assigned an evidence tier so weak references cannot inflate a candidate's standing. Of these, {n_weak} are weak/keyword-only or computational-only, and {n_mismatch} have a stored title that does not match the paper the PMID actually resolves to (flagged in the table). Confidence is the keyword-match score (0 to 1).", S_BODY)
P("Evidence tiers (strongest to weakest): " + "; ".join(
    f"{TIER_LABEL.get(k, k)} {tier_ct.get(k, 0)}"
    for k in ["direct_target", "mechanistic", "same_pathogen_phenotypic", "related_organism", "computational_only", "weak_keyword"]
    if tier_ct.get(k, 0)) + ".", S_CAP)
def _litrow(r):
    flag = "  [PMID title mismatch]" if r["tmatch"] == 0 else ""
    return [r["dn"], r["tid"], str(r["pmid"]),
            TIER_LABEL.get(r["tier"], r["tier"] or ""),
            f"{r['conf']:.2f}" if r["conf"] is not None else "",
            (r["title"] or "") + flag]
table(["Drug", "Target", "PMID", "Evidence tier", "Conf.", "Title (stored)"],
      [_litrow(r) for r in lit],
      [2.5 * cm, 1.9 * cm, 1.5 * cm, 2.6 * cm, 0.9 * cm, 7.4 * cm], fontsize=6.6, wrapcols=(0, 3, 5), align_right=(4,))

# ----- appendix B: full candidate rankings (all drugs, all targets)
story.append(PageBreak())
P("Appendix B. Full candidate rankings (every screened drug, all targets)", S_H1)
P("Complete per-target ranking of all screened drugs by binding strength, including non-drug-like molecules (flagged), which are de-emphasised in the headline ranking. This is the full dataset behind the Drug Explorer tab with all filters turned off.", S_BODY)
for tid in ORDER:
    t = TGT[tid]
    rows = q("""SELECT d.name, d.molecular_weight mw, m.ligand_efficiency le, m.is_druglike dl, a.overall_pass admet,
                 (SELECT MIN(vina_score) FROM docking_results dr WHERE dr.drug_id=d.drug_id AND dr.target_id=?) vina
                FROM ml_scores m JOIN drugs d ON d.drug_id=m.drug_id LEFT JOIN admet a ON a.drug_id=d.drug_id
                WHERE m.target_id=?""", (tid, tid))
    rows = [r for r in rows if r["vina"] is not None]
    rows.sort(key=lambda r: r["vina"])
    P(f"{t['disease']} — {t['name']} ({len(rows)} drugs)", S_H2)
    body = [[i, r["name"], f"{r['mw']:.0f}", f"{r['vina']:.2f}",
             f"{r['le']:.3f}" if r["le"] is not None else "",
             "Yes" if r["dl"] == 1 else "No", "Pass" if r["admet"] == 1 else "Flag"]
            for i, r in enumerate(rows, 1)]
    table(["#", "Drug", "MW", "Vina", "Lig.Eff", "Drug-like", "ADMET"], body,
          [0.9 * cm, 4.7 * cm, 1.6 * cm, 1.8 * cm, 2.0 * cm, 2.2 * cm, 2.0 * cm],
          fontsize=6.8, wrapcols=(1,), align_right=(2, 3, 4))

# ------------------------------------------------------------------ render
doc = SimpleDocTemplate(OUT, pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.7 * cm,
                        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                        title="GeneTropica Dashboard Data Export", author="Russell Young")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("WROTE", OUT)
print("SIZE_KB", round(os.path.getsize(OUT) / 1024, 1))
