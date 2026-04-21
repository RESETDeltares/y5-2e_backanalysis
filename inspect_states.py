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

states_key = next(
    (k for k in data if "state" in k.lower() and "correlation" not in k.lower()), None
)
print("States key:", states_key)
print(json.dumps(data[states_key], indent=2)[:4000])
