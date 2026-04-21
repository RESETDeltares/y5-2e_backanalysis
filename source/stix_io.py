"""
STIX file I/O utilities.
Read and write D-Stability .stix files (ZIP archives of JSON).
"""

import json
import os
import time
import zipfile
from pathlib import Path


def read_stix(path: Path) -> dict:
    """Load a .stix file into a dictionary of {key: json_object}."""
    archive = zipfile.ZipFile(path)
    data = {}
    for name in archive.namelist():
        if name == "checksum":
            continue
        try:
            content = archive.read(name).decode("utf-8")
            if content.strip():
                data[name.replace(".json", "")] = json.loads(content)
        except Exception:
            pass
    return data


def write_stix(path: Path, data: dict) -> None:
    """Write a dictionary back to a .stix file."""
    data["projectinfo"]["Path"] = str(path)
    tmp_json = path.with_suffix(".json")

    archive = zipfile.ZipFile(path, "w")
    for key, value in data.items():
        with open(tmp_json, "w") as f:
            json.dump(value, f, sort_keys=False, indent=4)

        info = zipfile.ZipInfo()
        info.filename = key + ".json"
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, open(tmp_json, "rb").read())
        time.sleep(0.01)

    archive.close()
    os.remove(tmp_json)


def get_soils(data: dict) -> list:
    """Return the list of soil objects from loaded STIX data."""
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
    return data[soils_key]["Soils"]


def get_soillayers(data: dict) -> dict:
    """
    Return all soillayer sets keyed by their data key.
    e.g. {'soillayers/soillayers': [...], 'soillayers/soillayers_1': [...]}
    """
    return {
        k: data[k]["SoilLayers"]
        for k in data
        if "soillayer" in k.lower() and "visual" not in k.lower()
    }


def get_states(data: dict) -> dict:
    """
    Return all state sets keyed by their data key.
    e.g. {'states/states': [...], 'states/states_1': [...]}
    """
    return {
        k: data[k].get("StatePoints", [])
        for k in data
        if "states" in k.lower() and "correlation" not in k.lower()
    }


def get_scenarios(data: dict) -> dict:
    """Return the scenario object (contains Stages and Calculations)."""
    key = next((k for k in data if "scenario" in k.lower()), None)
    return data[key] if key else {}


def get_calc_settings_map(data: dict) -> dict:
    """
    Return mapping from AnalysisType -> data key for all calculation settings.
    e.g. {'BishopBruteForce': 'calculationsettings/calculationsettings',
          'UpliftVanParticleSwarm': 'calculationsettings/calculationsettings_1'}
    """
    result = {}
    for key, value in data.items():
        if key.startswith("calculationsettings/"):
            analysis_type = value.get("AnalysisType")
            if analysis_type:
                result[analysis_type] = key
    return result


def get_soil_pop_map(data: dict) -> dict:
    """
    Build a mapping from soil Code -> list of (layer_label, POP) tuples.
    Uses the first states set that has state points.
    """
    soils = get_soils(data)
    soil_id_to_code = {s["Id"]: s["Code"] for s in soils}

    all_layers = get_soillayers(data)
    all_states = get_states(data)

    # Build a combined layer_id -> soil_id map across all layer sets
    layer_to_soil_id = {}
    for layers in all_layers.values():
        for layer in layers:
            layer_to_soil_id[layer["LayerId"]] = layer["SoilId"]

    result = {}
    for state_points in all_states.values():
        for sp in state_points:
            layer_id = sp.get("LayerId")
            soil_id = layer_to_soil_id.get(layer_id)
            soil_code = soil_id_to_code.get(soil_id, "unknown")
            stress = sp.get("Stress", {})
            if stress.get("StateType") == "Pop":
                pop = stress.get("Pop")
                label = sp.get("Label", "")
                result.setdefault(soil_code, []).append((label, pop))

    return result
