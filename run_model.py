"""
Run engine: reads the Excel run sheet, applies parameter changes to the
baseline STIX file, runs D-Stability, and writes FoS back to the results sheet.

Usage:
    1. Set the models to run to True in the USER CONTROL block below.
    2. Run:  python run_model.py

For every selected model <name> this reads:
    baseline_models/<name>.stix
    baseline_models/<name>_runs.xlsx

And writes modified STIX files to:
    results/<name>/<run_id>/<name>_<run_id>_cons.stix  (and _nocons)

Runs whose output STIX files already exist are skipped.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# USER CONTROL
# =============================================================================

# True = run this model (baseline_models/<name>.stix), False = skip it.
MODELS = {
    "bergambacht_v2":   False,
    "eemdijk_before":   False,
    "eemdijk_fail":     True,
    "ijkdijk_before":   False,
    "ijkdijk_fail":     True,
    "pernio":           False,
    "reevediep_before": False,
    "reevediep_fail":   False,
}


sys.path.insert(0, str(Path(__file__).parent))
from source.stix_io import (
    get_scenarios,
    get_soils,
    get_states,
    get_soillayers,
    read_stix,
    write_stix,
)
from source.constants.constants import DSTABILITY_BIN_FOLDER


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

    if pd.notna(active_model) and active_model and active_model != "SigmaTau":
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
        if active_model == "SigmaTau":
            _apply_sigmatau_table_from_key(soil, su_table_key)
        else:
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
    code_by_lower = {}
    for s in soils:
        code_by_lower.setdefault(s["Code"].strip().lower(), s["Code"])

    # Build sorted soillayers key list so layer_s1->index 0, layer_s2->index 1, etc.
    sl_key_list = sorted(
        k for k in data if k.startswith("soillayers/") and "visual" not in k.lower()
    )

    # Collect all layer_sN column names present in the dataframe
    layer_cols = sorted(c for c in material_rows.columns if c.startswith("layer_s"))

    for _, row in material_rows.iterrows():
        base_code = str(row["material_code"]).strip()
        # Case-insensitive match against STIX soil codes (exact match wins)
        if base_code not in soil_by_code:
            base_code = code_by_lower.get(base_code.lower(), base_code)
        raw_desc = row.get("simple_description", "")
        description = "" if pd.isna(raw_desc) else str(raw_desc).strip()

        # Gather non-empty layer assignments per scenario index
        # layer_s1 -> sl_key_list[0], layer_s2 -> sl_key_list[1], etc.
        layer_assignments = {}  # {sl_key: [label, ...]}
        for col in layer_cols:
            labels = _split_cell(row.get(col))
            if not labels:
                continue
            idx = int(col.replace("layer_s", "")) - 1
            if idx < len(sl_key_list):
                sl_key = sl_key_list[idx]
                layer_assignments[sl_key] = labels

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
            pop_labels = _split_cell(row.get("Layers"))
            pop_vals = [float(v) for v in _split_cell(row.get("POP"))]
            if pop_labels and pop_vals:
                _apply_pop_changes(data, clone_code, dict(zip(pop_labels, pop_vals)))

            _apply_ocr_from_row(data, row)

        else:
            # --- Direct-modify path (no description / no layer target) ---
            soil = soil_by_code.get(base_code)
            if not soil:
                print(f"  WARNING: material '{base_code}' not found in STIX, skipping.")
                continue

            _apply_soil_params(soil, row)

            for sl_key, labels in layer_assignments.items():
                _reassign_layers(data, labels, soil["Id"], sl_key=sl_key)

            pop_labels = _split_cell(row.get("Layers"))
            pop_vals = [float(v) for v in _split_cell(row.get("POP"))]
            if pop_labels and pop_vals:
                _apply_pop_changes(data, base_code, dict(zip(pop_labels, pop_vals)))

            _apply_ocr_from_row(data, row)

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


def _apply_sigmatau_table_from_key(soil: dict, sigmatau_table_key: str) -> None:
    """Load SigmaTauTable points from a JSON file in the su_tables/ folder."""
    import json

    project_root = Path(__file__).parent
    table_path = project_root / "su_tables" / "su_tables.json"
    if not table_path.exists():
        print(f"  WARNING: su_tables.json not found: {table_path}")
        return
    with open(table_path) as f:
        all_tables = json.load(f)
    if sigmatau_table_key not in all_tables:
        print(f"  WARNING: key '{sigmatau_table_key}' not found in su_tables.json")
        return
    points = all_tables[sigmatau_table_key]
    # Same {EffectiveStress, Su} source format; D-Stability names the strength field ShearStrength here.
    if isinstance(points, dict):
        points = [
            {"EffectiveStress": s, "ShearStrength": su}
            for s, su in zip(points["EffectiveStress"], points["Su"])
        ]
    soil["ShearStrengthModelTypeAbovePhreaticLevel"] = "SigmaTauTable"
    soil["ShearStrengthModelTypeBelowPhreaticLevel"] = "SigmaTauTable"
    soil.setdefault("SigmaTauTable", {})["SigmaTauTablePoints"] = points


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


def _split_cell(value) -> list:
    """Split a comma-separated Excel cell into stripped strings ([] if empty/NaN)."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return []
    return [s.strip() for s in str(value).split(",") if s.strip()]


def _apply_ocr_from_row(data: dict, row: pd.Series) -> None:
    """
    Read Layers / OCR_above / OCR_below from an Excel row and apply them to the
    matching state-line values. Either OCR column may be left empty to keep the
    baseline value on that side.
    """
    labels = _split_cell(row.get("Layers"))
    above = [float(v) for v in _split_cell(row.get("OCR_above"))]
    below = [float(v) for v in _split_cell(row.get("OCR_below"))]
    if not labels or not (above or below):
        return

    for name, vals in (("OCR_above", above), ("OCR_below", below)):
        if vals and len(vals) != len(labels):
            raise ValueError(
                f"run {row.get('run_id')} / {row.get('material_code')}: "
                f"{name} has {len(vals)} values but Layers has {len(labels)} labels."
            )

    label_to_ocr = {
        lbl: (above[i] if above else None, below[i] if below else None)
        for i, lbl in enumerate(labels)
    }
    _apply_ocr_changes(data, label_to_ocr)


def _apply_ocr_changes(data: dict, label_to_ocr: dict) -> None:
    """
    Set OCR on state-line values by label, e.g. {"SP 1": (above, below)}.
    A None value leaves that side unchanged. Updated sides are forced to
    StateType "Ocr". Matching is by label only (state lines carry no LayerId).
    """
    found = set()
    for key, states in data.items():
        if not key.startswith("states/"):
            continue
        for state_line in states.get("StateLines", []):
            for value in state_line.get("Values", []):
                label = value.get("Label", "")
                if label not in label_to_ocr:
                    continue
                found.add(label)
                for side, ocr in zip(("Above", "Below"), label_to_ocr[label]):
                    if ocr is None:
                        continue
                    stress = value.setdefault(side, {})
                    stress["StateType"] = "Ocr"
                    stress["Ocr"] = ocr

    missing = [lbl for lbl in label_to_ocr if lbl not in found]
    if missing:
        print(f"  WARNING: state-line labels not found for OCR: {missing}")


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


def get_calculations(data: dict) -> list:
    """
    List the calculations of the (first) scenario in D-Stability order.

    Each item: {index (1-based, as used by the console), label, analysis_type,
    result_id, fos_label}. fos_label is the short method name (upliftvan,
    bishop, spencer) when that method occurs once in the file; when the same
    method is used by several calculations (e.g. Ondiep/Diep, both Uplift-Van)
    the calculation's own label is used instead so the columns stay distinct.
    """
    scenario = get_scenarios(data)
    settings_by_id = {
        v.get("Id"): v
        for k, v in data.items()
        if k.startswith("calculationsettings/")
    }

    calcs = []
    for i, calc in enumerate(scenario.get("Calculations", []), start=1):
        settings = settings_by_id.get(calc.get("CalculationSettingsId"), {})
        calcs.append(
            {
                "index": i,
                "label": (calc.get("Label") or "").strip() or f"calc{i}",
                "analysis_type": settings.get("AnalysisType"),
                "result_id": calc.get("ResultId"),
            }
        )

    type_counts = {}
    for c in calcs:
        type_counts[c["analysis_type"]] = type_counts.get(c["analysis_type"], 0) + 1
    method_by_type = {at: lbl for lbl, at in METHOD_LABEL_TO_ANALYSIS_TYPE.items()}
    for c in calcs:
        at = c["analysis_type"]
        if type_counts[at] == 1 and at in method_by_type:
            c["fos_label"] = method_by_type[at]
        else:
            c["fos_label"] = c["label"]
    return calcs


def _read_fos(data: dict, result_id) -> float:
    """Return FactorOfSafety of the result object whose Id matches result_id."""
    for k, v in data.items():
        if k.startswith("results/") and isinstance(v, dict) and v.get("Id") == result_id:
            return v.get("FactorOfSafety")
    return None


def run_dstability(stix_path: Path, calculations: list) -> dict:
    """
    Run D-Stability for each calculation (see get_calculations) and return
    {fos_label: FoS}.
    """
    exe = str(Path(DSTABILITY_BIN_FOLDER) / "D-Stability Console.exe")

    fos_results = {}
    for calc in calculations:
        fos_label = calc["fos_label"]
        print(
            f"  Running '{calc['label']}' ({calc['analysis_type']}, "
            f"calc index {calc['index']})..."
        )
        try:
            proc = subprocess.run(
                [exe, str(stix_path), "1", str(calc["index"])],
                capture_output=True,
                text=True,
                errors="replace",
                check=True,
            )
            console_output = proc.stdout + "\n" + proc.stderr
        except subprocess.CalledProcessError as e:
            print(f"  ERROR running D-Stability: {e}")
            _print_console_messages(f"{e.stdout or ''}\n{e.stderr or ''}")
            fos_results[fos_label] = None
            continue

        # ResultId may be (re)assigned by D-Stability, so re-read it from the scenario
        result_data = read_stix(stix_path)
        result_id = next(
            (
                c["result_id"]
                for c in get_calculations(result_data)
                if c["index"] == calc["index"]
            ),
            calc["result_id"],
        )
        fos = _read_fos(result_data, result_id)
        if fos is None:
            print(f"  WARNING: no FoS for '{calc['label']}'. D-Stability reported:")
            _print_console_messages(console_output)
        fos_results[fos_label] = fos

    return fos_results


def _print_console_messages(output: str) -> None:
    """Print the error lines of D-Stability Console output (or its tail if none)."""
    lines = [l.strip() for l in output.splitlines() if l.strip()]
    errors = [l for l in lines if l.lower().startswith(("error", "warning"))]
    for line in errors or lines[-10:]:
        print(f"    | {line}")


def _append_results(excel_path: Path, rows: list) -> bool:
    """Append result rows to the 'results' sheet. Returns False if the file is locked."""
    try:
        df_existing = pd.read_excel(excel_path, sheet_name="results")
        df_combined = pd.concat([df_existing, pd.DataFrame(rows)], ignore_index=True)
        with pd.ExcelWriter(
            excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace"
        ) as writer:
            df_combined.to_excel(writer, sheet_name="results", index=False)
        return True
    except PermissionError:
        print(
            f"  WARNING: cannot write {excel_path.name} (open in Excel?). "
            f"{len(rows)} result row(s) kept, will retry after the next run."
        )
        return False


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
    pending_results = []  # rows not yet written to Excel (e.g. file was locked)
    n_written = 0

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

        # Run every calculation defined in the STIX scenario
        calculations = get_calculations(read_stix(stix_path))

        if not calculations:
            print(f"  No calculations found in STIX scenario, skipping.")
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

            fos_map = run_dstability(output_stix, calculations)

            result_row = {
                "run_id": variant_id,
                "model_name": stix_path.stem,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "constraints": keep_constraints,
            }
            for label, fos in fos_map.items():
                result_row[f"FoS_{label}"] = fos
                print(f"  FoS ({label}) = {fos}")

            # Save after every run so stopping the script loses at most one run
            pending_results.append(result_row)
            if _append_results(excel_path, pending_results):
                n_written += len(pending_results)
                pending_results = []

    if pending_results and _append_results(excel_path, pending_results):
        n_written += len(pending_results)
        pending_results = []
    if pending_results:
        print(
            f"\n  ERROR: {len(pending_results)} result row(s) could not be written "
            f"to {excel_path.name}:"
        )
        print(pd.DataFrame(pending_results).to_string(index=False))

    print(f"\n{n_written} result row(s) written to: {excel_path}")
    print(f"{'='*70}\n")


def main():
    project_root = Path(__file__).parent
    baseline_dir = project_root / "baseline_models"

    available = {p.stem: p for p in sorted(baseline_dir.glob("*.stix"))}
    if not available:
        print(f"ERROR: No .stix files found in {baseline_dir}")
        sys.exit(1)

    missing = [name for name, on in MODELS.items() if on and name not in available]
    if missing:
        print(f"WARNING: selected in MODELS but no .stix file found: {missing}")
    unlisted = [name for name in available if name not in MODELS]
    if unlisted:
        print(f"NOTE: .stix files not listed in MODELS (skipped): {unlisted}")

    selected = [available[name] for name, on in MODELS.items() if on and name in available]
    if not selected:
        print("No models selected. Set at least one model to True in MODELS.")
        return

    print(f"Running {len(selected)} model(s): {[p.stem for p in selected]}")

    for stix_path in selected:
        run_model(stix_path, project_root)


if __name__ == "__main__":
    main()
