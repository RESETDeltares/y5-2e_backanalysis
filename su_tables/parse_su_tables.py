"""
Parse all Su_tables*.txt files and write su_tables.json.

Naming convention for txt files:
  Su_tables_v1.txt   -> version tag "_v1" appended to all keys
  Su_tables_v2.txt   -> version tag "_v2" appended to all keys
  Su_tables.txt      -> no version tag (legacy / unversioned)

For each table key the following variants are extracted (where columns exist):
  <key>[_vN]          -> Su_5 or Tau_5             (5th percentile, direct)
  <key>_ln5[_vN]      -> ln(su_5)                  (log of 5th percentile, direct)
  <key>_mean[_vN]     -> exp(ln(su_mean))           (mean, back-transformed)
  <key>_sigma[_vN]    -> sigma(ln(su))              (log std dev, direct)
  <key>_nonasso[_vN]  -> Tau_davis_nonasso          (non-associative Davis friction)
  <key>_asso[_vN]     -> Tau_tanphi_asso            (associative tan-phi friction)

Stress column: 'EffectiveStress' or 'sigma_v_eff_mean_kpa' are both recognized.

Storage format in su_tables.json (compact two-list):
  "clay_2pct_v1": {
    "EffectiveStress": [1, 5, 10, ...],
    "Su":             [4.09, 6.75, ...]
  }

Example keys written to su_tables.json:
  clay_2pct_v1
  clay_2pct_ln5_v1
  clay_2pct_mean_v1
  clay_2pct_sigma_v1

In the Excel materials sheet, set 'su_table_key' to the full key, e.g.:
  clay_2pct_v1          -> 5th percentile from v1
  clay_2pct_mean_v2     -> mean from v2

Run: python su_tables/parse_su_tables.py
"""

import json
import math
import re
from pathlib import Path

folder = Path(__file__).parent
dst = folder / "su_tables.json"

# col_name -> (variant_suffix, apply_exp)
VARIANT_COLUMNS = {
    "Su_5": ("", False),
    "Tau_5": ("", False),
    "ln(su_5)": ("_ln5", False),
    "ln(tau_5)": ("_ln5", False),
    "ln(su_mean)": ("_mean", True),
    "ln(tau_mean)": ("_mean", True),
    "sigma(ln(su))": ("_sigma", False),
    "sigma(ln(tau))": ("_sigma", False),
    "Tau_davis_nonasso": ("_nonasso", False),
    "Tau_tanphi_asso": ("_asso", False),
    "Tau_davis_nonasso_int_princ": ("_nonasso_int_princ", False),
    "Tau_tanphi_asso_int_princ": ("_asso_int_princ", False),
}

# Recognized stress column names (mapped to 'EffectiveStress' internally)
STRESS_COLUMNS = {"EffectiveStress", "sigma_v_eff_mean_kpa"}

tables = {}

txt_files = sorted(folder.glob("Su_tables*.txt"))
if not txt_files:
    print("No Su_tables*.txt files found.")
    raise SystemExit(1)

for txt_file in txt_files:
    m = re.search(r"_v(\d+)", txt_file.stem, re.IGNORECASE)
    version_tag = f"_v{m.group(1)}" if m else ""
    print(f"Parsing {txt_file.name}  (version tag: '{version_tag or 'none'}')...")

    current_key = None
    col_map = {}

    for raw_line in txt_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("key:"):
            current_key = line.split(":", 1)[1].strip()
            col_map = {}
            continue

        parts = line.split("\t")

        if parts[0] in STRESS_COLUMNS:
            col_map = {h: i for i, h in enumerate(parts)}
            continue

        if current_key is None or not col_map:
            continue

        try:
            stress = float(parts[0])
        except (ValueError, IndexError):
            continue

        # Skip header-like rows that slipped through
        if parts[0] in STRESS_COLUMNS:
            continue

        for col_name, (variant_suffix, apply_exp) in VARIANT_COLUMNS.items():
            if col_name not in col_map:
                continue
            try:
                raw_val = float(parts[col_map[col_name]])
                su_val = math.exp(raw_val) if apply_exp else raw_val
            except (ValueError, IndexError):
                continue

            out_key = current_key + variant_suffix + version_tag
            entry = tables.setdefault(out_key, {"EffectiveStress": [], "Su": []})
            entry["EffectiveStress"].append(stress)
            entry["Su"].append(round(su_val, 6))

dst.write_text(json.dumps(tables, indent=2), encoding="utf-8")
print(f"\nWritten {len(tables)} tables to {dst.name}")
for k, v in sorted(tables.items()):
    print(f"  {k}: {len(v['EffectiveStress'])} points")
