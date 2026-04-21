import zipfile, json

stix_path = r"D:\codes\backcalculations\baseline_models\eemdijk_layeradjustment.stix"
stix = zipfile.ZipFile(stix_path)

data = {}
for name in stix.namelist():
    try:
        content = stix.read(name).decode("utf-8")
        if content.strip():
            data[name.replace(".json", "")] = json.loads(content)
    except Exception:
        pass

states_key = next(
    (k for k in data if "state" in k.lower() and "correlation" not in k.lower()), None
)
layers_key = next(k for k in data if "soillayers" in k.lower())
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

soils = data[soils_key]["Soils"]
layers = data[layers_key]["SoilLayers"]
state_points = data[states_key].get("StatePoints", [])

soil_id_to_code = {s["Id"]: s["Code"] for s in soils}
layer_to_soil_id = {layer["LayerId"]: layer["SoilId"] for layer in layers}

print(
    f"\n{'SP Label':<12} {'LayerId':<12} {'SoilId':<12} {'SoilCode':<35} {'StateType':<12} {'POP'}"
)
print("-" * 100)
for sp in state_points:
    layer_id = sp.get("LayerId")
    soil_id = layer_to_soil_id.get(layer_id, "?")
    soil_code = soil_id_to_code.get(soil_id, "unknown")
    label = sp.get("Label", "")
    stress = sp.get("Stress", {})
    state_type = stress.get("StateType", "")
    pop = stress.get("Pop", "-")
    print(
        f"{label:<12} {layer_id:<12} {soil_id:<12} {soil_code:<35} {state_type:<12} {pop}"
    )
