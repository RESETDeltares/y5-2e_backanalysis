import zipfile, json

stix_path = r"D:\codes\backcalculations\baseline_models\bergambacht_reviewed.stix"
stix = zipfile.ZipFile(stix_path)

data = {}
for name in stix.namelist():
    try:
        content = stix.read(name).decode("utf-8")
        if content.strip():
            data[name.replace(".json", "")] = json.loads(content)
    except Exception:
        pass

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

# Build LayerId -> SoilCode mapping via soillayers
layers_key = next((k for k in data if "soillayers" in k.lower()), None)
layers = data[layers_key]["SoilLayers"]
layer_to_soil_id = {layer["LayerId"]: layer["SoilId"] for layer in layers}
soil_id_to_code = {s["Id"]: s["Code"] for s in soils}

# Build SoilCode -> list of POPs from states
states_key = next((k for k in data if "states/states" in k.lower()), None)
state_points = data[states_key].get("StatePoints", [])
soil_code_to_pops = {}
for sp in state_points:
    layer_id = sp.get("LayerId")
    soil_id = layer_to_soil_id.get(layer_id)
    soil_code = soil_id_to_code.get(soil_id, "unknown")
    pop = sp.get("Stress", {}).get("Pop", None)
    state_type = sp.get("Stress", {}).get("StateType", "")
    if state_type == "Pop" and pop is not None:
        soil_code_to_pops.setdefault(soil_code, []).append(pop)


def get_params(soil):
    model = soil.get("ShearStrengthModelTypeBelowPhreaticLevel", "")
    params = {}

    params["gamma_dry"] = soil.get("VolumetricWeightAbovePhreaticLevel", "N/A")
    params["gamma_wet"] = soil.get("VolumetricWeightBelowPhreaticLevel", "N/A")

    if model in ("Su",):
        m = soil.get("SuShearStrengthModel", {})
        params["S"] = m.get("ShearStrengthRatio", "N/A")
        params["m"] = m.get("StrengthIncreaseExponent", "N/A")

    elif model == "SuTable":
        m = soil.get("SuTable", {})
        points = m.get("SuTablePoints", [])
        params["m"] = m.get("StrengthIncreaseExponent", "N/A")
        params["n_points"] = len(points)
        if points:
            params["Su_at_sig0"] = points[0].get("Su", "N/A")
            params["Su_at_sig200"] = points[-1].get("Su", "N/A")

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
        m = soil.get("SigmaTauTable", {})
        points = m.get("SigmaTauTablePoints", [])
        params["n_points"] = len(points)

    return params


print(f"\n{'#':<4} {'Code':<35} {'Model':<25} {'POP (kPa)':<20} {'Parameters'}")
print("-" * 140)
for i, s in enumerate(soils, 1):
    code = s.get("Code", "N/A")
    model = s.get("ShearStrengthModelTypeBelowPhreaticLevel", "N/A")
    params = get_params(s)
    param_str = "  ".join(f"{k}={v}" for k, v in params.items())
    pops = soil_code_to_pops.get(code, [])
    pop_str = ", ".join(str(p) for p in pops) if pops else "-"
    print(f"{i:<4} {code:<35} {model:<25} {pop_str:<20} {param_str}")

print(f"\nTotal: {len(soils)} soils")
print(f"\nTotal: {len(soils)} soils")
