"""
explore_stix.py — Print the full internal structure of a STIX file.

Usage:
    python exploration/explore_stix.py baseline_models/bergambacht.stix

This gives a high-level overview of every resource inside a STIX file:
- All keys (JSON files inside the ZIP)
- Scenarios with their linked geometry, soillayers, waternet, and state IDs
- Geometry keys (how many are there — 1 for single-stage, N for multi-stage)
- SoilLayer keys and how many layers each has
- Waternet keys
- State keys and how many state points each has
- Calculation settings and their analysis types
- Soils with their strength model

STIX files are ZIP archives of JSON files. D-Stability uses a single-stage
layout (one geometry, one soillayers, etc.) or a multi-stage layout where
resources are duplicated with suffixes (_1, _2, ...) per stage.

This script is intended for onboarding and debugging — run it when you
encounter an unfamiliar STIX file to understand its structure before writing
any modification code.
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
    """Print the full structure of a STIX file."""
    data = load_stix(stix_path)

    print(f"\nFile: {stix_path}")
    print(f"Total keys: {len(data)}\n")

    print("=== ALL KEYS ===")
    for k in sorted(data.keys()):
        print(f"  {k}")

    # Scenarios
    scenarios_key = next((k for k in data if "scenario" in k.lower()), None)
    if scenarios_key:
        print(f"\n=== SCENARIOS ({scenarios_key}) ===")
        sc_data = data[scenarios_key]
        sc_list = (
            sc_data
            if isinstance(sc_data, list)
            else sc_data.get("Scenarios", [sc_data])
        )
        for sc in sc_list:
            print(
                f"  Id={sc.get('Id')}  Label={sc.get('Label')}"
                f"  GeometryId={sc.get('GeometryId')}"
                f"  SoilLayersId={sc.get('SoilLayersId')}"
                f"  WaternetId={sc.get('WaternetId')}"
                f"  StateId={sc.get('StateId')}"
            )

    # Geometry
    geo_keys = [k for k in data if "geometr" in k.lower()]
    print(f"\n=== GEOMETRY KEYS ({len(geo_keys)}) ===")
    for k in geo_keys:
        print(f"  {k}")

    # SoilLayers
    sl_keys = [
        k for k in data if "soillayer" in k.lower() and "visual" not in k.lower()
    ]
    print(f"\n=== SOILLAYER KEYS ({len(sl_keys)}) ===")
    for k in sl_keys:
        layers = data[k].get("SoilLayers", [])
        print(f"  {k}  ->  {len(layers)} layers")

    # Waternets
    wn_keys = [
        k
        for k in data
        if "waternet" in k.lower()
        and "creator" not in k.lower()
        and "mesh" not in k.lower()
    ]
    print(f"\n=== WATERNET KEYS ({len(wn_keys)}) ===")
    for k in wn_keys:
        print(f"  {k}")

    # States
    st_keys = [
        k for k in data if "states" in k.lower() and "correlation" not in k.lower()
    ]
    print(f"\n=== STATE KEYS ({len(st_keys)}) ===")
    for k in st_keys:
        pts = data[k].get("StatePoints", [])
        print(f"  {k}  ->  {len(pts)} state points")

    # Calculation settings
    cs_keys = [k for k in data if "calculationsettings" in k.lower()]
    print(f"\n=== CALCULATION SETTINGS ({len(cs_keys)}) ===")
    for k in cs_keys:
        print(f"  {k}  ->  AnalysisType={data[k].get('AnalysisType', 'N/A')}")

    # Soils
    soils_key = next(
        (
            k
            for k in data
            if "soils" in k.lower()
            and "layer" not in k.lower()
            and "visual" not in k.lower()
            and "nail" not in k.lower()
            and "corr" not in k.lower()
        ),
        None,
    )
    if soils_key:
        soils = data[soils_key]["Soils"]
        print(f"\n=== SOILS ({len(soils)}) ===")
        print(f"  {'Id':<6} {'Code':<35} Model Below")
        print("  " + "-" * 70)
        for s in soils:
            print(
                f"  {s.get('Id', '?'):<6} {s.get('Code', '?'):<35}"
                f" {s.get('ShearStrengthModelTypeBelowPhreaticLevel', '?')}"
            )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python exploration/explore_stix.py <path/to/file.stix>")
        sys.exit(1)
    main(sys.argv[1])
