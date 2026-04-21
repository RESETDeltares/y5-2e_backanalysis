"""
inspect_states.py — Print all state points in a STIX file.

Usage:
    python exploration/inspect_states.py baseline_models/bergambacht.stix

Output columns:
    Label | LayerId | SoilId | SoilCode | StateType | POP

This is useful to understand which layers have pre-overburden pressure (POP)
assigned in the model, and to see the exact label names used for each state
point — which are the labels you reference in the 'Layers' column of the
Excel run sheet when you want to modify POP values for a sensitivity run.

For multi-stage STIX files (multiple stages), state points from all stages
are shown with the originating key for context.
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


def main(stix_path: str) -> None:
    """Print all state points in a STIX file with soil code and POP values."""
    data = load_stix(stix_path)

    # Soils
    soils_key = next(
        (k for k in data if "soils" in k.lower()
         and "layer" not in k.lower()
         and "visual" not in k.lower()
         and "nail" not in k.lower()
         and "corr" not in k.lower()),
        None,
    )
    soils = data[soils_key]["Soils"] if soils_key else []
    soil_id_to_code = {s["Id"]: s["Code"] for s in soils}

    # Collect all state point keys (may be multiple for multi-stage)
    state_keys = [k for k in data if "states" in k.lower() and "correlation" not in k.lower()]

    if not state_keys:
        print("No state point data found in this STIX file.")
        return

    print(f"\nFile: {stix_path}\n")

    for states_key in sorted(state_keys):
        # Find the matching soillayers key (same suffix, e.g. _1, _2, ...)
        suffix = states_key.split("/")[-1].replace("states", "")
        layers_key = next(
            (k for k in data if "soillayers" in k.lower()
             and k.endswith(suffix)
             and "visual" not in k.lower()),
            next((k for k in data if "soillayers" in k.lower() and "visual" not in k.lower()), None),
        )
        layer_to_soil_id = {}
        if layers_key:
            for layer in data[layers_key].get("SoilLayers", []):
                layer_to_soil_id[layer["LayerId"]] = layer["SoilId"]

        state_points = data[states_key].get("StatePoints", [])
        print(f"Key: {states_key}  ({len(state_points)} state points)")
        print(f"  {'Label':<12} {'LayerId':<38} {'SoilCode':<35} {'StateType':<12} POP")
        print("  " + "-" * 110)

        for sp in state_points:
            layer_id = sp.get("LayerId", "?")
            soil_id = layer_to_soil_id.get(layer_id, "?")
            soil_code = soil_id_to_code.get(soil_id, "unknown")
            label = sp.get("Label", "")
            stress = sp.get("Stress", {})
            state_type = stress.get("StateType", "")
            pop = stress.get("Pop", "-")
            print(f"  {label:<12} {layer_id:<38} {soil_code:<35} {state_type:<12} {pop}")

        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python exploration/inspect_states.py <path/to/file.stix>")
        sys.exit(1)
    main(sys.argv[1])
