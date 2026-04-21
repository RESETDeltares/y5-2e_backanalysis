"""
list_soils.py — Print all soils in a STIX file with their strength model and parameters.

Usage:
    python exploration/list_soils.py baseline_models/bergambacht.stix

Output columns:
    # | Code | Model | POP (kPa) | Parameters (S, m, phi, c, etc.)

This is useful when you first open a new STIX file and want to know:
- Which soil codes are present
- What strength model each soil uses (Su, MohrCoulomb, SuTable, etc.)
- What the baseline parameter values are
- Which layers have a POP pre-overburden pressure assigned to state points
"""

import sys
import zipfile
import json
from pathlib import Path


def load_stix(stix_path: str) -> dict:
    """Load all JSON entries from a STIX (ZIP) file into a flat dict."""
    data = {}
    with zipfile.ZipFile(stix_path) as z:
        for name in z.namelist():
            try:
                content = z.read(name).decode("utf-8")
                if content.strip():
                    data[name.replace(".json", "")] = json.loads(content)
            except Exception:
                pass
    return data


def find_key(data: dict, *fragments, exclude=()) -> str | None:
    """Find the first key that contains all fragments and none of the exclusions."""
    for k in data:
        kl = k.lower()
        if all(f in kl for f in fragments) and not any(e in kl for e in exclude):
            return k
    return None


def get_soil_params(soil: dict) -> dict:
    """Extract the relevant strength parameters from a soil dict."""
    model = soil.get("ShearStrengthModelTypeBelowPhreaticLevel", "")
    params = {
        "gamma_dry": soil.get("VolumetricWeightAbovePhreaticLevel", "N/A"),
        "gamma_wet": soil.get("VolumetricWeightBelowPhreaticLevel", "N/A"),
    }

    if model in ("Su", "SuShearStrengthModel"):
        m = soil.get("SuShearStrengthModel", {})
        params["S"] = m.get("ShearStrengthRatio", "N/A")
        params["m"] = m.get("StrengthIncreaseExponent", "N/A")

    elif model == "SuTable":
        m = soil.get("SuTable", {})
        points = m.get("SuTablePoints", [])
        params["m"] = m.get("StrengthIncreaseExponent", "N/A")
        params["n_points"] = len(points)
        if points:
            params["Su@sig0"] = points[0].get("Su", "N/A")
            params["Su@sig200"] = points[-1].get("Su", "N/A")

    elif model in ("MohrCoulombAdvanced", "MohrCoulombClassic"):
        key = (
            "MohrCoulombAdvancedShearStrengthModel"
            if model == "MohrCoulombAdvanced"
            else "MohrCoulombClassicShearStrengthModel"
        )
        m = soil.get(key, {})
        params["phi"] = m.get("FrictionAngle", "N/A")
        params["c"] = m.get("Cohesion", "N/A")
        if model == "MohrCoulombAdvanced":
            params["psi"] = m.get("Dilatancy", "N/A")

    elif model == "SigmaTauTable":
        points = soil.get("SigmaTauTable", {}).get("SigmaTauTablePoints", [])
        params["n_points"] = len(points)

    return params


def main(stix_path: str) -> None:
    """List all soils in a STIX file with their parameters and POP values."""
    data = load_stix(stix_path)

    # Find soils
    soils_key = find_key(data, "soils", exclude=("layer", "visual", "nail", "corr"))
    if not soils_key:
        print("ERROR: Could not find soils key in STIX file.")
        return
    soils = data[soils_key]["Soils"]

    # Build layer -> soil mapping (try first soillayers key found)
    layers_key = find_key(data, "soillayers", exclude=("visual",))
    layer_to_soil_id = {}
    if layers_key:
        for layer in data[layers_key].get("SoilLayers", []):
            layer_to_soil_id[layer["LayerId"]] = layer["SoilId"]
    soil_id_to_code = {s["Id"]: s["Code"] for s in soils}

    # Collect POP per soil code across all state keys
    soil_code_to_pops: dict[str, list] = {}
    for k, v in data.items():
        if "states" not in k.lower() or "correlation" in k.lower():
            continue
        for sp in v.get("StatePoints", []):
            stress = sp.get("Stress", {})
            if stress.get("StateType") != "Pop":
                continue
            pop = stress.get("Pop")
            if pop is None:
                continue
            layer_id = sp.get("LayerId")
            soil_id = layer_to_soil_id.get(layer_id)
            code = soil_id_to_code.get(soil_id, "unknown")
            soil_code_to_pops.setdefault(code, []).append(pop)

    # Print table
    print(f"\nFile: {stix_path}\n")
    print(f"{'#':<4} {'Code':<35} {'Model':<25} {'POP (kPa)':<20} Parameters")
    print("-" * 150)
    for i, soil in enumerate(soils, 1):
        code = soil.get("Code", "N/A")
        model = soil.get("ShearStrengthModelTypeBelowPhreaticLevel", "N/A")
        params = get_soil_params(soil)
        param_str = "  ".join(f"{k}={v}" for k, v in params.items())
        pops = soil_code_to_pops.get(code, [])
        pop_str = ", ".join(str(p) for p in pops) if pops else "-"
        print(f"{i:<4} {code:<35} {model:<25} {pop_str:<20} {param_str}")

    print(f"\nTotal: {len(soils)} soils")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python exploration/list_soils.py <path/to/file.stix>")
        sys.exit(1)
    main(sys.argv[1])
