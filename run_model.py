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

import copy
import uuid as _uuid


def _apply_soil_params(soil: dict, row: pd.Series) -> None:
    """Apply parameter columns from one Excel row onto a soil dict in-place."""
    active_model = row.get("active_model")

    if pd.notna(row.get("gamma_dry")):
        soil["VolumetricWeightAbovePhreaticLevel"] = float(row["gamma_dry"])
    if pd.notna(row.get("gamma_wet")):
        soil["VolumetricWeightBelowPhreaticLevel"] = float(row["gamma_wet"])

    if pd.notna(active_model) and active_model:
        soil["ShearStrengthModelTypeAbovePhreaticLevel"] = active_model
        soil["ShearStrengthModelTypeBelowPhreaticLevel"] = active_model

    if pd.notna(row.get("Su_S")) or pd.notna(row.get("Su_m")):
        m = soil.setdefault("SuShearStrengthModel", {})
        if pd.notna(row.get("Su_S")):
            m["ShearStrengthRatio"] = float(row["Su_S"])
        if pd.notna(row.get("Su_m")):
            m["StrengthIncreaseExponent"] = float(row["Su_m"])

    for model_key in [
        "MohrCoulombAdvancedShearStrengthModel",
        "MohrCoulombClassicShearStrengthModel",
    ]:
        if pd.notna(row.get("MC_phi")) or pd.notna(row.get("MC_c")):
            m = soil.setdefault(model_key, {})
            if pd.notna(row.get("MC_phi")):
                m["FrictionAngle"] = float(row["MC_phi"])
            if pd.notna(row.get("MC_c")):
                m["Cohesion"] = float(row["MC_c"])
            if pd.notna(row.get("MC_psi")):
                m["Dilatancy"] = float(row["MC_psi"])

    su_table_key = row.get("su_table_key")
    if pd.notna(su_table_key) and su_table_key:
        _apply_su_table_from_key(soil, su_table_key)


def _reassign_layers(
    data: dict, layer_labels: list, new_soil_id: str, sl_key: str = None
) -> None:
    """
    Point soillayer entries matching the given geometry labels to new_soil_id.
    If sl_key is given, only that soillayers set is updated; otherwise all sets.

    Each soillayers set is paired with its geometry by sorted index:
      soillayers/soillayers   <-> geometries/geometry
      soillayers/soillayers_1 <-> geometries/geometry_1
    Label->UUID lookups are scoped to the paired geometry to avoid cross-scenario
    collisions when different scenarios share the same layer label names.
    """
    sl_key_list = sorted(
        k for k in data if k.startswith("soillayers/") and "visual" not in k.lower()
    )
    geo_key_list = sorted(k for k in data if k.startswith("geometries/"))

    sl_keys_to_update = [sl_key] if sl_key else sl_key_list

    for k in sl_keys_to_update:
        if k not in sl_key_list:
            continue
        idx = sl_key_list.index(k)
        geo_key = geo_key_list[idx] if idx < len(geo_key_list) else None
        if not geo_key:
            print(f"  WARNING: no geometry found for {k}, skipping.")
            continue

        # Build label -> UUID only from the paired geometry
        geo_label_to_id = {}
        for layer in data[geo_key].get("Layers", []):
            lbl = layer.get("Label", "")
            if lbl:
                geo_label_to_id[lbl] = layer["Id"]

        target_ids = {geo_label_to_id[l] for l in layer_labels if l in geo_label_to_id}
        missing = [l for l in layer_labels if l not in geo_label_to_id]
        if missing:
            print(f"  WARNING: labels not found in {geo_key}: {missing}")

        for sl in data[k].get("SoilLayers", []):
            if sl.get("LayerId") in target_ids:
                sl["SoilId"] = new_soil_id


def apply_material_changes(data: dict, material_rows: pd.DataFrame) -> dict:
    """
    Apply parameter overrides from the materials sheet to loaded STIX data.

    When a row has a 'simple_description', a new soil is cloned from the base
    material_code soil and assigned that description as its Code/Name.
    All layers listed in layer_s1 are reassigned to the new soil.
    Rows sharing the same simple_description share the same new soil.

    Rows without a simple_description modify the base soil directly (legacy).
    """
    soils = get_soils(data)
    soil_by_code = {s["Code"]: s for s in soils}

    # Build sorted soillayers key list so layer_s1->index 0, layer_s2->index 1, etc.
    sl_key_list = sorted(
        k for k in data if k.startswith("soillayers/") and "visual" not in k.lower()
    )

    # Collect all layer_sN column names present in the dataframe
    layer_cols = sorted(c for c in material_rows.columns if c.startswith("layer_s"))

    for _, row in material_rows.iterrows():
        base_code = row["material_code"]
        raw_desc = row.get("simple_description", "")
        description = "" if pd.isna(raw_desc) else str(raw_desc).strip()

        # Gather non-empty layer assignments per scenario index
        # layer_s1 -> sl_key_list[0], layer_s2 -> sl_key_list[1], etc.
        layer_assignments = {}  # {sl_key: [label, ...]}
        for col in layer_cols:
            val = str(row.get(col, "") or "").strip()
            if not val:
                continue
            idx = int(col.replace("layer_s", "")) - 1
            if idx < len(sl_key_list):
                sl_key = sl_key_list[idx]
                layer_assignments[sl_key] = [l.strip() for l in val.split(",")]

        has_description = bool(description)
        has_layer = bool(layer_assignments)

        if has_description and has_layer:
            # --- Clone-and-reassign path ---
            # Stable clone key keeps link to original: e.g. "Material_BVN_RESET peat next (D)"
            clone_code = f"{base_code}_{description}"

            # Create the new soil once; reuse on subsequent rows with same clone_code
            if clone_code not in soil_by_code:
                base_soil = soil_by_code.get(base_code)
                if not base_soil:
                    print(
                        f"  WARNING: base material '{base_code}' not found, skipping."
                    )
                    continue
                new_soil = copy.deepcopy(base_soil)
                new_soil_id = str(_uuid.uuid4())
                new_soil["Id"] = new_soil_id
                new_soil["Code"] = clone_code
                new_soil["Name"] = clone_code
                soils.append(new_soil)
                soil_by_code[clone_code] = new_soil

                # Copy visual style from the original soil
                viz_list = data.get("soilvisualizations", {}).get(
                    "SoilVisualizations", []
                )
                orig_viz = next(
                    (v for v in viz_list if v.get("SoilId") == base_soil["Id"]), None
                )
                if orig_viz:
                    viz_list.append({**orig_viz, "SoilId": new_soil_id})

                print(f"  Cloned '{base_code}' -> '{clone_code}'")

            soil = soil_by_code[clone_code]
            _apply_soil_params(soil, row)

            for sl_key, labels in layer_assignments.items():
                _reassign_layers(data, labels, soil["Id"], sl_key=sl_key)

            # POP changes use the clone code
            layers_col = str(row.get("Layers", "") or "").strip()
            pop_col = str(row.get("POP", "") or "").strip()
            if layers_col and pop_col:
                pop_labels = [s.strip() for s in layers_col.split(",")]
                pop_vals = [float(s.strip()) for s in pop_col.split(",")]
                _apply_pop_changes(data, clone_code, dict(zip(pop_labels, pop_vals)))

        else:
            # --- Direct-modify path (no description / no layer target) ---
            soil = soil_by_code.get(base_code)
            if not soil:
                print(f"  WARNING: material '{base_code}' not found in STIX, skipping.")
                continue

            _apply_soil_params(soil, row)

            for sl_key, labels in layer_assignments.items():
                _reassign_layers(data, labels, soil["Id"], sl_key=sl_key)

            layers_col = str(row.get("Layers", "") or "").strip()
            pop_col = str(row.get("POP", "") or "").strip()
            if layers_col and pop_col:
                pop_labels = [s.strip() for s in layers_col.split(",")]
                pop_vals = [float(s.strip()) for s in pop_col.split(",")]
                _apply_pop_changes(data, base_code, dict(zip(pop_labels, pop_vals)))

    return data


def _apply_su_table_from_key(soil: dict, su_table_key: str) -> None:
    """Load SuTable points from a JSON file in the su_tables/ folder."""
    import json

    project_root = Path(__file__).parent
    table_path = project_root / "su_tables" / "su_tables.json"
    if not table_path.exists():
        print(f"  WARNING: su_tables.json not found: {table_path}")
        return
    with open(table_path) as f:
        all_tables = json.load(f)
    if su_table_key not in all_tables:
        print(f"  WARNING: key '{su_table_key}' not found in su_tables.json")
        return
    points = all_tables[su_table_key]
    # Convert compact two-list format to D-Stability list-of-dicts
    if isinstance(points, dict):
        points = [
            {"EffectiveStress": s, "Su": su}
            for s, su in zip(points["EffectiveStress"], points["Su"])
        ]
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


def strip_constraints(data: dict) -> dict:
    """
    Disable slip plane constraint zones (A, B, tangent) for all calc settings.
    SearchAreaA/B coordinates are left untouched — only the zone flags are cleared.
    """
    import copy

    data = copy.deepcopy(data)

    for key in data:
        if not key.startswith("calculationsettings/"):
            continue
        cs = data[key]

        # UpliftVanParticleSwarm
        uvps = cs.get("UpliftVanParticleSwarm", {})
        if uvps:
            spc = uvps.get("SlipPlaneConstraints", {})
            if spc:
                spc["IsZoneAConstraintsEnabled"] = False
                spc["IsZoneBConstraintsEnabled"] = False
                spc["IsSizeConstraintsEnabled"] = False

        # BishopBruteForce
        bbf = cs.get("BishopBruteForce", {})
        spc = bbf.get("SlipPlaneConstraints", {})
        if spc:
            spc["IsZoneAConstraintsEnabled"] = False
            spc["IsZoneBConstraintsEnabled"] = False
            spc["IsSizeConstraintsEnabled"] = False

        # Spencer / SpencerGenetic
        for method in ("Spencer", "SpencerGenetic"):
            spc = cs.get(method, {}).get("SlipPlaneConstraints", {})
            if spc:
                spc["IsEnabled"] = False

    return data


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


def run_model(stix_path: Path, project_root: Path) -> None:
    """Process all runs for a single STIX baseline file."""
    excel_path = stix_path.with_name(stix_path.stem + "_runs.xlsx")
    output_root = project_root / "results" / stix_path.stem

    if not excel_path.exists():
        print(f"  WARNING: No runs Excel found for {stix_path.name}, skipping.")
        print(f"  (Run generate_template.py first.)")
        return

    print(f"\n{'='*70}")
    print(f"  Model: {stix_path.name}")
    print(f"  Excel: {excel_path.name}")
    print(f"{'='*70}\n")

    # Read Excel
    df_runs = pd.read_excel(excel_path, sheet_name="runs")
    df_materials = pd.read_excel(excel_path, sheet_name="materials")

    output_root.mkdir(parents=True, exist_ok=True)
    all_results = []

    for _, run_row in df_runs.iterrows():
        run_id = run_row["run_id"]
        print(f"\n--- Run: {run_id} ---")

        # Parse constraints column: TRUE / FALSE / BOTH (default: TRUE)
        constraints_val = (
            str(run_row.get("constraints", "TRUE") or "TRUE").strip().upper()
        )
        if constraints_val == "BOTH":
            variants = [("_cons", True), ("_nocons", False)]
        elif constraints_val == "FALSE":
            variants = [("_nocons", False)]
        else:
            variants = [
                ("_cons", True)
            ]  # TRUE or missing -> no suffix, keep constraints

        # Skip if ALL variant output files already exist
        all_done = all(
            (
                output_root / str(run_id) / f"{stix_path.stem}_{run_id}{suffix}.stix"
            ).exists()
            for suffix, _ in variants
        )
        if all_done:
            print(f"  Already computed, skipping. (Delete output file(s) to rerun.)")
            continue

        # Which methods to run — if_run TRUE means run all calc methods in STIX
        if_run_val = str(run_row.get("if_run", "TRUE") or "TRUE").strip().upper()
        if if_run_val != "TRUE":
            print(f"  if_run not TRUE, skipping.")
            continue

        # Run all calc methods present in the STIX file
        calc_map = get_calc_settings_map(read_stix(stix_path))
        analysis_types = [
            at
            for label, at in METHOD_LABEL_TO_ANALYSIS_TYPE.items()
            if any(k == at for k in calc_map)
        ]

        if not analysis_types:
            print(f"  No matching calc methods found in STIX, skipping.")
            continue

        # Load baseline and apply material changes once
        data = read_stix(stix_path)
        run_materials = df_materials[df_materials["run_id"] == run_id]
        if not run_materials.empty:
            data = apply_material_changes(data, run_materials)

        # Run each variant (with/without constraints)
        for suffix, keep_constraints in variants:
            variant_id = f"{run_id}{suffix}"
            output_stix = (
                output_root / str(run_id) / f"{stix_path.stem}_{variant_id}.stix"
            )

            if output_stix.exists():
                print(f"  Variant '{variant_id}' already computed, skipping.")
                continue

            variant_data = data if keep_constraints else strip_constraints(data)
            output_stix.parent.mkdir(parents=True, exist_ok=True)
            write_stix(output_stix, variant_data)
            print(f"  Saved: {output_stix.name}")

            fos_map = run_dstability(output_stix, analysis_types)

            result_row = {
                "run_id": variant_id,
                "model_name": stix_path.stem,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "constraints": keep_constraints,
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


def main():
    project_root = Path(__file__).parent
    baseline_dir = project_root / "baseline_models"

    stix_files = sorted(baseline_dir.glob("*.stix"))
    if not stix_files:
        print(f"ERROR: No .stix files found in {baseline_dir}")
        sys.exit(1)

    print(f"Found {len(stix_files)} model(s): {[f.name for f in stix_files]}")

    for stix_path in stix_files:
        run_model(stix_path, project_root)


if __name__ == "__main__":
    main()
