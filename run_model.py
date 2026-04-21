"""
Run engine: reads the Excel run sheet, applies parameter changes to the
baseline STIX file, runs D-Stability, and writes FoS back to the results sheet.

Usage:
    python run_model.py baseline_models/bergambacht_reviewed.stix

This reads:
    baseline_models/bergambacht_reviewed_runs.xlsx

And writes modified STIX files to:
    results/bergambacht_reviewed/<run_id>/
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).parent))
from source.stix_io import (
    get_calc_settings_map,
    get_soils,
    get_states,
    get_soillayers,
    read_stix,
    write_stix,
)
from source.constants.constants import DSTABILITY_BIN_FOLDER

# ============================================================================
# CONFIGURATION
# ============================================================================
STIX_FILE = "baseline_models/bergambacht_reviewed.stix"
# ============================================================================

ANALYSIS_TYPE_TO_RESULT_KEY = {
    "BishopBruteForce": "results/bishopbruteforce/bishopbruteforceresult",
    "UpliftVanParticleSwarm": "results/upliftvanparticleswarm/upliftvanparticleswarmresult",
    "SpencerGenetic": "results/spencergenetic/spencergeneticresult",
}

METHOD_LABEL_TO_ANALYSIS_TYPE = {
    "bishop": "BishopBruteForce",
    "upliftvan": "UpliftVanParticleSwarm",
    "spencer": "SpencerGenetic",
}


# ---------------------------------------------------------------------------
# Soil modification
# ---------------------------------------------------------------------------


def apply_material_changes(data: dict, material_rows: pd.DataFrame) -> dict:
    """Apply parameter overrides from the materials sheet to loaded STIX data."""
    soils = get_soils(data)
    soil_by_code = {s["Code"]: s for s in soils}

    for _, row in material_rows.iterrows():
        code = row["material_code"]
        if code not in soil_by_code:
            print(f"  WARNING: material '{code}' not found in STIX, skipping.")
            continue

        soil = soil_by_code[code]
        active_model = row.get("active_model")

        # Unit weights
        if pd.notna(row.get("gamma_dry")):
            soil["VolumetricWeightAbovePhreaticLevel"] = float(row["gamma_dry"])
        if pd.notna(row.get("gamma_wet")):
            soil["VolumetricWeightBelowPhreaticLevel"] = float(row["gamma_wet"])

        # Switch model if specified
        if pd.notna(active_model) and active_model:
            soil["ShearStrengthModelTypeAbovePhreaticLevel"] = active_model
            soil["ShearStrengthModelTypeBelowPhreaticLevel"] = active_model

        # Su / SHANSEP
        if pd.notna(row.get("Su_S")) or pd.notna(row.get("Su_m")):
            m = soil.setdefault("SuShearStrengthModel", {})
            if pd.notna(row.get("Su_S")):
                m["ShearStrengthRatio"] = float(row["Su_S"])
            if pd.notna(row.get("Su_m")):
                m["StrengthIncreaseExponent"] = float(row["Su_m"])

        # MohrCoulomb
        for mc_key, model_key in [
            ("MohrCoulombAdvanced", "MohrCoulombAdvancedShearStrengthModel"),
            ("MohrCoulombClassic", "MohrCoulombClassicShearStrengthModel"),
        ]:
            if pd.notna(row.get("MC_phi")) or pd.notna(row.get("MC_c")):
                m = soil.setdefault(model_key, {})
                if pd.notna(row.get("MC_phi")):
                    m["FrictionAngle"] = float(row["MC_phi"])
                if pd.notna(row.get("MC_c")):
                    m["Cohesion"] = float(row["MC_c"])
                if pd.notna(row.get("MC_psi")):
                    m["Dilatancy"] = float(row["MC_psi"])

        # SuTable from JSON file
        su_table_key = row.get("su_table_key")
        if pd.notna(su_table_key) and su_table_key:
            _apply_su_table_from_key(soil, su_table_key)

        # POP changes via Layers / POP columns
        layers_str = row.get("Layers", "")
        pop_str = row.get("POP", "")
        if pd.notna(layers_str) and pd.notna(pop_str) and layers_str and pop_str:
            labels = [s.strip() for s in str(layers_str).split(",")]
            pop_vals = [float(s.strip()) for s in str(pop_str).split(",")]
            _apply_pop_changes(data, code, dict(zip(labels, pop_vals)))

    return data


def _apply_su_table_from_key(soil: dict, su_table_key: str) -> None:
    """Load SuTable points from a JSON file in the su_tables/ folder."""
    import json

    project_root = Path(__file__).parent
    table_path = project_root / "su_tables" / f"{su_table_key}.json"
    if not table_path.exists():
        print(f"  WARNING: SuTable file not found: {table_path}")
        return
    with open(table_path) as f:
        points = json.load(f)
    soil["ShearStrengthModelTypeAbovePhreaticLevel"] = "SuTable"
    soil["ShearStrengthModelTypeBelowPhreaticLevel"] = "SuTable"
    soil.setdefault("SuTable", {})["SuTablePoints"] = points


def _apply_pop_changes(data: dict, soil_code: str, label_to_pop: dict) -> None:
    """Apply POP changes to state points by label for the given soil code."""
    soils = get_soils(data)
    soil_id_by_code = {s["Code"]: s["Id"] for s in soils}
    soil_id = soil_id_by_code.get(soil_code)
    if not soil_id:
        return

    all_layers = get_soillayers(data)
    all_states = get_states(data)

    layer_to_soil_id = {}
    for layers in all_layers.values():
        for layer in layers:
            layer_to_soil_id[layer["LayerId"]] = layer["SoilId"]

    for state_points in all_states.values():
        for sp in state_points:
            layer_id = sp.get("LayerId")
            if layer_to_soil_id.get(layer_id) != soil_id:
                continue
            label = sp.get("Label", "")
            if label in label_to_pop:
                sp["Stress"]["Pop"] = label_to_pop[label]


# ---------------------------------------------------------------------------
# D-Stability runner
# ---------------------------------------------------------------------------


def run_dstability(stix_path: Path, analysis_types: list) -> dict:
    """
    Run D-Stability for each requested analysis type and return FoS per type.
    """
    exe = str(Path(DSTABILITY_BIN_FOLDER) / "D-Stability Console.exe")
    calc_map = get_calc_settings_map(read_stix(stix_path))

    fos_results = {}
    for analysis_type in analysis_types:
        if analysis_type not in calc_map:
            print(
                f"  WARNING: {analysis_type} not found in STIX calc settings, skipping."
            )
            continue

        # D-Stability Console uses 1-based index of calculation in file
        calc_keys = sorted(
            k for k in read_stix(stix_path) if k.startswith("calculationsettings/")
        )
        calc_index = calc_keys.index(calc_map[analysis_type]) + 1

        print(f"  Running {analysis_type} (calc index {calc_index})...")
        try:
            subprocess.run(
                [exe, str(stix_path), "1", str(calc_index)],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"  ERROR running D-Stability: {e}")
            fos_results[analysis_type] = None
            continue

        # Read result back
        result_data = read_stix(stix_path)
        result_key = ANALYSIS_TYPE_TO_RESULT_KEY.get(analysis_type)
        try:
            fos_results[analysis_type] = result_data[result_key]["FactorOfSafety"]
        except (KeyError, TypeError):
            fos_results[analysis_type] = None

    return fos_results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    project_root = Path(__file__).parent
    stix_path = project_root / STIX_FILE
    excel_path = stix_path.with_name(stix_path.stem + "_runs.xlsx")
    output_root = project_root / "results" / stix_path.stem

    if not stix_path.exists():
        print(f"ERROR: STIX file not found: {stix_path}")
        sys.exit(1)
    if not excel_path.exists():
        print(f"ERROR: Excel run file not found: {excel_path}")
        print(f"Run generate_template.py first.")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"  Model: {stix_path.name}")
    print(f"  Excel: {excel_path.name}")
    print(f"{'='*70}\n")

    # Read Excel
    df_runs = pd.read_excel(excel_path, sheet_name="runs")
    df_materials = pd.read_excel(excel_path, sheet_name="materials")
    wb = load_workbook(excel_path)
    ws_results = wb["results"]

    # Determine calc method columns in runs sheet
    method_cols = [c for c in df_runs.columns if c.startswith("run_")]
    output_root.mkdir(parents=True, exist_ok=True)

    all_results = []

    for _, run_row in df_runs.iterrows():
        run_id = run_row["run_id"]
        description = run_row.get("description", "")
        print(f"\n--- Run: {run_id} | {description} ---")

        # Which methods to run
        analysis_types = []
        for col in method_cols:
            method_label = col.replace("run_", "")
            if (
                run_row.get(col) is True
                or str(run_row.get(col)).strip().lower() == "true"
            ):
                at = METHOD_LABEL_TO_ANALYSIS_TYPE.get(method_label)
                if at:
                    analysis_types.append(at)

        if not analysis_types:
            print(f"  No methods enabled for this run, skipping.")
            continue

        # Load baseline fresh for each run
        data = read_stix(stix_path)

        # Apply material changes for this run
        run_materials = df_materials[df_materials["run_id"] == run_id]
        if not run_materials.empty:
            data = apply_material_changes(data, run_materials)

        # Save modified STIX
        run_output_dir = output_root / run_id
        run_output_dir.mkdir(parents=True, exist_ok=True)
        output_stix = run_output_dir / f"{stix_path.stem}_{run_id}.stix"
        write_stix(output_stix, data)
        print(f"  Saved: {output_stix.name}")

        # Run D-Stability
        fos_map = run_dstability(output_stix, analysis_types)

        # Collect results
        result_row = {
            "run_id": run_id,
            "model_name": stix_path.stem,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        for at, fos in fos_map.items():
            label = next(
                (l for l, a in METHOD_LABEL_TO_ANALYSIS_TYPE.items() if a == at), at
            )
            result_row[f"FoS_{label}"] = fos
            print(f"  FoS ({label}) = {fos}")

        all_results.append(result_row)

    # Write results back to Excel
    if all_results:
        df_new = pd.DataFrame(all_results)
        df_existing = pd.read_excel(excel_path, sheet_name="results")
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        with pd.ExcelWriter(
            excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace"
        ) as writer:
            df_combined.to_excel(writer, sheet_name="results", index=False)

    print(f"\n✓ Results written to: {excel_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
