"""ColabFold pipeline for batch structure prediction.

ColabFold uses AlphaFold2 with MMseqs2 for fast MSA generation
and structure prediction. It requires a GPU, so this module
generates a pre-filled Colab notebook and parses output results.

Usage:
    1. Call generate_colabfold_notebook() to create a .ipynb file
    2. Upload the notebook to Google Colab (colab.research.google.com)
    3. Run all cells (GPU runtime required)
    4. Download the results directory
    5. Call parse_colabfold_output() to extract the best structure

ColabFold typically produces higher-quality structures than ESMFold
for multi-domain proteins or targets requiring evolutionary information.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src.utils.config import STRUCTURES_DIR

logger = logging.getLogger(__name__)


def generate_colabfold_notebook(
    sequence: str,
    output_dir: Optional[Path] = None,
    job_name: str = "genetropica_prediction",
    num_models: int = 5,
    num_recycles: int = 3,
) -> Path:
    """Create a pre-filled ColabFold notebook for structure prediction.

    Generates a Jupyter notebook (.ipynb) that can be uploaded to
    Google Colab and run with a GPU runtime to predict protein
    structures using AlphaFold2.

    Args:
        sequence: Amino acid sequence (single-letter code).
        output_dir: Directory to save the notebook. Defaults to STRUCTURES_DIR.
        job_name: Name for the ColabFold job.
        num_models: Number of AlphaFold2 models to run (1-5).
        num_recycles: Number of recycling iterations.

    Returns:
        Path to the generated .ipynb file.
    """
    dest_dir = output_dir or STRUCTURES_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    notebook_path = dest_dir / f"ColabFold_{job_name}.ipynb"

    seq_clean = sequence.strip().upper().replace(" ", "").replace("\n", "")

    # Build notebook cells
    cells = [
        _markdown_cell(
            f"# ColabFold Structure Prediction: {job_name}\n\n"
            f"Sequence length: {len(seq_clean)} residues\n\n"
            "**Instructions:**\n"
            "1. Set runtime to GPU: Runtime > Change runtime type > T4 GPU\n"
            "2. Run all cells: Runtime > Run all\n"
            "3. Download the results folder when complete"
        ),
        _code_cell(
            "# Install ColabFold\n"
            "!pip install -q colabfold[alphafold2]@git+https://github.com/"
            "sokrypton/ColabFold 2>/dev/null\n"
            "!pip install -q jax[cuda12] 2>/dev/null"
        ),
        _code_cell(
            "# Define sequence and parameters\n"
            f'SEQUENCE = "{seq_clean}"\n'
            f'JOB_NAME = "{job_name}"\n'
            f"NUM_MODELS = {num_models}\n"
            f"NUM_RECYCLES = {num_recycles}\n"
            "\n"
            "import os\n"
            "os.makedirs(JOB_NAME, exist_ok=True)\n"
            "\n"
            "# Write query FASTA\n"
            'with open(f"{JOB_NAME}/query.fasta", "w") as f:\n'
            '    f.write(f">query\\n{SEQUENCE}\\n")\n'
            'print(f"Sequence: {len(SEQUENCE)} residues")'
        ),
        _code_cell(
            "# Run ColabFold prediction\n"
            "from colabfold.batch import run as colabfold_run\n"
            "from colabfold.download import default_data_dir\n"
            "\n"
            "colabfold_run(\n"
            f'    queries=[(JOB_NAME, SEQUENCE, None)],\n'
            f'    result_dir=JOB_NAME,\n'
            f'    num_models=NUM_MODELS,\n'
            f'    num_recycles=NUM_RECYCLES,\n'
            '    model_type="alphafold2_ptm",\n'
            '    use_gpu=True,\n'
            ")"
        ),
        _code_cell(
            "# Download results\n"
            "import shutil\n"
            f'shutil.make_archive(JOB_NAME, "zip", JOB_NAME)\n'
            "from google.colab import files\n"
            f'files.download(f"{{JOB_NAME}}.zip")\n'
            'print("Download complete!")'
        ),
    ]

    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
            "accelerator": "GPU",
        },
        "cells": cells,
    }

    with open(notebook_path, "w") as f:
        json.dump(notebook, f, indent=2)

    logger.info("Generated ColabFold notebook: %s", notebook_path.name)
    return notebook_path


def _markdown_cell(source: str) -> dict:
    """Create a Jupyter markdown cell."""
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [source],
    }


def _code_cell(source: str) -> dict:
    """Create a Jupyter code cell."""
    return {
        "cell_type": "code",
        "metadata": {},
        "source": [source],
        "outputs": [],
        "execution_count": None,
    }


def parse_colabfold_output(
    output_dir: Path,
    job_name: str = "genetropica_prediction",
) -> Optional[Path]:
    """Parse ColabFold results and extract the best-ranked structure.

    ColabFold outputs multiple ranked PDB files. This function
    finds the rank_001 (best) model.

    Args:
        output_dir: Directory containing ColabFold output files.
        job_name: Job name used during prediction.

    Returns:
        Path to the best-ranked PDB file, or None if not found.
    """
    if not output_dir.exists():
        logger.warning("ColabFold output directory not found: %s", output_dir)
        return None

    # ColabFold names: {job_name}_unrelaxed_rank_001_*.pdb
    candidates = sorted(output_dir.glob(f"*rank_001*.pdb"))

    if not candidates:
        # Try alternative naming
        candidates = sorted(output_dir.glob("*rank_1*.pdb"))

    if not candidates:
        # Check for any PDB output
        candidates = sorted(output_dir.glob("*.pdb"))

    if candidates:
        best = candidates[0]
        logger.info("Best ColabFold model: %s", best.name)
        return best

    logger.warning("No PDB files found in ColabFold output: %s", output_dir)
    return None


def get_colabfold_scores(output_dir: Path) -> dict[str, float]:
    """Extract pLDDT and pTM scores from ColabFold JSON output.

    Args:
        output_dir: Directory containing ColabFold results.

    Returns:
        Dict with 'plddt' and 'ptm' scores for the best model.
    """
    scores = {"plddt": 0.0, "ptm": 0.0}

    json_files = sorted(output_dir.glob("*scores_rank_001*.json"))
    if not json_files:
        json_files = sorted(output_dir.glob("*scores*.json"))

    if json_files:
        try:
            with open(json_files[0]) as f:
                data = json.load(f)
            scores["plddt"] = data.get("plddt", 0.0)
            scores["ptm"] = data.get("ptm", 0.0)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse ColabFold scores: %s", e)

    return scores
