# PyMOL Installation Notes

## Status

PyMOL is **not currently functional** on this system. The open-source pip package installs but fails at runtime due to missing native shared libraries.

## What Was Tried

### 1. pip install (failed)

```bash
pip3 install pymol-open-source
```

Package `pymol-open-source 3.2.0a0` installed successfully, but importing fails:

```
ImportError: dlopen pymol/_cmd.cpython-313-darwin.so
  Library not loaded: @rpath/libGLEW.2.1.dylib
```

### 2. Install GLEW via Homebrew (partially fixed)

```bash
brew install glew
```

Homebrew installed `libGLEW.2.3.dylib`, but the PyMOL binary was compiled against `libGLEW.2.1.dylib`. Creating a symlink resolved this:

```bash
ln -sf /opt/homebrew/lib/libGLEW.2.3.dylib /opt/homebrew/lib/libGLEW.2.1.dylib
```

However, a second missing library appeared:

```
Library not loaded: @rpath/libnetcdf.22.dylib
```

### 3. Root Cause

The `pymol-open-source` pip wheel was compiled in a conda/mamba environment (`/Users/Martin/.local/share/mamba/envs/pymol_313/`). It has hardcoded `@rpath` references to many native libraries (GLEW, netcdf, and likely more) that don't exist in the current Anaconda environment.

## Recommended Fix (When Needed)

### Option A: Conda install (most reliable)

```bash
conda install -c conda-forge pymol-open-source
```

This pulls all native dependencies (GLEW, netcdf, freetype, libpng, etc.) into the conda environment automatically.

### Option B: Dedicated conda environment

```bash
conda create -n pymol_env python=3.13 pymol-open-source -c conda-forge
conda activate pymol_env
```

This avoids any risk of disrupting the main project environment.

### Option C: Homebrew cask (GUI version)

```bash
brew install --cask pymol
```

Installs the full PyMOL application. Useful for manual visualization but not scriptable from Python.

## Current Workaround

GeneTropica Phase 13 uses **py3Dmol** (already working in the project) for interactive 3D conservation visualization in the Streamlit dashboard. A `.pml` PyMOL script is also generated at `data/conservation/consurf/conservation_view.pml` so the visualization can be reproduced in PyMOL once it is installed.

## Environment Details

- **OS**: macOS (Apple Silicon / arm64)
- **Python**: 3.13.5 (Anaconda)
- **Date**: 2026-02-28
