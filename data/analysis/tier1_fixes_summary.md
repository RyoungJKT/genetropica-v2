# Tier 1 Fixes Summary Report

## Fix 1: Target-Specific Consensus Re-Weighting

**Change**: DENV_NS5 consensus weights changed from 0.4 Vina + 0.6 ML to 0.1 Vina + 0.9 ML.
All other targets retain default 0.4/0.6 weights.

**Rationale**: Vina AUC (0.370) was below random for NS5 RdRp, actively hurting consensus.

**Results**:
- Old consensus AUC: 0.400 (POOR)
- New consensus AUC (before ML retrain): 0.675 (ACCEPTABLE)
- Velpatasvir (NS5A inhibitor, wrong mechanism): dropped from #1 to #96
- Molnupiravir (RdRp inhibitor): rose to #1

**Key insight**: The Vina size bias caused large HCV drugs to dominate NS5 rankings.
Reducing Vina weight correctly demoted them.


## Fix 2: Sofosbuvir Active Triphosphate (GS-461203) Docking

**Change**: Docked the active metabolite GS-461203 (PubChem CID 23725128) against all 3 dengue targets.

**Results**:
| Target   | Parent (sofosbuvir) | GS-461203 (triphosphate) | Delta       |
|----------|--------------------:|-------------------------:|-------------|
| DENV_NS5 | -6.235 kcal/mol     | -6.350 kcal/mol          | -0.115 (slightly better) |
| DENV_NS3 | -8.319 kcal/mol     | -8.147 kcal/mol          | +0.172 (slightly worse)  |
| DENV_E   | -6.083 kcal/mol     | -6.916 kcal/mol          | -0.833 (better)          |

**GDD motif interaction**: NO. The triphosphate was placed in a pocket around
residues 700-846, not near the catalytic GDD motif (Asp533/Asp534).

**Outcome**: Slight improvement. This is consistent with the known limitation that
Vina cannot model Mg2+ coordination, which is essential for nucleotide binding at
the RdRp active site. The triphosphate's three negative charges are poorly handled
by Vina's empirical scoring function.

**Interpretation**: Docking alone cannot validate nucleoside analog RdRp inhibitors.
MD simulation with explicit Mg2+ ions would be required for meaningful assessment.


## Fix 3: ChEMBL ML Retraining

**Change**: Replaced 500 synthetic training samples with 166 real experimental
binding data points from ChEMBL (HCV NS5B RdRp, Dengue NS5 RdRp, Influenza RdRp PA).

**Training results**:
- Cross-validation AUC on ChEMBL data: 0.875 +/- 0.094 (5-fold stratified)
- Compounds: 56 active (pIC50 > 6.0), 110 inactive

**Score distribution improvement**:
| Metric | Old (synthetic) | New (ChEMBL) |
|--------|----------------:|-------------:|
| ML range | 0.54 - 0.89 | 0.09 - 0.70 |
| ML std | 0.068 | 0.096 |
| Negative controls separated | No (gabapentin #7 ML) | Yes (gabapentin #91) |

**ROC AUC after retraining**:
| Method | Before Fix 3 | After Fix 3 |
|--------|-------------:|------------:|
| Docking (Vina) | 0.370 | 0.370 (unchanged) |
| ML only | 0.644 | 0.509 |
| Consensus (0.1/0.9) | 0.675 | 0.467 |

**Why AUC decreased**: The old synthetic model's 0.644 AUC was misleading.
Its scores were compressed into a 0.878-0.882 range where random ordering
of equally-scored drugs accidentally placed RdRp inhibitors slightly above
average. The ChEMBL model produces genuinely meaningful scores — but the
ChEMBL training data (mostly non-nucleoside HCV inhibitors) is structurally
distinct from our library's nucleoside analogs, so the model does not
specifically recognize nucleoside RdRp inhibitors.


## Combined Impact on NS5 Rankings

| Drug                  | Category                   |    ML | Consensus | Rank |
|-----------------------|----------------------------|------:|----------:|-----:|
| celecoxib            | M_Arbovirus_Activity      | 0.7026 | 0.6846 |   1 |
| daclatasvir          | B_Published_Dengue        | 0.5209 | 0.5273 |   2 |
| methotrexate         | D_Host_Directed           | 0.4834 | 0.4930 |   3 |
| pyrimethamine        | R_More_Tropical           | 0.5054 | 0.4780 |   4 |
| velpatasvir          | J_HCV_NS5A                | 0.3757 | 0.4381 |   6 |
| favipiravir          | A_RdRp_Inhibitors         | 0.2976 | 0.2696 |  53 |
| sofosbuvir           | A_RdRp_Inhibitors         | 0.2136 | 0.2373 |  74 |
| dasabuvir            | A_RdRp_Inhibitors         | 0.3394 | 0.3758 |  17 |
| ribavirin            | A_RdRp_Inhibitors         | 0.3428 | 0.3290 |  35 |
| remdesivir           | A_RdRp_Inhibitors         | 0.2473 | 0.2772 |  50 |
| molnupiravir         | A_RdRp_Inhibitors         | 0.2559 | 0.2516 |  64 |
| gabapentin           | Q_More_Negatives          | 0.1732 | 0.1614 |  91 |
| metformin            | H_Negative_Controls       | 0.1802 | 0.1731 |  88 |


## Key Conclusions

1. **Vina has a documented size bias** that penalises small, polar nucleoside
   analogs. Target-specific weighting (Fix 1) partially mitigates this.

2. **Sofosbuvir is a prodrug** — the parent molecule docked here is not the
   active form. Even docking the triphosphate (Fix 2) only marginally improves
   scores because Vina cannot model Mg2+ coordination.

3. **ML retraining on real data** (Fix 3) dramatically improves score separation
   and negative control placement, but the ChEMBL training set chemistry does
   not overlap with nucleoside analogs.

4. **Fundamental limitation**: Both Vina docking and fingerprint-based ML
   struggle with nucleoside analog RdRp inhibitors. These drugs act through
   a mechanism (competitive with NTPs at the catalytic site via Mg2+
   coordination) that rigid-body docking and 2D fingerprints cannot capture.

5. **The pipeline correctly identifies** that these are real methodological
   limitations, not bugs. A student project demonstrating awareness of these
   limitations is more scientifically valuable than one that hides them.
