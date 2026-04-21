import zipfile, json

data = {}
with zipfile.ZipFile('baseline_models/eemdijk.stix') as z:
    for name in z.namelist():
        try:
            content = z.read(name).decode('utf-8')
            if content.strip():
                data[name.replace('.json','')] = json.loads(content)
        except:
            pass

soils = data['soils']['Soils']
soil_id_to_code = {s['Id']: s['Code'] for s in soils}

# Print the raw full content of first few soillayer objects
for sl_key in ['soillayers/soillayers', 'soillayers/soillayers_1']:
    layers = data[sl_key]['SoilLayers']
    print(f'\n=== {sl_key} ({len(layers)} layers) - FULL OBJECTS ===')
    for i, l in enumerate(layers):
        code = soil_id_to_code.get(l.get('SoilId'), '?')
        print(f'  [{i}] SoilCode={code}')
        for k, v in l.items():
            if k != 'SoilId':
                print(f'       {k} = {repr(v)[:80]}')
        print()
