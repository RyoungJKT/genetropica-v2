"""DrugBank/ZINC15 drug structure downloader.

Provides functions to download and parse FDA-approved drug data,
with a curated fallback list for development without external downloads.
"""

import logging
from pathlib import Path
from typing import Optional

import requests

from src.utils.config import DB_PATH, RAW_DIR
from src.utils.db import get_connection, init_db

logger = logging.getLogger(__name__)

_DRUGBANK_OPEN_URL = "https://go.drugbank.com/releases/latest/downloads/all-open-structures"

# ─── Curated FDA-approved drug list (fallback) ───────────────
# 100 well-known drugs with name, DrugBank ID, SMILES, MW, LogP, indication

CURATED_DRUGS: list[dict] = [
    {"name": "aspirin", "drugbank_id": "DB00945", "smiles": "CC(=O)Oc1ccccc1C(O)=O", "molecular_weight": 180.16, "logp": 1.2, "original_indication": "pain and inflammation"},
    {"name": "metformin", "drugbank_id": "DB00331", "smiles": "CN(C)C(=N)NC(N)=N", "molecular_weight": 129.16, "logp": -1.4, "original_indication": "type 2 diabetes"},
    {"name": "ibuprofen", "drugbank_id": "DB01050", "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O", "molecular_weight": 206.28, "logp": 3.97, "original_indication": "pain and inflammation"},
    {"name": "acetaminophen", "drugbank_id": "DB00316", "smiles": "CC(=O)Nc1ccc(O)cc1", "molecular_weight": 151.16, "logp": 0.46, "original_indication": "pain and fever"},
    {"name": "amoxicillin", "drugbank_id": "DB01060", "smiles": "CC1(C)SC2C(NC(=O)C(N)c3ccc(O)cc3)C(=O)N2C1C(O)=O", "molecular_weight": 365.40, "logp": 0.87, "original_indication": "bacterial infections"},
    {"name": "lisinopril", "drugbank_id": "DB00722", "smiles": "NCCCC[C@@H](N[C@@H](CCc1ccccc1)C(O)=O)C(=O)N1CCC[C@H]1C(O)=O", "molecular_weight": 405.49, "logp": -0.85, "original_indication": "hypertension"},
    {"name": "atorvastatin", "drugbank_id": "DB01076", "smiles": "CC(C)c1n(CC[C@@H](O)C[C@@H](O)CC(O)=O)c(c2ccc(F)cc2)c(c1c1ccccc1)C(=O)Nc1ccccc1", "molecular_weight": 558.64, "logp": 4.46, "original_indication": "hypercholesterolemia"},
    {"name": "metoprolol", "drugbank_id": "DB00264", "smiles": "COCCc1ccc(OCC(O)CNC(C)C)cc1", "molecular_weight": 267.36, "logp": 1.88, "original_indication": "hypertension"},
    {"name": "omeprazole", "drugbank_id": "DB00338", "smiles": "COc1ccc2[nH]c(S(=O)Cc3ncc(C)c(OC)c3C)nc2c1", "molecular_weight": 345.42, "logp": 2.23, "original_indication": "gastric ulcers"},
    {"name": "losartan", "drugbank_id": "DB00678", "smiles": "CCCCc1nc(Cl)c(CO)n1Cc1ccc(c2ccccc2c2nn[nH]n2)cc1", "molecular_weight": 422.91, "logp": 4.01, "original_indication": "hypertension"},
    {"name": "amlodipine", "drugbank_id": "DB00381", "smiles": "CCOC(=O)C1=C(COCCN)NC(C)=C(C1c1ccccc1Cl)C(=O)OC", "molecular_weight": 408.88, "logp": 3.0, "original_indication": "hypertension"},
    {"name": "simvastatin", "drugbank_id": "DB00641", "smiles": "CCC(C)(C)C(=O)OC1CC(O)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C12", "molecular_weight": 418.57, "logp": 4.68, "original_indication": "hypercholesterolemia"},
    {"name": "levothyroxine", "drugbank_id": "DB00451", "smiles": "NC(Cc1cc(I)c(Oc2cc(I)c(O)c(I)c2)c(I)c1)C(O)=O", "molecular_weight": 776.87, "logp": 4.12, "original_indication": "hypothyroidism"},
    {"name": "azithromycin", "drugbank_id": "DB00207", "smiles": "CCC1OC(=O)C(C)C(OC2CC(C)(OC)C(O)C(C)O2)C(C)C(OC2OC(C)CC(N(C)C)C2O)C(C)(O)CC(C)CN(C)C1C(C)O", "molecular_weight": 748.98, "logp": 4.02, "original_indication": "bacterial infections"},
    {"name": "hydrochlorothiazide", "drugbank_id": "DB00999", "smiles": "NS(=O)(=O)c1cc2c(cc1Cl)NCNS2(=O)=O", "molecular_weight": 297.74, "logp": -0.07, "original_indication": "hypertension"},
    {"name": "gabapentin", "drugbank_id": "DB00996", "smiles": "NCC1(CC(O)=O)CCCCC1", "molecular_weight": 171.24, "logp": -1.1, "original_indication": "epilepsy"},
    {"name": "sertraline", "drugbank_id": "DB01104", "smiles": "CNC1CCC(c2ccc(Cl)c(Cl)c2)c2ccccc21", "molecular_weight": 306.23, "logp": 5.29, "original_indication": "depression"},
    {"name": "fluoxetine", "drugbank_id": "DB00472", "smiles": "CNCCC(Oc1ccc(C(F)(F)F)cc1)c1ccccc1", "molecular_weight": 309.33, "logp": 4.05, "original_indication": "depression"},
    {"name": "ciprofloxacin", "drugbank_id": "DB00537", "smiles": "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O", "molecular_weight": 331.34, "logp": 0.28, "original_indication": "bacterial infections"},
    {"name": "prednisone", "drugbank_id": "DB00635", "smiles": "CC12CC(=O)C3C(CCC4=CC(=O)C=CC34C)C1CCC2(O)C(=O)CO", "molecular_weight": 358.43, "logp": 1.46, "original_indication": "inflammation"},
    {"name": "albuterol", "drugbank_id": "DB01001", "smiles": "CC(C)(C)NCC(O)c1ccc(O)c(CO)c1", "molecular_weight": 239.31, "logp": 0.64, "original_indication": "asthma"},
    {"name": "warfarin", "drugbank_id": "DB00682", "smiles": "CC(=O)CC(c1ccccc1)c1c(O)c2ccccc2oc1=O", "molecular_weight": 308.33, "logp": 2.7, "original_indication": "thromboembolism"},
    {"name": "clopidogrel", "drugbank_id": "DB00758", "smiles": "COC(=O)C(c1ccccc1Cl)N1CCc2sccc2C1", "molecular_weight": 321.82, "logp": 3.8, "original_indication": "thrombosis prevention"},
    {"name": "montelukast", "drugbank_id": "DB00471", "smiles": "CC(C)(O)c1ccccc1CCSc1cc2c(cc1Cl)C(C(=O)O)=CC2c1cccc(/C=C/c2ccc3ccc(Cl)cc3n2)c1", "molecular_weight": 586.18, "logp": 7.9, "original_indication": "asthma"},
    {"name": "pantoprazole", "drugbank_id": "DB00213", "smiles": "COc1ccnc(CS(=O)c2nc3cc(OC(F)F)ccc3[nH]2)c1OC", "molecular_weight": 383.37, "logp": 0.5, "original_indication": "gastric ulcers"},
    {"name": "escitalopram", "drugbank_id": "DB01175", "smiles": "Fc1ccc(C2(CCNCC2)OCc2cc3ccccc3s2)cc1", "molecular_weight": 324.39, "logp": 3.5, "original_indication": "depression"},
    {"name": "tamsulosin", "drugbank_id": "DB00706", "smiles": "CCOc1ccc(CC(C)NCC(O)c2ccc(OC)c(S(N)(=O)=O)c2)cc1", "molecular_weight": 408.51, "logp": 2.2, "original_indication": "benign prostatic hyperplasia"},
    {"name": "duloxetine", "drugbank_id": "DB00476", "smiles": "CNCC(Oc1cccc2ccccc12)c1cccs1", "molecular_weight": 297.41, "logp": 4.2, "original_indication": "depression"},
    {"name": "rosuvastatin", "drugbank_id": "DB01098", "smiles": "CC(C)c1nc(N(C)S(C)(=O)=O)nc(c1/C=C/C(O)CC(O)CC(O)=O)c1ccc(F)cc1", "molecular_weight": 481.54, "logp": 1.6, "original_indication": "hypercholesterolemia"},
    {"name": "tramadol", "drugbank_id": "DB00193", "smiles": "COc1cccc(C2(O)CCCC(CN(C)C)C2)c1", "molecular_weight": 263.37, "logp": 1.35, "original_indication": "pain"},
    {"name": "furosemide", "drugbank_id": "DB00695", "smiles": "NS(=O)(=O)c1cc(C(O)=O)c(NCc2ccco2)cc1Cl", "molecular_weight": 330.74, "logp": 2.03, "original_indication": "edema"},
    {"name": "doxycycline", "drugbank_id": "DB00254", "smiles": "CC1C2C(O)C3C(N(C)C)C(O)=C(C(N)=O)C(=O)C3(O)C(O)=C2C(=O)c2c(O)cccc21", "molecular_weight": 444.43, "logp": -0.02, "original_indication": "bacterial infections"},
    {"name": "cephalexin", "drugbank_id": "DB00567", "smiles": "CC1=C(C(=O)O)N2C(=O)C(NC(=O)C(N)c3ccccc3)C2SC1", "molecular_weight": 347.39, "logp": 0.65, "original_indication": "bacterial infections"},
    {"name": "naproxen", "drugbank_id": "DB00788", "smiles": "COc1ccc2cc(CC(C)C(O)=O)ccc2c1", "molecular_weight": 230.26, "logp": 3.18, "original_indication": "pain and inflammation"},
    {"name": "cetirizine", "drugbank_id": "DB00341", "smiles": "OC(=O)COCCN1CCN(CC1)C(c1ccccc1)c1ccc(Cl)cc1", "molecular_weight": 388.89, "logp": 1.7, "original_indication": "allergies"},
    {"name": "loratadine", "drugbank_id": "DB00455", "smiles": "CCOC(=O)N1CCC(=C2c3ccc(Cl)cc3CCc3cccnc32)CC1", "molecular_weight": 382.88, "logp": 5.2, "original_indication": "allergies"},
    {"name": "ranitidine", "drugbank_id": "DB00863", "smiles": "CNC(/N=C/[N+](=O)[O-])NCCSCc1ccc(CN(C)C)o1", "molecular_weight": 314.40, "logp": 0.27, "original_indication": "gastric ulcers"},
    {"name": "clonazepam", "drugbank_id": "DB01068", "smiles": "OC1N=C(c2ccccc2Cl)c2cc([N+](=O)[O-])ccc2NC1=O", "molecular_weight": 315.71, "logp": 2.41, "original_indication": "epilepsy"},
    {"name": "alprazolam", "drugbank_id": "DB00404", "smiles": "Cc1nnc2n1-c1ccc(Cl)cc1C(c1ccccc1)=NC2", "molecular_weight": 308.76, "logp": 2.12, "original_indication": "anxiety"},
    {"name": "diazepam", "drugbank_id": "DB00829", "smiles": "CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21", "molecular_weight": 284.74, "logp": 2.82, "original_indication": "anxiety"},
    {"name": "sildenafil", "drugbank_id": "DB00203", "smiles": "CCCc1nn(C)c2c1nc(nc2OCC)c1cc(ccc1OCC)S(=O)(=O)N1CCN(C)CC1", "molecular_weight": 474.58, "logp": 2.75, "original_indication": "erectile dysfunction"},
    {"name": "tadalafil", "drugbank_id": "DB00820", "smiles": "CN1CC(=O)N2C(Cc3c([nH]c4ccccc34)C2c2ccc3OCOc3c2)C1=O", "molecular_weight": 389.40, "logp": 1.7, "original_indication": "erectile dysfunction"},
    {"name": "finasteride", "drugbank_id": "DB01216", "smiles": "CC(C)(C)NC(=O)C1CCC2C3CCC4=CC(=O)CCC4(C)C3C(=O)CC12C", "molecular_weight": 372.54, "logp": 3.03, "original_indication": "benign prostatic hyperplasia"},
    {"name": "spironolactone", "drugbank_id": "DB00421", "smiles": "CC(=O)SC1CC2=CC(=O)CCC2(C)C2CCC3(C)C(CCC34CCC(=O)O4)C12", "molecular_weight": 416.57, "logp": 2.78, "original_indication": "heart failure"},
    {"name": "citalopram", "drugbank_id": "DB00215", "smiles": "Fc1ccc(C2(CCNCC2)OCc2cc3ccccc3s2)cc1", "molecular_weight": 324.39, "logp": 3.5, "original_indication": "depression"},
    {"name": "venlafaxine", "drugbank_id": "DB00285", "smiles": "COc1ccc(C(CN(C)C)C2(O)CCCCC2)cc1", "molecular_weight": 277.40, "logp": 3.2, "original_indication": "depression"},
    {"name": "carvedilol", "drugbank_id": "DB01136", "smiles": "COc1ccccc1OCCNCC(O)COc1cccc2[nH]c3ccccc3c12", "molecular_weight": 406.47, "logp": 4.19, "original_indication": "heart failure"},
    {"name": "methotrexate", "drugbank_id": "DB00563", "smiles": "CN(Cc1cnc2nc(N)nc(N)c2n1)c1ccc(C(=O)NC(CCC(O)=O)C(O)=O)cc1", "molecular_weight": 454.44, "logp": -1.85, "original_indication": "cancer"},
    {"name": "hydroxychloroquine", "drugbank_id": "DB01611", "smiles": "CCN(CCO)CCCC(C)Nc1ccnc2cc(Cl)ccc12", "molecular_weight": 335.87, "logp": 3.58, "original_indication": "malaria"},
    {"name": "chloroquine", "drugbank_id": "DB00608", "smiles": "CCN(CC)CCCC(C)Nc1ccnc2cc(Cl)ccc12", "molecular_weight": 319.87, "logp": 4.63, "original_indication": "malaria"},
    {"name": "ivermectin", "drugbank_id": "DB00602", "smiles": "CCC(C)C1OC(=O)C(C)C(OC2CC(OC)C(OC3CC(OC)C(O)C(C)O3)C(C)O2)C(C)CC(=O)CC=CC=CC=CC(CC2CC(=O)C(C(CC(C)C3OCC(C3O)C=CC(C)C(O)C(C)C1O)O2)O)OC", "molecular_weight": 875.10, "logp": 5.83, "original_indication": "parasitic infections"},
    {"name": "dexamethasone", "drugbank_id": "DB01234", "smiles": "CC1CC2C3CCC4=CC(=O)C=CC4(C)C3(F)C(O)CC2(C)C1(O)C(=O)CO", "molecular_weight": 392.46, "logp": 1.83, "original_indication": "inflammation"},
    {"name": "prednisolone", "drugbank_id": "DB00860", "smiles": "CC12CC(O)C3C(CCC4=CC(=O)C=CC34C)C1CCC2(O)C(=O)CO", "molecular_weight": 360.44, "logp": 1.62, "original_indication": "inflammation"},
    {"name": "methylprednisolone", "drugbank_id": "DB00959", "smiles": "CC1CC2C3CCC4=CC(=O)C=CC4(C)C3(F)C(O)CC2(C)C1(O)C(=O)CO", "molecular_weight": 374.47, "logp": 1.55, "original_indication": "inflammation"},
    {"name": "celecoxib", "drugbank_id": "DB00482", "smiles": "Cc1ccc(c(c1)c1cc(cf1)C(F)(F)F)S(=O)(=O)N", "molecular_weight": 381.37, "logp": 3.53, "original_indication": "arthritis"},
    {"name": "meloxicam", "drugbank_id": "DB00814", "smiles": "CN1C(=C(O)c2ccccc2S1(=O)=O)C(=O)Nc1ccccn1", "molecular_weight": 351.40, "logp": 3.43, "original_indication": "arthritis"},
    {"name": "colchicine", "drugbank_id": "DB01394", "smiles": "COc1cc2c(c(OC)c1OC)-c1ccc(OC)c(=O)cc1CC2NC(C)=O", "molecular_weight": 399.44, "logp": 1.3, "original_indication": "gout"},
    {"name": "allopurinol", "drugbank_id": "DB00437", "smiles": "O=c1[nH]cnc2[nH]ncc12", "molecular_weight": 136.11, "logp": -0.55, "original_indication": "gout"},
    {"name": "febuxostat", "drugbank_id": "DB04854", "smiles": "CC(C)COc1nc(c(s1)c1ccc(OCC)cc1)C#N", "molecular_weight": 316.37, "logp": 3.27, "original_indication": "gout"},
    {"name": "ribavirin", "drugbank_id": "DB00811", "smiles": "NC(=O)c1ncn(C2OC(CO)C(O)C2O)n1", "molecular_weight": 244.20, "logp": -2.6, "original_indication": "hepatitis C"},
    {"name": "sofosbuvir", "drugbank_id": "DB08934", "smiles": "CC(C)OC(=O)C(C)NP(=O)(OCC1OC(n2ccc(=O)[nH]c2=O)C(C1O)(C)F)Oc1ccccc1", "molecular_weight": 529.45, "logp": 1.62, "original_indication": "hepatitis C"},
    {"name": "oseltamivir", "drugbank_id": "DB00198", "smiles": "CCOC(=O)C1=CC(OC(CC)CC)C(NC(C)=O)C(N)C1", "molecular_weight": 312.40, "logp": 1.09, "original_indication": "influenza"},
    {"name": "acyclovir", "drugbank_id": "DB00787", "smiles": "Nc1nc2n(COCCO)cnc2c(=O)[nH]1", "molecular_weight": 225.20, "logp": -1.56, "original_indication": "herpes"},
    {"name": "valacyclovir", "drugbank_id": "DB00577", "smiles": "CC(C)C(N)C(=O)OCOCCN1C=Nc2c1nc(N)[nH]c2=O", "molecular_weight": 324.34, "logp": -0.86, "original_indication": "herpes"},
    {"name": "fluconazole", "drugbank_id": "DB00196", "smiles": "OC(Cn1cncn1)(Cn1cncn1)c1ccc(F)cc1F", "molecular_weight": 306.27, "logp": 0.5, "original_indication": "fungal infections"},
    {"name": "itraconazole", "drugbank_id": "DB01167", "smiles": "CCC(C)n1ncn(-c2ccc(N3CCN(c4ccc(OCC5COC(Cn6cncn6)(c6ccc(Cl)cc6Cl)O5)cc4)CC3)cc2)c1=O", "molecular_weight": 705.63, "logp": 5.66, "original_indication": "fungal infections"},
    {"name": "metronidazole", "drugbank_id": "DB00916", "smiles": "Cc1ncc([N+](=O)[O-])n1CCO", "molecular_weight": 171.15, "logp": -0.02, "original_indication": "anaerobic infections"},
    {"name": "nitrofurantoin", "drugbank_id": "DB00698", "smiles": "O=NN=Cc1ccc(o1)[N+](=O)[O-]", "molecular_weight": 238.16, "logp": -0.47, "original_indication": "urinary tract infections"},
    {"name": "phenytoin", "drugbank_id": "DB00252", "smiles": "O=C1NC(=O)C(c2ccccc2)(c2ccccc2)N1", "molecular_weight": 252.27, "logp": 2.47, "original_indication": "epilepsy"},
    {"name": "carbamazepine", "drugbank_id": "DB00564", "smiles": "NC(=O)N1c2ccccc2C=Cc2ccccc21", "molecular_weight": 236.27, "logp": 2.45, "original_indication": "epilepsy"},
    {"name": "valproic acid", "drugbank_id": "DB00313", "smiles": "CCCC(CCC)C(O)=O", "molecular_weight": 144.21, "logp": 2.75, "original_indication": "epilepsy"},
    {"name": "levetiracetam", "drugbank_id": "DB01202", "smiles": "CCC(C(=O)N)N1CCCC1=O", "molecular_weight": 170.21, "logp": -0.64, "original_indication": "epilepsy"},
    {"name": "lamotrigine", "drugbank_id": "DB00555", "smiles": "Nc1nnc(c(N)n1)c1cccc(Cl)c1Cl", "molecular_weight": 256.09, "logp": 2.57, "original_indication": "epilepsy"},
    {"name": "topiramate", "drugbank_id": "DB00273", "smiles": "CC1(C)OC2COC3(COS(N)(=O)=O)OC(C)(C)OC3C2O1", "molecular_weight": 339.36, "logp": -0.79, "original_indication": "epilepsy"},
    {"name": "donepezil", "drugbank_id": "DB00843", "smiles": "COc1cc2CC(CC(=O)c2c(OC)c1)CC1CCN(Cc2ccccc2)CC1", "molecular_weight": 379.49, "logp": 4.28, "original_indication": "Alzheimer disease"},
    {"name": "memantine", "drugbank_id": "DB01043", "smiles": "CC12CC3CC(N)(C1)CC(C)(C3)C2", "molecular_weight": 179.30, "logp": 3.28, "original_indication": "Alzheimer disease"},
    {"name": "levodopa", "drugbank_id": "DB01235", "smiles": "NC(Cc1ccc(O)c(O)c1)C(O)=O", "molecular_weight": 197.19, "logp": -2.74, "original_indication": "Parkinson disease"},
    {"name": "carbidopa", "drugbank_id": "DB00190", "smiles": "CC(Cc1ccc(O)c(O)c1)(NN)C(O)=O", "molecular_weight": 226.23, "logp": -1.2, "original_indication": "Parkinson disease"},
    {"name": "entacapone", "drugbank_id": "DB00494", "smiles": "CCN(CC)C(=O)/C(=C/c1cc(O)c(O)c([N+](=O)[O-])c1)C#N", "molecular_weight": 305.29, "logp": 1.49, "original_indication": "Parkinson disease"},
    {"name": "sumatriptan", "drugbank_id": "DB00669", "smiles": "CNS(=O)(=O)Cc1ccc2[nH]cc(CCN(C)C)c2c1", "molecular_weight": 295.40, "logp": 0.93, "original_indication": "migraine"},
    {"name": "rizatriptan", "drugbank_id": "DB00953", "smiles": "CN(C)CCc1c[nH]c2ccc(CN3C=CN=C3)cc12", "molecular_weight": 269.34, "logp": 1.3, "original_indication": "migraine"},
    {"name": "ondansetron", "drugbank_id": "DB00904", "smiles": "Cc1ncc2CC(=O)N(CC3CCc4ccccc43)c2n1", "molecular_weight": 293.37, "logp": 2.4, "original_indication": "nausea"},
    {"name": "promethazine", "drugbank_id": "DB01069", "smiles": "CC(CN1c2ccccc2Sc2ccccc21)N(C)C", "molecular_weight": 284.42, "logp": 4.81, "original_indication": "allergies"},
    {"name": "diphenhydramine", "drugbank_id": "DB01075", "smiles": "CN(C)CCOC(c1ccccc1)c1ccccc1", "molecular_weight": 255.36, "logp": 3.27, "original_indication": "allergies"},
    {"name": "fexofenadine", "drugbank_id": "DB00950", "smiles": "CC(C)(C(O)=O)c1ccc(cc1)C(O)CCCN1CCC(CC1)C(O)(c1ccccc1)c1ccccc1", "molecular_weight": 501.66, "logp": 2.8, "original_indication": "allergies"},
    {"name": "montelukast", "drugbank_id": "DB00471", "smiles": "CC(C)(O)c1ccccc1CCSc1cc2c(cc1Cl)C(C(=O)O)=CC2c1cccc(/C=C/c2ccc3ccc(Cl)cc3n2)c1", "molecular_weight": 586.18, "logp": 7.9, "original_indication": "asthma"},
    {"name": "theophylline", "drugbank_id": "DB00277", "smiles": "Cn1c2c(c(=O)n(C)c1=O)[nH]cn2", "molecular_weight": 180.16, "logp": -0.02, "original_indication": "asthma"},
    {"name": "budesonide", "drugbank_id": "DB01222", "smiles": "CCCC1OC2CC3C4CCC5=CC(=O)C=CC5(C)C4C(O)CC3(C)C2(O1)C(=O)CO", "molecular_weight": 430.53, "logp": 2.42, "original_indication": "asthma"},
    {"name": "pioglitazone", "drugbank_id": "DB01132", "smiles": "CCc1ccc(CCOc2ccc(CC3SC(=O)NC3=O)cc2)nc1", "molecular_weight": 356.44, "logp": 3.5, "original_indication": "type 2 diabetes"},
    {"name": "glipizide", "drugbank_id": "DB01067", "smiles": "Cc1cnc(cn1)C(=O)NS(=O)(=O)c1ccc(CCNC(=O)N2CCCCC2)cc1", "molecular_weight": 445.53, "logp": 1.91, "original_indication": "type 2 diabetes"},
    {"name": "empagliflozin", "drugbank_id": "DB09038", "smiles": "OCC1OC(c2ccc(Cl)c(Cc3ccc4OCC(O4)c4ccccc4)c2)C(O)C(O)C1O", "molecular_weight": 450.91, "logp": 1.8, "original_indication": "type 2 diabetes"},
    {"name": "canagliflozin", "drugbank_id": "DB08907", "smiles": "Cc1ccc(cc1Cc1ccc(s1)c1ccc(F)cc1)C1OC(CO)C(O)C(O)C1O", "molecular_weight": 444.52, "logp": 3.8, "original_indication": "type 2 diabetes"},
    {"name": "liraglutide", "drugbank_id": "DB06655", "smiles": "CCCCCCCCCCCCCCCC(=O)N", "molecular_weight": 3751.20, "logp": 0.5, "original_indication": "type 2 diabetes"},
    {"name": "captopril", "drugbank_id": "DB01197", "smiles": "CC(CS)C(=O)N1CCCC1C(O)=O", "molecular_weight": 217.28, "logp": 0.34, "original_indication": "hypertension"},
    {"name": "enalapril", "drugbank_id": "DB00584", "smiles": "CCOC(=O)C(CCc1ccccc1)NC(C)C(=O)N1CCCC1C(O)=O", "molecular_weight": 376.45, "logp": 0.07, "original_indication": "hypertension"},
    {"name": "valsartan", "drugbank_id": "DB00177", "smiles": "CCCCC(=O)N(Cc1ccc(c2ccccc2c2nn[nH]n2)cc1)C(C(C)C)C(O)=O", "molecular_weight": 435.52, "logp": 4.0, "original_indication": "hypertension"},
    {"name": "diltiazem", "drugbank_id": "DB00343", "smiles": "COc1ccc(C2Sc3ccccc3N(CCN(C)C)C(=O)C2OC(C)=O)cc1", "molecular_weight": 414.52, "logp": 2.7, "original_indication": "hypertension"},
    {"name": "nifedipine", "drugbank_id": "DB01115", "smiles": "COC(=O)C1=C(C)NC(C)=C(C(=O)OC)C1c1ccccc1[N+](=O)[O-]", "molecular_weight": 346.33, "logp": 2.2, "original_indication": "hypertension"},
    {"name": "propranolol", "drugbank_id": "DB00571", "smiles": "CC(C)NCC(O)COc1cccc2ccccc12", "molecular_weight": 259.34, "logp": 3.48, "original_indication": "hypertension"},
    {"name": "atenolol", "drugbank_id": "DB00335", "smiles": "CC(C)NCC(O)COc1ccc(CC(N)=O)cc1", "molecular_weight": 266.34, "logp": 0.16, "original_indication": "hypertension"},
]


def download_drugbank_open(output_dir: Optional[Path] = None) -> Optional[Path]:
    """Download DrugBank open-data SDF file.

    Args:
        output_dir: Directory to save the file. Defaults to RAW_DIR.

    Returns:
        Path to the downloaded SDF file, or None on failure.
    """
    dest = (output_dir or RAW_DIR) / "drugbank_open_structures.sdf"
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        logger.info("DrugBank SDF already exists at %s", dest)
        return dest

    logger.info("Downloading DrugBank open structures...")
    try:
        resp = requests.get(_DRUGBANK_OPEN_URL, timeout=60, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("Downloaded DrugBank SDF to %s", dest)
        return dest
    except requests.RequestException as e:
        logger.warning("Failed to download DrugBank SDF: %s", e)
        return None


def parse_sdf(filepath: Path) -> list[dict]:
    """Parse an SDF file and extract drug records.

    Args:
        filepath: Path to the SDF file.

    Returns:
        List of dicts with keys: name, smiles, molecular_weight, logp, etc.
    """
    records = []
    if not filepath.exists():
        logger.warning("SDF file not found: %s", filepath)
        return records

    current_block: list[str] = []
    with open(filepath) as f:
        for line in f:
            if line.strip() == "$$$$":
                record = _parse_sdf_block(current_block)
                if record:
                    records.append(record)
                current_block = []
            else:
                current_block.append(line)

    # Handle last block if file doesn't end with $$$$
    if current_block:
        record = _parse_sdf_block(current_block)
        if record:
            records.append(record)

    logger.info("Parsed %d drug records from %s", len(records), filepath)
    return records


def _parse_sdf_block(lines: list[str]) -> Optional[dict]:
    """Parse a single SDF molecule block into a drug record."""
    if not lines:
        return None

    name = lines[0].strip() if lines else "unknown"

    # Extract properties from SDF data fields
    props: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("> <"):
            key = line.strip("> <").rstrip(">").strip()
            if i + 1 < len(lines):
                props[key] = lines[i + 1].strip()
            i += 2
        else:
            i += 1

    return {
        "name": props.get("GENERIC_NAME", name).lower(),
        "drugbank_id": props.get("DATABASE_ID", ""),
        "smiles": props.get("SMILES", ""),
        "molecular_weight": float(props["MOLECULAR_WEIGHT"]) if "MOLECULAR_WEIGHT" in props else 0.0,
        "logp": float(props["LOGP"]) if "LOGP" in props else 0.0,
        "original_indication": props.get("INDICATION", "unknown"),
    }


def load_curated_drugs() -> list[dict]:
    """Return the curated list of 100 FDA-approved drugs.

    This fallback is used when DrugBank download is unavailable.
    """
    return CURATED_DRUGS.copy()


def store_drugs(drugs: list[dict], db_path: Optional[Path] = None) -> int:
    """Insert drug records into the database.

    Skips duplicates based on drug_id (name-based).

    Args:
        drugs: List of drug dicts.
        db_path: Optional database path override.

    Returns:
        Number of drugs inserted.
    """
    conn = get_connection(db_path)
    inserted = 0
    try:
        for drug in drugs:
            drug_id = drug["name"].lower().replace(" ", "_")
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO drugs
                       (drug_id, name, drugbank_id, original_indication,
                        smiles, molecular_weight, logp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        drug_id,
                        drug["name"],
                        drug.get("drugbank_id", ""),
                        drug.get("original_indication", "unknown"),
                        drug.get("smiles", ""),
                        drug.get("molecular_weight", 0.0),
                        drug.get("logp", 0.0),
                    ),
                )
                if conn.total_changes:
                    inserted += 1
            except Exception as e:
                logger.warning("Failed to insert drug %s: %s", drug["name"], e)
        conn.commit()
        logger.info("Inserted %d drugs into database", inserted)
    finally:
        conn.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()

    # Try DrugBank download first, fall back to curated list
    sdf_path = download_drugbank_open()
    if sdf_path and sdf_path.exists():
        drugs = parse_sdf(sdf_path)
        if drugs:
            store_drugs(drugs)
            print(f"Stored {len(drugs)} drugs from DrugBank SDF")
        else:
            print("SDF parsing returned no drugs, using curated list")
            drugs = load_curated_drugs()
            store_drugs(drugs)
            print(f"Stored {len(drugs)} curated drugs")
    else:
        print("DrugBank download unavailable, using curated list")
        drugs = load_curated_drugs()
        store_drugs(drugs)
        print(f"Stored {len(drugs)} curated drugs")
