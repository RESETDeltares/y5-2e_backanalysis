import zipfile, json

stix_path = r"D:\codes\backcalculations\baseline_models\pernio_.stix"
stix = zipfile.ZipFile(stix_path)

data = {}
for name in stix.namelist():
    try:
        content = stix.read(name).decode("utf-8")
        if content.strip():
            data[name.replace(".json", "")] = json.loads(content)
    except Exception:
        pass

print("=== ALL KEYS IN STIX ===")
for k in sorted(data.keys()):
    print(" ", k)

# Scenarios
scenarios_key = next((k for k in data if "scenario" in k.lower()), None)
if scenarios_key:
    print("\n=== SCENARIOS ===")
    scenarios = data[scenarios_key]
    sc_list = (
        scenarios
        if isinstance(scenarios, list)
        else scenarios.get("Scenarios", [scenarios])
    )
    for sc in sc_list:
        print(
            f"  Id={sc.get('Id')}  Label={sc.get('Label')}  GeometryId={sc.get('GeometryId')}  SoilLayersId={sc.get('SoilLayersId')}  WaternetId={sc.get('WaternetId')}  StateId={sc.get('StateId')}"
        )

# Geometry keys
geo_keys = [k for k in data if "geometr" in k.lower()]
print(f"\n=== GEOMETRY KEYS ({len(geo_keys)}) ===")
for k in geo_keys:
    print(f"  {k}")

# SoilLayer keys
sl_keys = [k for k in data if "soillayer" in k.lower() and "visual" not in k.lower()]
print(f"\n=== SOILLAYER KEYS ({len(sl_keys)}) ===")
for k in sl_keys:
    layers = data[k].get("SoilLayers", [])
    print(f"  {k}  ->  {len(layers)} layers")

# Waternet keys
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

# States keys
st_keys = [k for k in data if "states" in k.lower() and "correlation" not in k.lower()]
print(f"\n=== STATES KEYS ({len(st_keys)}) ===")
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
soils = data[soils_key]["Soils"]
print(f"\n=== SOILS ({len(soils)}) ===")
print(f"  {'Id':<6} {'Code':<35} {'Model Below'}")
print("  " + "-" * 70)
for s in soils:
    print(
        f"  {s.get('Id','?'):<6} {s.get('Code','?'):<35} {s.get('ShearStrengthModelTypeBelowPhreaticLevel','?')}"
    )
