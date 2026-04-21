# Backcalculations

Excel-driven sensitivity analysis workflow for geotechnical slope stability backcalculations using D-Stability (Deltares).

## What this project does

Given a set of baseline slope stability models (STIX files), this project lets you define sensitivity runs in Excel â€” changing soil parameters, strength models, and pre-overburden pressure (POP) â€” and automatically:

1. Creates a modified copy of the baseline STIX file for each run
2. Runs D-Stability in batch via its console interface
3. Writes the Factor of Safety (FoS) results back into the same Excel file

The goal is to efficiently explore which parameter combinations best reproduce observed failure or target safety factors during backcalculation.

---

## Project structure

```
backcalculations/
+-- baseline_models/                # Baseline STIX files + their run Excel files
|   +-- bergambacht.stix
|   +-- bergambacht_runs.xlsx       # Run definitions for bergambacht
|   +-- eemdijk.stix
|   +-- eemdijk_runs.xlsx
|   +-- ijkdijk.stix
|   +-- ijkdijk_runs.xlsx
|
+-- results/                        # Auto-created output folder
|   +-- <model_name>/
|       +-- <run_id>/
|           +-- <model>_<run_id>.stix   # Modified STIX with D-Stability results
|
+-- su_tables/                      # Optional: SuTable JSON files for tabulated strength
|
+-- exploration/                    # Scripts to inspect STIX files (read-only, no edits)
|   +-- explore_stix.py             # Full structure overview of any STIX file
|   +-- list_soils.py               # All soils with strength model and parameters
|   +-- inspect_states.py          # All state points with POP values
|
+-- source/
|   +-- stix_io.py                  # Read/write STIX files, extract soils/layers/states
|   +-- stix_modifier.py            # Legacy soil modification functions (old system)
|   +-- utils.py                    # Legacy utilities (old system)
|   +-- constants/
|   |   +-- constants.py            # D-Stability binary path, enums, dataclasses
|   |   +-- safety_format.py        # Safety format definitions
|   +-- __init__.py
|
+-- generate_template.py            # Generate Excel run templates from baseline STIX
+-- run_model.py                    # Main run engine (reads Excel, runs D-Stability)
|
+-- run_attempt.py                  # Legacy runner (JSON-config based, kept for reference)
+-- compare_attempts.py             # Legacy comparison tool
+-- attempts_config/                # Legacy JSON configs
+-- attempts_tracking.xlsx          # Legacy tracking table
```

---

## Prerequisites

- **Python 3.11+** with a virtual environment at `.venv/`
- **D-Stability 2025.01** installed (Deltares). The binary path is set in `source/constants/constants.py`:
  ```python
  DSTABILITY_BIN_FOLDER = r"C:\Program Files\Deltares\D-GEO Suite\D-Stability 2025.01\bin"
  ```
  Update this path if your installation is different.
- Required Python packages: `pandas`, `openpyxl`, `numpy`

To activate the environment:
```
.venv\Scripts\activate
```

---

## Quick start: running a sensitivity analysis

### Step 1 â€” Generate the Excel template

Run this once per model to create the Excel run file:

```
python generate_template.py
```

This scans all `.stix` files in `baseline_models/` and creates a `<model>_runs.xlsx` next to each one. To regenerate a specific model only:

```
python generate_template.py baseline_models/bergambacht.stix
```

The Excel file contains four sheets:
- **runs** â€” one row per run; defines which calculation methods to execute
- **materials** â€” one row per (run, soil); defines parameter overrides
- **su_tables** â€” optional registry of tabulated strength (SuTable) JSON files
- **results** â€” automatically filled by `run_model.py` with FoS values

### Step 2 â€” Define your runs in Excel

Open `baseline_models/bergambacht_runs.xlsx`.

#### `runs` sheet

Add a new row for each run you want to execute:

| run_id | description | notes | run_upliftvan |
|--------|-------------|-------|---------------|
| baseline | Original model | | TRUE |
| run_1 | Increase clay S | Test S=0.4 | TRUE |
| run_2 | Lower POP | POP=20 everywhere | TRUE |

- `run_id` must be unique and contain no spaces (use underscores)
- `run_upliftvan`, `run_bishop`, `run_spencer` â€” set to `TRUE` for each method you want to run
- The baseline row is pre-filled when the template is generated; you can run it as-is to verify the setup

#### `materials` sheet

For each run that modifies parameters, add a row per soil you want to change. Leave cells **blank** for parameters you do not want to touch â€” they will keep the baseline value.

| run_id | material_code | active_model | gamma_dry | gamma_wet | Su_S | Su_m | MC_phi | MC_c | MC_psi | su_table_key | Layers | POP |
|--------|---------------|--------------|-----------|-----------|------|------|--------|------|--------|--------------|--------|-----|
| baseline | GKZO | Su | 15.0 | 15.0 | 0.35 | 0.8 | | | | | SP 1, SP 2 | 25.0, 18.0 |
| run_1 | GKZO | | | | 0.4 | | | | | | | |
| run_2 | GKZO | | | | | | | | | | SP 1, SP 2 | 20.0, 20.0 |

Column reference:

| Column | Meaning |
|--------|---------|
| `run_id` | Must match a `run_id` in the runs sheet |
| `material_code` | Soil code exactly as it appears in the STIX file |
| `active_model` | Force a specific strength model: `Su`, `MohrCoulombAdvanced`, `MohrCoulombClassic`, `SuTable` |
| `gamma_dry` | Unit weight above phreatic level (kN/mÂ³) |
| `gamma_wet` | Unit weight below phreatic level (kN/mÂ³) |
| `Su_S` | SHANSEP strength ratio S |
| `Su_m` | SHANSEP exponent m |
| `MC_phi` | Mohr-Coulomb friction angle (Â°) |
| `MC_c` | Mohr-Coulomb cohesion (kPa) |
| `MC_psi` | Mohr-Coulomb dilatancy angle (Â°) |
| `su_table_key` | Name of a JSON file in `su_tables/` (without `.json`) |
| `Layers` | Comma-separated state point labels to change POP for |
| `POP` | Comma-separated POP values (kPa) matching the order of `Layers` |

To find the correct soil codes and state point labels for your model, use the exploration scripts (see below).

### Step 3 â€” Run the model

Edit the `STIX_FILE` constant at the top of `run_model.py` to point at the model you want:

```python
STIX_FILE = "baseline_models/bergambacht.stix"
```

Then run:

```
python run_model.py
```

For each run defined in the Excel file, the engine will:
1. Load the baseline STIX fresh
2. Apply the parameter overrides from the `materials` sheet
3. Save the modified STIX to `results/<model>/<run_id>/<model>_<run_id>.stix`
4. Run D-Stability Console for each enabled calculation method
5. Read the FoS from the result file
6. Append a row to the `results` sheet in the Excel file

### Step 4 â€” Review results

Open the Excel file and go to the `results` sheet. It will contain one row per completed run with FoS values per method:

| run_id | model_name | timestamp | FoS_upliftvan |
|--------|------------|-----------|---------------|
| baseline | bergambacht | 2026-04-21 10:00:00 | 1.23 |
| run_1 | bergambacht | 2026-04-21 10:01:30 | 1.31 |

The modified STIX files in `results/` can be opened directly in D-Stability to inspect the calculated slip surface.

---

## Exploration scripts

These read-only scripts help you understand the contents of any STIX file. Run them from the project root:

```
python exploration/list_soils.py baseline_models/bergambacht.stix
```
Prints all soils with their strength model and baseline parameter values. Use this to find the correct `material_code` values for the materials sheet.

```
python exploration/inspect_states.py baseline_models/bergambacht.stix
```
Prints all state points with their label, associated soil code, and POP value. Use this to find the correct label names for the `Layers` column in the materials sheet.

```
python exploration/explore_stix.py baseline_models/bergambacht.stix
```
Prints the full internal structure: all keys, scenarios, geometry, soillayers, waternets, state sets, calculation settings, and soils. Use this when first encountering an unfamiliar STIX file.

---

## Using SuTable strength models

If you want to assign a tabulated strength profile (SuTable) to a soil:

1. Create a JSON file in `su_tables/` with the table points:
   ```json
   [
     {"EffectiveStress": 0.0, "Su": 5.0},
     {"EffectiveStress": 50.0, "Su": 22.5},
     {"EffectiveStress": 200.0, "Su": 75.0}
   ]
   ```
   Save it as e.g. `su_tables/GKZO_case1.json`.

2. In the `materials` sheet, fill the `su_table_key` column with the filename without extension (`GKZO_case1`) and set `active_model` to `SuTable`.

---

## D-Stability binary path

If D-Stability is installed in a different location, update the path in `source/constants/constants.py`:

```python
DSTABILITY_BIN_FOLDER = r"C:\Program Files\Deltares\D-GEO Suite\D-Stability 2025.01\bin"
```

---

## Troubleshooting

**`ERROR: Excel run file not found`**
Run `python generate_template.py` first to create the Excel file for your model.

**`WARNING: material 'XYZ' not found in STIX`**
The `material_code` in the materials sheet does not match any soil code in the STIX. Run `python exploration/list_soils.py <your_model>.stix` to see exact codes.

**`WARNING: SuTable file not found`**
The `su_table_key` value in the materials sheet does not match any file in `su_tables/`. Check the filename.

**`ModuleNotFoundError`**
Make sure you are running Python from the `.venv` environment and from the project root directory.

**D-Stability does not produce results**
Check that the STIX file was saved correctly before running. Open the modified STIX in `results/` in D-Stability manually to debug.

---

*This README was written with the assistance of GitHub Copilot.*

