"""
generate_models_matrix.py — Build a single CSV matrix showing, for every
run_id (subsoil.POP.embankment combination) defined across all cases,
whether that run was performed (Yes/No) for each case.

Reads the 'runs' sheet of each <case>_runs.xlsx in baseline_models/.
A run counts as "performed" for a case if its run_id appears in that
case's runs sheet (all defined runs were verified complete in the
results sheet — see run completeness check).

Output: models_matrix.csv (project root)
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent

# Preference order for which case's descriptive labels to show per run_id
# (label text formatting differs slightly between cases for the same code).
CASES = ["bergambacht_v2", "ijkdijk", "eemdijk", "pernio"]

DESC_COLS = ["subsoil_strength", "POP_states", "embankment_strength"]


def _run_sort_key(run_id: str) -> tuple:
    parts = str(run_id).split(".")
    return tuple(int(p) for p in parts)


def main():
    case_runs = {}
    for case in CASES:
        path = PROJECT_ROOT / "baseline_models" / f"{case}_runs.xlsx"
        case_runs[case] = pd.read_excel(path, sheet_name="runs").set_index(
            "run_id"
        )

    all_run_ids = sorted(
        set().union(*(df.index.astype(str) for df in case_runs.values())),
        key=_run_sort_key,
    )

    rows = []
    for run_id in all_run_ids:
        row = {"run_id": run_id}

        # Use the first case (in preference order) that defines this run_id
        # as the source of the descriptive labels.
        for col in DESC_COLS:
            row[col] = next(
                (
                    df.loc[run_id, col]
                    for df in case_runs.values()
                    if run_id in df.index
                ),
                "",
            )

        for case, df in case_runs.items():
            row[case] = "Yes" if run_id in df.index else "No"

        rows.append(row)

    matrix = pd.DataFrame(rows, columns=["run_id", *DESC_COLS, *CASES])
    output_path = PROJECT_ROOT / "models_matrix.csv"
    matrix.to_csv(output_path, index=False)
    print(f"✓ Wrote {len(matrix)} rows to {output_path}")


if __name__ == "__main__":
    main()
