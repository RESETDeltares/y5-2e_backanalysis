"""
plot_results.py  -  Visualise backcalculation FoS results.

Outputs (written to project root):
  plot_fos_cons.png      - Absolute FoS (constrained), one panel per case
  plot_fos_nocons.png    - Absolute FoS (unconstrained), one panel per case
  plot_pct_change.png    - % change from baseline, all cases combined (cons + nocons)
"""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).parent

# Case identity → color palette (light→dark for sub-runs .0, .1, .2, .3)
# fos_col: which result column to use for this case
CASES = {
    "bergambacht": {
        "label": "Bergambacht",
        "colors": ["#90caf9", "#1e88e5", "#0d47a1", "#062a6e"],  # blues
        "fos_col": "FoS_upliftvan",
    },
    "eemdijk": {
        "label": "Eemdijk",
        "colors": ["#ef9a9a", "#e53935", "#b71c1c", "#7f0000"],  # reds
        "fos_col": "FoS_upliftvan",
    },
    "ijkdijk": {
        "label": "IJkdijk",
        "colors": ["#a5d6a7", "#43a047", "#1b5e20", "#0a2e0f"],  # greens
        "fos_col": "FoS_upliftvan",
    },
    "pernio": {
        "label": "Pernio (Bishop)",
        "colors": ["#ce93d8", "#8e24aa", "#4a148c", "#2a0a52"],  # purples
        "fos_col": "FoS_bishop",
    },
    "bergambacht_v2": {
        "label": "Bergambacht v2",
        "colors": ["#80deea", "#00acc1", "#006064", "#002f35"],  # teals
        "fos_col": "FoS_upliftvan",
    },
}

# Run family → marker shape (auto-assigned from pool for any family number)
_MARKER_POOL = ["^", "o", "s", "D", "P", "*", "v", "h", "<", ">", "8", "H"]

# ---------------------------------------------------------------------------
# Strip-plot constants  (new S.P.E run convention)
# ---------------------------------------------------------------------------

# Active cases for the new-style strip plot (bergambacht v1 excluded)
_STRIP_CASES = ["bergambacht_v2", "eemdijk", "ijkdijk", "pernio"]
_STRIP_LABELS = {
    "bergambacht_v2": "Bergambacht",
    "eemdijk": "Eemdijk",
    "ijkdijk": "IJkdijk",
    "pernio": "Pernio",
}

_SUBSOIL_ORDER = [0, 3, 4, 5, 10, 13, 11, 14]
# Pernio-specific order: adds models 15 (avg mobilization) and 16 (cautious mobilization)
# right next to the Original subsoil
_PERNIO_SUBSOIL_ORDER = [0, 15, 16, 3, 4, 5, 10, 13, 11, 14]
_SUBSOIL_LABELS = {
    0: "Original",
    3: "LNA",
    4: "RY4",
    5: "RY5",
    10: "RY5.avg",
    13: "RY5.avg+(c.int)",
    11: "RY5.caut",
    14: "RY5.caut+(c.int)",
    15: "Orig.avg.mob.",
    16: "Orig.caut.mob.",
}

_EMB_COLORS = {
    0: "#000000",  # Original
    1: "#FF0000",  # Sand assoc.          (bright red)
    2: "#FFA500",  # Sand non-assoc.      (bright orange)
    3: "#00AA00",  # LNA clay             (bright green)
    4: "#0066CC",  # RY4 clay
    5: "#911eb4",  # RY5 clay
    6: "#1E90FF",  # Davis (CPT)          (dodger blue)
    7: "#00008B",  # Davis+int (CPT)      (dark blue)
    8: "#8B4513",  # Tan-phi (CPT)        (saddle brown)
    9: "#9932CC",  # Tan-phi+int (CPT)    (dark orchid purple)
    10: "#FFD700",  # RY5.avg            (gold)
    13: "#00FF00",  # RY5.avg+(c.int)    (lime green)
    11: "#FF00FF",  # RY5.caut           (magenta)
    14: "#008080",  # RY5.caut+(c.int)   (teal)
}
_EMB_LABELS = {
    0: "Original",
    1: "Sand assoc.",
    2: "Sand non-assoc.",
    3: "LNA clay",
    4: "RY4 clay",
    5: "RY5 clay",
    6: "Davis (CPT)",
    7: "Davis+int (CPT)",
    8: "Tan-phi (CPT)",
    9: "Tan-phi+int (CPT)",
    10: "RY5.avg",
    13: "RY5.avg+(c.int)",
    11: "RY5.caut",
    14: "RY5.caut+(c.int)",
}

# Marker shape per embankment — one distinct shape per family for readability
_EMB_MARKER = {
    0: "D",   # Original          — diamond
    1: "^",   # Sand assoc.       — triangle up  (Sand lab)
    2: "^",   # Sand non-assoc.   — triangle up  (Sand lab)
    3: "s",   # LNA clay          — square       (Clay lab)
    6: "P",   # Davis (CPT)       — filled plus  (CPT Davis)
    7: "P",   # Davis+int (CPT)   — filled plus  (CPT Davis)
    8: "*",   # Tan-phi (CPT)     — star         (CPT Tan-phi)
    9: "*",   # Tan-phi+int (CPT) — star         (CPT Tan-phi)
    10: "o",  # RY5.avg           — circle       (RY5 gen.)
    11: "o",  # RY5.caut          — circle       (RY5 gen.)
    13: "o",  # RY5.avg+(c.int)   — circle       (RY5 gen.)
    14: "o",  # RY5.caut+(c.int)  — circle       (RY5 gen.)
}

# Single representative color per case for focused plots
_CASE_COLORS = {
    "bergambacht_v2": "#00acc1",  # teal
    "eemdijk": "#e53935",  # red
    "ijkdijk": "#43a047",  # green
    "pernio": "#8e24aa",  # purple
}

# Embankment family groupings for family-level analysis
_EMB_FAMILIES = {
    "Original": [0],
    "Sand (lab)": [1, 2],
    "Clay (lab)": [3, 4, 5],
    "CPT Davis": [6, 7],
    "CPT Tan-phi": [8, 9],
    "RY5 gen.": [10, 13, 11, 14],
}
_FAMILY_COLORS = {
    "Original": "#555555",
    "Sand (lab)": "#f58231",
    "Clay (lab)": "#3cb44b",
    "CPT Davis": "#4363d8",
    "CPT Tan-phi": "#911eb4",
    "RY5 gen.": "#ffd54f",  # light gold (representative for family band)
}
# Reverse lookup: emb code → family name
_EMB_TO_FAMILY = {e: fam for fam, embs in _EMB_FAMILIES.items() for e in embs}


def _run_sort_key(rid: str) -> tuple:
    """Sort key so run_1 < run_1.1 < run_1.4 < run_2 < run_2.1 etc."""
    stripped = rid.replace("run_", "")
    parts = stripped.split(".")
    try:
        fam = int(parts[0])
    except ValueError:
        fam = 9999
    sub = int(parts[1]) if len(parts) > 1 else 0
    return (fam, sub)


def _family_marker(fam: str) -> str:
    """Return a marker for a family string like '1', '2', '7' etc. — always unique."""
    try:
        idx = int(fam) - 1
    except (ValueError, TypeError):
        idx = hash(fam)
    return _MARKER_POOL[idx % len(_MARKER_POOL)]


def run_style(run_id: str, case: str) -> tuple:
    """Return (color, marker) for a run_id + case combination."""
    case_colors = CASES[case]["colors"]
    if run_id == "baseline":
        return "#888888", "D"
    stripped = run_id.replace("run_", "")
    parts = stripped.split(".")
    fam = parts[0]
    sub = int(parts[1]) if len(parts) > 1 else 0
    color = case_colors[min(sub, len(case_colors) - 1)]
    marker = _family_marker(fam)
    return color, marker


def _draw_sigma_bands(ax, center: float = 1.0) -> None:
    """Overlay ±1σ (0.05) and ±2σ (0.10) tolerance bands around *center*.
    Bands use a very light green fill; boundaries are faint dotted green lines.
    Call this before plotting data so bands sit behind the markers.
    """
    _GREEN = "#43a047"
    # Outer band ±0.10  (2σ)
    ax.axhspan(center - 0.10, center + 0.10, color=_GREEN, alpha=0.07, zorder=0, lw=0)
    # Inner band ±0.05  (1σ) — slightly stronger fill
    ax.axhspan(center - 0.05, center + 0.05, color=_GREEN, alpha=0.10, zorder=0, lw=0)
    # Boundary lines
    for delta in (0.05, 0.10):
        ax.axhline(center + delta, color=_GREEN, lw=0.8, ls=":", alpha=0.55, zorder=1)
        ax.axhline(center - delta, color=_GREEN, lw=0.8, ls=":", alpha=0.55, zorder=1)


def _parse_spe(run_id: str):
    """Parse 'S.P.E' run_id -> (subsoil, pop, emb) ints, or None if not that format."""
    parts = run_id.split(".")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _load_strip_data(fos_col: str) -> pd.DataFrame:
    """Load results for all _STRIP_CASES for one FoS column.
    Returns flat DataFrame with columns:
      case, run_id, subsoil, pop, emb, variant (cons/nocons), fos
    """
    rows = []
    for name in _STRIP_CASES:
        p = PROJECT_ROOT / "baseline_models" / f"{name}_runs.xlsx"
        if not p.exists():
            continue
        df_res = pd.read_excel(p, sheet_name="results")
        if fos_col not in df_res.columns:
            continue
        for _, row in df_res.iterrows():
            rid = str(row["run_id"])
            for suffix, variant in (("_cons", "cons"), ("_nocons", "nocons")):
                if rid.endswith(suffix):
                    base = rid[: -len(suffix)]
                    parsed = _parse_spe(base)
                    if parsed and pd.notna(row[fos_col]):
                        s, pop, e = parsed
                        rows.append(
                            {
                                "case": name,
                                "run_id": base,
                                "subsoil": s,
                                "pop": pop,
                                "emb": e,
                                "variant": variant,
                                "fos": float(row[fos_col]),
                            }
                        )
                    break
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_combined(name: str) -> pd.DataFrame:
    """
    Load runs + results sheets for one case and return a merged DataFrame.
    Handles missing baseline gracefully (pct columns will be NaN).
    """
    fos_col = CASES[name]["fos_col"]
    path = PROJECT_ROOT / "baseline_models" / f"{name}_runs.xlsx"
    df_runs = pd.read_excel(path, sheet_name="runs")
    df_results = pd.read_excel(path, sheet_name="results")

    def base_id(rid):
        for suffix in ("_cons", "_nocons"):
            if str(rid).endswith(suffix):
                return rid[: -len(suffix)]
        return rid

    df_results = df_results.copy()
    df_results["base_id"] = df_results["run_id"].apply(base_id)
    df_results["variant"] = df_results["constraints"].map(
        {True: "cons", False: "nocons"}
    )

    pivot = df_results.pivot_table(
        index="base_id", columns="variant", values=fos_col, aggfunc="first"
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns={"base_id": "run_id"})

    merged = df_runs.merge(pivot, on="run_id", how="left")
    merged = merged.drop_duplicates(subset="run_id", keep="first")

    # Baseline FoS values (may not exist for all cases)
    bl_rows = merged.loc[merged["run_id"] == "baseline"]
    has_baseline = (
        len(bl_rows) > 0
        and "cons" in bl_rows.columns
        and pd.notna(bl_rows["cons"].values[0])
    )

    if has_baseline:
        bl_cons = float(bl_rows["cons"].values[0])
        bl_nocons = float(bl_rows["nocons"].values[0])
        merged["bl_cons"] = bl_cons
        merged["bl_nocons"] = bl_nocons
        merged["pct_cons"] = (merged["cons"] - bl_cons) / bl_cons * 100
        merged["pct_nocons"] = (merged["nocons"] - bl_nocons) / bl_nocons * 100
    else:
        # No baseline row — use FoS=1.0 as reference so the case still appears
        # in the % change plot (values represent % above/below the critical FoS).
        merged["bl_cons"] = 1.0
        merged["bl_nocons"] = 1.0
        merged["pct_cons"] = (merged["cons"] - 1.0) * 100
        merged["pct_nocons"] = (merged["nocons"] - 1.0) * 100

    # Run family (first number group before any dot)
    def family(rid):
        if rid == "baseline":
            return "baseline"
        return rid.replace("run_", "").split(".")[0]

    merged["family"] = merged["run_id"].apply(family)
    merged["has_baseline"] = has_baseline
    merged["model"] = name
    return merged


def load_for_method(name: str, fos_col: str) -> pd.DataFrame:
    """Like load_combined but uses the specified fos_col (may differ from CASES default)."""
    path = PROJECT_ROOT / "baseline_models" / f"{name}_runs.xlsx"
    df_runs = pd.read_excel(path, sheet_name="runs")
    df_results = pd.read_excel(path, sheet_name="results")

    if fos_col not in df_results.columns:
        # Method not available for this case — return shell with NaNs
        merged = df_runs.copy()
        merged["cons"] = float("nan")
        merged["nocons"] = float("nan")
        merged["has_baseline"] = False
        merged["family"] = merged["run_id"].apply(
            lambda r: (
                "baseline" if r == "baseline" else r.replace("run_", "").split(".")[0]
            )
        )
        merged["model"] = name
        return merged

    def base_id(rid):
        for suffix in ("_cons", "_nocons"):
            if str(rid).endswith(suffix):
                return rid[: -len(suffix)]
        return rid

    df_results = df_results.copy()
    df_results["base_id"] = df_results["run_id"].apply(base_id)
    df_results["variant"] = df_results["constraints"].map(
        {True: "cons", False: "nocons"}
    )

    pivot = df_results.pivot_table(
        index="base_id", columns="variant", values=fos_col, aggfunc="first"
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns={"base_id": "run_id"})

    merged = df_runs.merge(pivot, on="run_id", how="left")
    merged = merged.drop_duplicates(subset="run_id", keep="first")

    bl_rows = merged.loc[merged["run_id"] == "baseline"]
    has_baseline = (
        len(bl_rows) > 0
        and "cons" in bl_rows.columns
        and pd.notna(bl_rows["cons"].values[0])
    )

    def family(rid):
        if rid == "baseline":
            return "baseline"
        return rid.replace("run_", "").split(".")[0]

    merged["family"] = merged["run_id"].apply(family)
    merged["has_baseline"] = has_baseline
    merged["model"] = name
    return merged


def _get_available_methods() -> dict:
    """Return {method_suffix: [case_name, ...]} based on FoS_ columns in each results sheet."""
    method_cases: dict = {}
    for name in CASES:
        p = PROJECT_ROOT / "baseline_models" / f"{name}_runs.xlsx"
        if not p.exists():
            continue
        df_header = pd.read_excel(p, sheet_name="results", nrows=0)
        for col in df_header.columns:
            if col.startswith("FoS_"):
                method = col[len("FoS_") :]
                method_cases.setdefault(method, [])
                if name not in method_cases[method]:
                    method_cases[method].append(name)
    return method_cases


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _case_legend(ax, cases_used: list, families_used: list):
    """Legend: case color (darkest shade, square) + family markers (auto-discovered)."""
    handles = []
    for name in cases_used:
        info = CASES[name]
        h = plt.Line2D(
            [0],
            [0],
            marker="s",
            color="w",
            markerfacecolor=info["colors"][-1],
            markeredgecolor="none",
            markersize=9,
            label=info["label"],
        )
        handles.append(h)
    for fam in sorted(families_used, key=lambda f: (int(f) if f.isdigit() else 999)):
        h = plt.Line2D(
            [0],
            [0],
            marker=_family_marker(fam),
            color="w",
            markerfacecolor="#555555",
            markeredgecolor="none",
            markersize=8,
            label=f"run_{fam}.x",
        )
        handles.append(h)
    ax.legend(
        handles=handles,
        fontsize=7,
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        framealpha=0.85,
        ncol=1,
    )


def draw_fos_ax(ax, df, variant, case, case_label, show_ylabel, all_run_ids):
    """Draw absolute FoS for one case onto ax. Only shows runs with data for this case."""
    import numpy as np

    case_df = df[df["run_id"] != "baseline"].set_index("run_id")
    has_baseline = bool(df["has_baseline"].values[0])

    # Filter to runs that have data for this case/variant
    present_ids = [
        rid
        for rid in all_run_ids
        if rid in case_df.index and pd.notna(case_df.loc[rid, variant])
    ]

    for x, rid in enumerate(present_ids):
        color, marker = run_style(rid, case)
        y = case_df.loc[rid, variant]
        ax.scatter(
            x,
            y,
            color=color,
            marker=marker,
            s=70,
            edgecolors="white",
            linewidths=0.4,
            zorder=3,
        )

    ref_handles = []
    if has_baseline:
        bl = float(df.loc[df["run_id"] == "baseline", variant].values[0])
        ax.axhline(bl, color="#555555", lw=1.2, ls="--")
        ref_handles.append(
            plt.Line2D(
                [0], [0], color="#555555", lw=1.2, ls="--", label=f"Baseline = {bl:.3f}"
            )
        )
    ax.axhline(1.0, color="#c0392b", lw=0.9, ls=":", alpha=0.85)
    ref_handles.append(
        plt.Line2D([0], [0], color="#c0392b", lw=0.9, ls=":", label="FoS = 1.0")
    )

    # Family handles — only for runs present in this case
    family_handles = []
    seen_fam = []
    for rid in case_df.index:
        fam = rid.replace("run_", "").split(".")[0]
        if fam not in seen_fam:
            seen_fam.append(fam)
            color, marker = run_style(f"run_{fam}", case)
            family_handles.append(
                plt.Line2D(
                    [0],
                    [0],
                    marker=marker,
                    color="w",
                    markerfacecolor=color,
                    markeredgecolor="none",
                    markersize=8,
                    label=f"run_{fam}.x",
                )
            )
    fos_label = CASES[case]["fos_col"].replace("FoS_", "")
    ax.legend(
        handles=family_handles + ref_handles,
        fontsize=7,
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        framealpha=0.85,
        title=fos_label,
        title_fontsize=7,
    )

    ax.set_xticks(list(range(len(present_ids))))
    ax.set_xticklabels(present_ids, rotation=45, ha="right", fontsize=8)
    ax.tick_params(axis="x", pad=8)
    ax.set_title(case_label, fontsize=11, fontweight="bold")
    if show_ylabel:
        ax.set_ylabel("FoS")
    ax.grid(axis="y", alpha=0.3, lw=0.5)
    ax.set_xlim(-0.5, len(present_ids) - 0.5)
    ax.set_ylim(0.4, 1.4)
    ax.set_yticks(np.arange(0.4, 1.41, 0.1))


def draw_pct_combined_ax(ax, dfs: dict, variant: str, title: str):
    """Draw % change from baseline for ALL cases on a single axis."""
    # Collect all unique run_ids (non-baseline) across cases, sorted numerically
    seen: set = set()
    all_run_ids = []
    for name, df in dfs.items():
        for rid in df.loc[df["run_id"] != "baseline", "run_id"]:
            if rid not in seen:
                seen.add(rid)
                all_run_ids.append(rid)
    all_run_ids.sort(key=_run_sort_key)

    x_pos = {rid: i for i, rid in enumerate(all_run_ids)}

    for name, df in dfs.items():
        plot_df = df[df["run_id"] != "baseline"]
        for _, row in plot_df.iterrows():
            rid = row["run_id"]
            pct = row[f"pct_{variant}"]
            if not pd.notna(pct) or rid not in x_pos:
                continue
            color, marker = run_style(rid, name)
            ax.scatter(
                x_pos[rid],
                pct,
                color=color,
                marker=marker,
                s=70,
                edgecolors="white",
                linewidths=0.4,
                zorder=3,
            )

    ax.axhline(0, color="#555555", lw=1.2, ls="--", alpha=0.7)

    families_used = sorted(
        {rid.replace("run_", "").split(".")[0] for rid in all_run_ids},
        key=lambda f: int(f) if f.isdigit() else 999,
    )
    ax.set_xticks(list(x_pos.values()))
    ax.set_xticklabels(list(x_pos.keys()), rotation=45, ha="right", fontsize=8)
    ax.tick_params(axis="x", pad=8)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel("% change from baseline")
    ax.grid(axis="y", alpha=0.3, lw=0.5)
    ax.set_xlim(-0.5, len(all_run_ids) - 0.5)
    _case_legend(ax, list(dfs.keys()), families_used)


# ---------------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------------


def plot_absolute(dfs: dict, variant: str, out_path: Path) -> None:
    """2×2 grid: absolute FoS per case. All panels share the same x-axis."""
    title = "Constrained" if variant == "cons" else "Unconstrained"

    # Build unified x-axis (union of all non-baseline run_ids, sorted numerically)
    seen: set = set()
    all_run_ids: list = []
    for df in dfs.values():
        for rid in df.loc[df["run_id"] != "baseline", "run_id"]:
            if rid not in seen:
                seen.add(rid)
                all_run_ids.append(rid)
    all_run_ids.sort(key=_run_sort_key)

    n_runs = len(all_run_ids)
    n = len(dfs)
    ncols = 2
    nrows = (n + ncols - 1) // ncols
    panel_h = 6
    # Panels slightly wider than tall (close to square); cap so they don't grow huge
    panel_w = min(max(5, n_runs * 0.35), panel_h * 1.3)
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(ncols * panel_w, nrows * panel_h),
        gridspec_kw={"wspace": 0.55, "hspace": 0.65},
    )
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
    fig.suptitle(f"Factor of Safety — {title}", fontsize=14, fontweight="bold", y=1.01)

    for i, name in enumerate(dfs.keys()):
        draw_fos_ax(
            axes_flat[i],
            dfs[name],
            variant,
            name,
            CASES[name]["label"],
            i % ncols == 0,
            all_run_ids,
        )
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_absolute_stack(dfs: dict, variant: str, out_path: Path) -> None:
    """4 rows x 1 col: one case per row, full-width panels. All share the same x-axis."""
    title = "Constrained" if variant == "cons" else "Unconstrained"

    seen: set = set()
    all_run_ids: list = []
    for df in dfs.values():
        for rid in df.loc[df["run_id"] != "baseline", "run_id"]:
            if rid not in seen:
                seen.add(rid)
                all_run_ids.append(rid)
    all_run_ids.sort(key=_run_sort_key)

    n_runs = len(all_run_ids)
    n = len(dfs)
    panel_w = max(10, n_runs * 0.5)
    panel_h = 4
    fig, axes = plt.subplots(
        n,
        1,
        figsize=(panel_w, n * panel_h),
        gridspec_kw={"hspace": 0.7},
    )
    if n == 1:
        axes = [axes]
    fig.suptitle(
        f"Factor of Safety \u2014 {title}", fontsize=14, fontweight="bold", y=1.01
    )

    for i, name in enumerate(dfs.keys()):
        draw_fos_ax(
            axes[i],
            dfs[name],
            variant,
            name,
            CASES[name]["label"],
            True,
            all_run_ids,
        )

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_bergambacht_compare(
    df_v1: pd.DataFrame, df_v2: pd.DataFrame, out_path: Path
) -> None:
    """Side-by-side comparison of Bergambacht v1 vs v2 absolute FoS (cons + nocons)."""
    import numpy as np

    # Shared x-axis: union of both versions' run IDs, sorted
    seen: set = set()
    all_run_ids: list = []
    for df in (df_v1, df_v2):
        for rid in df.loc[df["run_id"] != "baseline", "run_id"]:
            if rid not in seen:
                seen.add(rid)
                all_run_ids.append(rid)
    all_run_ids.sort(key=_run_sort_key)

    n_runs = len(all_run_ids)
    panel_w = max(10, n_runs * 0.5)
    fig, axes = plt.subplots(2, 1, figsize=(panel_w, 10), gridspec_kw={"hspace": 0.65})
    fig.suptitle("Bergambacht v1 vs v2 — Absolute FoS", fontsize=14, fontweight="bold")

    versions = [
        ("bergambacht", df_v1, "Constrained", "cons"),
        ("bergambacht", df_v1, "Unconstrained", "nocons"),
    ]

    OFFSET = {"bergambacht": -0.18, "bergambacht_v2": 0.18}

    for ax, variant, subtitle in zip(
        axes, ("cons", "nocons"), ("Constrained", "Unconstrained")
    ):
        # First pass: collect (x, y) per version to draw connecting lines
        pts = {"bergambacht": {}, "bergambacht_v2": {}}
        for case_key, df in (("bergambacht", df_v1), ("bergambacht_v2", df_v2)):
            case_df = df[df["run_id"] != "baseline"].set_index("run_id")
            offset = OFFSET[case_key]
            for xi, rid in enumerate(all_run_ids):
                if rid not in case_df.index:
                    continue
                y = case_df.loc[rid, variant]
                if not pd.notna(y):
                    continue
                pts[case_key][rid] = (xi + offset, y)

        # Draw connecting lines between v1 and v2 for shared runs
        for rid in all_run_ids:
            if rid in pts["bergambacht"] and rid in pts["bergambacht_v2"]:
                x1, y1 = pts["bergambacht"][rid]
                x2, y2 = pts["bergambacht_v2"][rid]
                ax.plot(
                    [x1, x2],
                    [y1, y2],
                    color="#aaaaaa",
                    lw=0.8,
                    ls="-",
                    zorder=2,
                    alpha=0.6,
                )

        # Second pass: scatter points on top
        for case_key, df in (("bergambacht", df_v1), ("bergambacht_v2", df_v2)):
            for rid, (x, y) in pts[case_key].items():
                color, marker = run_style(rid, case_key)
                ax.scatter(
                    x,
                    y,
                    color=color,
                    marker=marker,
                    s=90,
                    edgecolors="#333333",
                    linewidths=0.6,
                    zorder=4,
                )

            # Baseline line
            has_baseline = bool(df["has_baseline"].values[0])
            if has_baseline:
                bl = float(df.loc[df["run_id"] == "baseline", variant].values[0])
                lc = CASES[case_key]["colors"][-1]
                ax.axhline(bl, color=lc, lw=1.4, ls="--", alpha=0.8)

        ax.axhline(1.0, color="#c0392b", lw=0.9, ls=":", alpha=0.85)
        ax.set_xticks(list(range(len(all_run_ids))))
        ax.set_xticklabels(all_run_ids, rotation=45, ha="right", fontsize=8)
        ax.tick_params(axis="x", pad=8)
        ax.set_title(subtitle, fontsize=11, fontweight="bold")
        ax.set_ylabel("FoS")
        ax.grid(axis="y", alpha=0.3, lw=0.5)
        ax.set_xlim(-0.5, len(all_run_ids) - 0.5)
        ax.set_ylim(0.4, 1.4)
        ax.set_yticks(np.arange(0.4, 1.41, 0.1))

        # Legend
        handles = []
        for case_key in ("bergambacht", "bergambacht_v2"):
            info = CASES[case_key]
            handles.append(
                plt.Line2D(
                    [0],
                    [0],
                    marker="s",
                    color="w",
                    markerfacecolor=info["colors"][-1],
                    markeredgecolor="none",
                    markersize=9,
                    label=info["label"],
                )
            )
            handles.append(
                plt.Line2D(
                    [0],
                    [0],
                    color=info["colors"][-1],
                    lw=1.2,
                    ls="--",
                    label=f"{info['label']} baseline",
                )
            )
        handles.append(
            plt.Line2D([0], [0], color="#c0392b", lw=0.9, ls=":", label="FoS = 1.0")
        )
        ax.legend(
            handles=handles,
            fontsize=7,
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
            borderaxespad=0,
            framealpha=0.85,
        )

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def _strip_methods() -> list:
    """Return sorted list of FoS method suffixes available across all strip cases."""
    found: set = set()
    for name in _STRIP_CASES:
        p = PROJECT_ROOT / "baseline_models" / f"{name}_runs.xlsx"
        if not p.exists():
            continue
        df_h = pd.read_excel(p, sheet_name="results", nrows=0)
        for col in df_h.columns:
            if col.startswith("FoS_"):
                found.add(col[4:])
    return sorted(found)


def plot_case_strip(
    out_path: Path,
    method: str,
    variants: tuple = ("cons", "nocons"),
    active_embs: list = None,
    active_cases: list = None,
    active_subsoils: list = None,
    filter_subsoils: list = None,
    filter_embs: list = None,
    pop_replaced_only: bool = False,
) -> None:
    """Like plot_subsoil_strip but with axes swapped:
    Outer groups = cases (Bergambacht, Eemdijk, IJkdijk, Pernio).
    Inner X positions = subsoil models (Original, LNA, RY4, RY5, ...).
    Color = embankment type.  Fill = POP state.
    active_embs / active_cases / active_subsoils: full alpha when active, 0.05 otherwise.
    filter_subsoils / filter_embs: hard filter — excluded items are not shown at all.
    pop_replaced_only: when True only POP-replaced (filled) constrained points are shown.
    """
    import numpy as np

    df = _load_strip_data(f"FoS_{method}")
    if df.empty:
        return

    # Per-case subsoil order: pernio gets models 15 & 16 next to Original
    _case_sub_order = {
        case: (_PERNIO_SUBSOIL_ORDER if case == "pernio" else _SUBSOIL_ORDER)
        for case in _STRIP_CASES
    }

    # Hard-filter subsoil slots per case (filter_subsoils removes positions entirely)
    if filter_subsoils is not None:
        _case_sub_order = {
            case: [s for s in order if s in filter_subsoils]
            for case, order in _case_sub_order.items()
        }

    # Variable-width groups: each case group is as wide as its subsoil list
    _gap = 1
    case_widths = [len(_case_sub_order[c]) for c in _STRIP_CASES]
    case_offsets = []
    _off = 0
    for w in case_widths:
        case_offsets.append(_off)
        _off += w + _gap
    total_width = _off - _gap

    def xc(case_idx, sub_idx, emb):
        jitter = (emb % 5 - 2) * 0.09
        return case_offsets[case_idx] + sub_idx + jitter

    title_suffix = (
        "(\u25cf constrained, \u00d7 unconstrained)"
        if len(variants) > 1
        else "(constrained only)"
    )
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle(
        f"FoS by case \u2014 {method}  {title_suffix}",
        fontsize=12,
        fontweight="bold",
    )

    for _, row in df.iterrows():
        if row["variant"] not in variants:
            continue
        s = row["subsoil"]
        case = row["case"]
        if case not in _STRIP_CASES:
            continue
        sub_order = _case_sub_order[case]
        if s not in sub_order:
            continue
        si = sub_order.index(s)
        ci = _STRIP_CASES.index(case)
        e = row["emb"]

        # Hard filters — skip excluded embankments and POP-original points
        if filter_embs is not None and e not in filter_embs:
            continue
        if pop_replaced_only and row["pop"] == 0:
            continue

        x = xc(ci, si, e)
        color = _EMB_COLORS.get(e, "#000000")
        a = (
            0.55
            if (
                (active_embs is None or e in active_embs)
                and (active_cases is None or case in active_cases)
                and (active_subsoils is None or s in active_subsoils)
            )
            else 0.05
        )

        if row["variant"] == "cons":
            pop_matched = row["pop"] != 0
            marker = _EMB_MARKER.get(e, "o")
            ax.scatter(
                x,
                row["fos"],
                marker=marker,
                s=28,
                facecolors=color if pop_matched else "none",
                edgecolors=color,
                linewidths=0.4 if pop_matched else 1.6,
                zorder=4,
                alpha=a,
            )
        else:
            marker = _EMB_MARKER.get(e, "o")
            ax.scatter(
                x,
                row["fos"],
                color=color,
                marker=marker,
                s=28,
                linewidths=1.0,
                zorder=4,
                alpha=a,
            )

    _draw_sigma_bands(ax)
    ax.axhline(1.1, color="#4caf50", lw=0.8, ls="--", alpha=0.6, zorder=2)
    ax.axhline(1.05, color="#ff9800", lw=0.8, ls="--", alpha=0.6, zorder=2)
    ax.axhline(1.0, color="#c0392b", lw=1.0, ls=":", alpha=0.9, zorder=3)

    xtick_pos, xtick_labels = [], []
    for ci, case in enumerate(_STRIP_CASES):
        sub_order = _case_sub_order[case]
        if ci > 0:
            ax.axvline(case_offsets[ci] - 0.5, color="#cccccc", lw=1.0, zorder=1)
        for si, s in enumerate(sub_order):
            xtick_pos.append(case_offsets[ci] + si)
            xtick_labels.append(_SUBSOIL_LABELS[s])

    ax.set_xticks(xtick_pos)
    ax.set_xticklabels(xtick_labels, rotation=40, ha="right", fontsize=8)

    for ci, case in enumerate(_STRIP_CASES):
        sub_order = _case_sub_order[case]
        mid_x = case_offsets[ci] + (len(sub_order) - 1) / 2
        ax.text(
            mid_x,
            1.52,
            _STRIP_LABELS[case],
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.2", fc="#f0f0f0", ec="#cccccc", lw=0.8),
        )

    ax.set_xlim(-0.8, total_width - 0.2)
    ax.set_ylim(0.4, 1.6)
    ax.set_yticks(np.arange(0.4, 1.61, 0.1))
    ax.set_ylabel("FoS")
    ax.grid(axis="y", alpha=0.25, lw=0.5)

    present = set(df["emb"].dropna().astype(int))
    if filter_embs is not None:
        present = present & set(filter_embs)
    present_embs = [e for e in _EMB_LABELS if e in present]

    handles = [
        plt.Line2D(
            [0],
            [0],
            marker=_EMB_MARKER.get(e, "o"),
            color="w",
            markerfacecolor=_EMB_COLORS[e],
            markeredgecolor=_EMB_COLORS[e],
            markersize=8,
            linestyle="None",
            label=_EMB_LABELS[e],
        )
        for e in present_embs
    ]
    if "cons" in variants and not pop_replaced_only:
        handles.append(
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="#888",
                markeredgecolor="#888",
                markersize=7,
                linestyle="None",
                label="Cons, POP replaced",
            )
        )
        if not pop_replaced_only:
            handles.append(
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="none",
                    markeredgecolor="#888",
                    markersize=7,
                    linestyle="None",
                    label="Cons, POP original",
                )
            )
    if "nocons" in variants:
        handles.append(
            plt.Line2D(
                [0],
                [0],
                marker="x",
                color="#555",
                markersize=7,
                linestyle="None",
                label="Unconstrained",
            )
        )
    handles.append(
        plt.Line2D([0], [0], color="#c0392b", lw=1.0, ls=":", label="FoS = 1.0")
    )
    handles.append(
        plt.Line2D([0], [0], color="#ff9800", lw=0.8, ls="--", label="FoS = 1.05")
    )
    handles.append(
        plt.Line2D([0], [0], color="#4caf50", lw=0.8, ls="--", label="FoS = 1.1")
    )
    ax.legend(
        handles=handles,
        fontsize=7,
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        framealpha=0.85,
        title="Embankment",
        title_fontsize=8,
    )

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_fos_heatmaps(out_path, method, variant="cons"):
    """Create 2×2 grid of heatmaps showing FoS for all embankment×subsoil combos per case.
    
    Each cell = FoS value, color-coded by safety zone:
    - Red (< 1.0), Orange (1.0-1.05), Yellow (1.05-1.1), Green (≥ 1.1)
    Rows = embankment types, Columns = subsoil models per case.
    """
    import numpy as np
    from matplotlib.colors import ListedColormap, BoundaryNorm
    import seaborn as sns

    fos_col = f"FoS_{method}"
    df = _load_strip_data(fos_col)
    if df.empty:
        return

    # Filter to constrained variant
    df = df[df["variant"] == variant].copy()

    # Create 2×2 grid
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    # Define custom colormap for safety zones
    colors = ["#c0392b", "#ff9800", "#fff9c4", "#4caf50"]  # Red, Orange, Light Yellow, Green
    boundaries = [0.4, 1.0, 1.05, 1.1, 1.6]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(boundaries, cmap.N)

    # Embankment order (same as used in scatter plots)
    all_embs = sorted(df["emb"].unique())
    emb_labels = {e: _EMB_LABELS.get(e, f"E{e}") for e in all_embs}

    for idx, case in enumerate(_STRIP_CASES):
        ax = axes[idx]
        case_df = df[df["case"] == case].copy()

        if case_df.empty:
            ax.text(0.5, 0.5, f"No data for {case}", ha="center", va="center")
            ax.set_xticks([])
            ax.set_yticks([])
            continue

        # Get subsoil order for this case
        sub_order = (
            _PERNIO_SUBSOIL_ORDER if case == "pernio" else _SUBSOIL_ORDER
        )

        # Build pivot table: rows=embankment, cols=subsoil, values=FoS
        pivot_data = case_df.pivot_table(
            index="emb", columns="subsoil", values="fos", aggfunc="first"
        )

        # Reorder columns by subsoil order, keep only those in sub_order
        pivot_data = pivot_data[[s for s in sub_order if s in pivot_data.columns]]

        # Reorder rows by all_embs
        pivot_data = pivot_data.reindex([e for e in all_embs if e in pivot_data.index])

        # Plot heatmap
        sns.heatmap(
            pivot_data,
            ax=ax,
            cmap=cmap,
            norm=norm,
            cbar=False,
            annot=True,
            fmt=".2f",
            linewidths=0.5,
            linecolor="white",
            cbar_kws={"label": "Factor of Safety"},
        )

        # Set labels
        ax.set_xlabel("Subsoil Model", fontsize=10, fontweight="bold")
        ax.set_ylabel("Embankment Type", fontsize=10, fontweight="bold")
        ax.set_title(_STRIP_LABELS[case], fontsize=12, fontweight="bold")

        # Replace column labels with subsoil labels
        col_labels = [_SUBSOIL_LABELS.get(s, f"S{s}") for s in pivot_data.columns]
        ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=8)

        # Replace row labels with embankment labels
        row_labels = [emb_labels.get(e, f"E{e}") for e in pivot_data.index]
        ax.set_yticklabels(row_labels, rotation=0, fontsize=8)

    # Add colorbar with zone labels
    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    cb = plt.colorbar(
        plt.cm.ScalarMappable(cmap=cmap, norm=norm),
        cax=cbar_ax,
        boundaries=boundaries,
        ticks=[0.7, 1.025, 1.075, 1.35],
        spacing="proportional",
    )
    cb.ax.set_yticklabels(["Critical\n(< 1.0)", "Marginal\n(1.0-1.05)", "Acceptable\n(1.05-1.1)", "Good\n(≥ 1.1)"], fontsize=8)
    cb.set_label("Safety Zone", fontsize=10, fontweight="bold")

    fig.suptitle(f"Factor of Safety Heatmaps ({method}, {variant})", fontsize=14, fontweight="bold", y=0.995)
    fig.tight_layout(rect=[0, 0, 0.9, 0.99])
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_subsoil_trend(out_path, method, variant="cons"):
    """Connected dot plot: subsoil progression on x-axis, FoS on y.

    Filters to E=0 (original embankment only).
    Hollow dots + dashed line  = original POP kept (P=0).
    Filled dots + solid line   = POP matched to subsoil (P=S).
    One pair of lines per case, coloured by case.
    """
    import numpy as np

    fos_col = f"FoS_{method}"
    df = _load_strip_data(fos_col)
    if df.empty:
        return

    df = df[(df["emb"] == 0) & (df["variant"] == variant)].copy()
    # Keep only standard subsoil models (excludes pernio-specific 15, 16)
    df = df[df["subsoil"].isin(_SUBSOIL_ORDER)]
    if df.empty:
        return

    x_pos = {s: i for i, s in enumerate(_SUBSOIL_ORDER)}  # {0:0, 3:1, 4:2, 5:3}

    fig, ax = plt.subplots(figsize=(7, 5))

    for case in _STRIP_CASES:
        dc = df[df["case"] == case]
        if dc.empty:
            continue
        color = _CASE_COLORS.get(case, "#333333")
        label = _STRIP_LABELS[case]

        # --- P=0 series: hollow markers, dashed line ---
        pop0 = dc[dc["pop"] == 0].sort_values("subsoil")
        if not pop0.empty:
            xs = [x_pos[s] for s in pop0["subsoil"]]
            ys = pop0["fos"].tolist()
            ax.plot(xs, ys, color=color, lw=1.4, ls="--", alpha=0.7, zorder=3)
            ax.scatter(
                xs,
                ys,
                facecolors="none",
                edgecolors=color,
                linewidths=1.6,
                marker="o",
                s=60,
                zorder=4,
                alpha=0.9,
                label=f"{label} — orig POP",
            )

        # --- P=S series: filled markers, solid line (only S in [3,4,5]) ---
        popS = dc[(dc["pop"] == dc["subsoil"]) & (dc["subsoil"] != 0)].sort_values(
            "subsoil"
        )
        if not popS.empty:
            xs = [x_pos[s] for s in popS["subsoil"]]
            ys = popS["fos"].tolist()
            ax.plot(xs, ys, color=color, lw=1.4, ls="-", alpha=0.7, zorder=3)
            ax.scatter(
                xs,
                ys,
                facecolors=color,
                edgecolors=color,
                linewidths=0.4,
                marker="o",
                s=60,
                zorder=4,
                alpha=0.9,
                label=f"{label} — matched POP",
            )

    _draw_sigma_bands(ax)
    ax.axhline(1.0, color="#c0392b", lw=1.0, ls=":", alpha=0.9, zorder=2)
    ax.set_xticks(range(len(_SUBSOIL_ORDER)))
    ax.set_xticklabels([_SUBSOIL_LABELS[s] for s in _SUBSOIL_ORDER])
    ax.set_xlabel("Subsoil model")
    ax.set_ylabel("FoS")
    title_v = "Constrained" if variant == "cons" else "Unconstrained"
    ax.set_title(
        f"Subsoil effect on FoS — {method.capitalize()} ({title_v}, original embankment)"
    )
    ax.grid(axis="y", alpha=0.25, lw=0.5)
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_subsoil_strip(
    out_path: Path,
    method: str,
    variants: tuple = ("cons", "nocons"),
    active_cases: list = None,
    active_subsoils: list = None,
    active_embs: list = None,
) -> None:
    """One figure for one FoS method.
    X axis  : subsoil groups (Original / LNA / RY4 / RY5),
              each group has 4 location clusters.
    Y axis  : FoS
    Color   : embankment type
    Shape   : filled circle = constrained, x = unconstrained
    """
    import numpy as np

    df = _load_strip_data(f"FoS_{method}")
    if df.empty:
        return

    n_locs = len(_STRIP_CASES)
    n_sub = len(_SUBSOIL_ORDER)
    group_w = n_locs + 1  # 4 location slots + 1 gap

    def xc(sub_idx, loc_idx, emb):
        jitter = (emb % 5 - 2) * 0.09
        return sub_idx * group_w + loc_idx + jitter

    title_suffix = (
        "(\u25cf constrained, \u00d7 unconstrained)"
        if len(variants) > 1
        else "(constrained only)"
    )
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle(
        f"FoS by subsoil parameter \u2014 {method}  {title_suffix}",
        fontsize=12,
        fontweight="bold",
    )

    for _, row in df.iterrows():
        if row["variant"] not in variants:
            continue
        s = row["subsoil"]
        if s not in _SUBSOIL_ORDER:
            continue
        si = _SUBSOIL_ORDER.index(s)
        case = row["case"]
        if case not in _STRIP_CASES:
            continue
        li = _STRIP_CASES.index(case)
        e = row["emb"]
        x = xc(si, li, e)
        color = _EMB_COLORS.get(e, "#000000")
        a = (
            0.55
            if (
                (active_cases is None or case in active_cases)
                and (active_subsoils is None or s in active_subsoils)
                and (active_embs is None or e in active_embs)
            )
            else 0.05
        )

        if row["variant"] == "cons":
            pop_matched = (
                row["pop"] != 0
            )  # True = POP same as subsoil, False = original
            ax.scatter(
                x,
                row["fos"],
                color=color,
                marker="o",
                s=22,
                facecolors=color if pop_matched else "none",
                edgecolors=color,
                linewidths=0.4 if pop_matched else 1.6,
                zorder=4,
                alpha=a,
            )
        else:
            ax.scatter(
                x,
                row["fos"],
                color=color,
                marker="x",
                s=22,
                linewidths=1.0,
                zorder=4,
                alpha=a,
            )

    _draw_sigma_bands(ax)
    ax.axhline(1.0, color="#c0392b", lw=1.0, ls=":", alpha=0.9, zorder=3)

    xtick_pos, xtick_labels = [], []
    for si, s in enumerate(_SUBSOIL_ORDER):
        if si > 0:
            ax.axvline(si * group_w - 0.5, color="#cccccc", lw=1.0, zorder=1)
        for li, case in enumerate(_STRIP_CASES):
            xtick_pos.append(si * group_w + li)
            xtick_labels.append(_STRIP_LABELS[case])

    ax.set_xticks(xtick_pos)
    ax.set_xticklabels(xtick_labels, rotation=40, ha="right", fontsize=8)

    for si, s in enumerate(_SUBSOIL_ORDER):
        mid_x = si * group_w + (n_locs - 1) / 2
        ax.text(
            mid_x,
            1.52,
            _SUBSOIL_LABELS[s],
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.2", fc="#f0f0f0", ec="#cccccc", lw=0.8),
        )

    ax.set_xlim(-0.8, n_sub * group_w - 1.3)
    ax.set_ylim(0.4, 1.6)
    ax.set_yticks(np.arange(0.4, 1.61, 0.1))
    ax.set_ylabel("FoS")
    ax.grid(axis="y", alpha=0.25, lw=0.5)

    present = set(df["emb"].dropna().astype(int))
    present_embs = [e for e in _EMB_LABELS if e in present]
    handles = []
    for e in present_embs:
        handles.append(
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor=_EMB_COLORS[e],
                markeredgecolor="#333333",
                markersize=7,
                linestyle="None",
                label=_EMB_LABELS[e],
            )
        )
    if "cons" in variants:
        handles.append(
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="#888",
                markeredgecolor="#888",
                markersize=7,
                linestyle="None",
                label="Cons, POP replaced",
            )
        )
        handles.append(
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="none",
                markeredgecolor="#888",
                markersize=7,
                linestyle="None",
                label="Cons, POP original",
            )
        )
    if "nocons" in variants:
        handles.append(
            plt.Line2D(
                [0],
                [0],
                marker="x",
                color="#555",
                markersize=7,
                linestyle="None",
                label="Unconstrained",
            )
        )
    handles.append(
        plt.Line2D([0], [0], color="#c0392b", lw=1.0, ls=":", label="FoS = 1.0")
    )
    ax.legend(
        handles=handles,
        fontsize=7,
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        framealpha=0.85,
        title="Embankment",
        title_fontsize=8,
    )

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_combined(out_path: Path) -> None:
    """One subplot per (case, method) pair.
    Circle (o) = constrained, X = unconstrained. Color = sub-run depth.
    Baseline shown as a dashed horizontal line (cons value only).
    Layout: 2 columns, N rows.
    """
    import numpy as np

    # Build ordered panel list: (case_name, method) — skip bergambacht (v1), use v2
    # Order: for each case in CASES order, for each method alphabetically
    panels = []
    for name in CASES:
        if name == "bergambacht":
            continue
        p = PROJECT_ROOT / "baseline_models" / f"{name}_runs.xlsx"
        if not p.exists():
            continue
        df_header = pd.read_excel(p, sheet_name="results", nrows=0)
        methods = sorted(
            c[len("FoS_") :] for c in df_header.columns if c.startswith("FoS_")
        )
        for method in methods:
            panels.append((name, method))

    n = len(panels)
    ncols = 2
    nrows = (n + 1) // ncols

    # Size: width driven by the widest panel's run count
    run_counts = []
    for name, method in panels:
        df = load_for_method(name, f"FoS_{method}")
        run_counts.append(len(df[df["run_id"] != "baseline"]))
    max_runs = max(run_counts) if run_counts else 1
    panel_w = max(7, max_runs * 0.5)
    panel_h = 5

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(ncols * panel_w, nrows * panel_h),
        gridspec_kw={"wspace": 0.45, "hspace": 0.45},
    )
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
    fig.suptitle(
        "Factor of Safety  (\u25cf constrained,  \u00d7 unconstrained)",
        fontsize=13,
        fontweight="bold",
        y=1.01,
    )

    for ax_idx, (name, method) in enumerate(panels):
        ax = axes_flat[ax_idx]
        df = load_for_method(name, f"FoS_{method}")
        case_df = df[df["run_id"] != "baseline"].set_index("run_id")

        run_ids = sorted(case_df.index.tolist(), key=_run_sort_key)

        for xi, rid in enumerate(run_ids):
            color, _ = run_style(rid, name)
            y_cons = (
                case_df.loc[rid, "cons"] if "cons" in case_df.columns else float("nan")
            )
            y_nocons = (
                case_df.loc[rid, "nocons"]
                if "nocons" in case_df.columns
                else float("nan")
            )
            if pd.notna(y_cons):
                ax.scatter(
                    xi,
                    y_cons,
                    color=color,
                    marker="o",
                    s=70,
                    edgecolors="#333333",
                    linewidths=0.5,
                    zorder=4,
                )
            if pd.notna(y_nocons):
                ax.scatter(
                    xi,
                    y_nocons,
                    color=color,
                    marker="x",
                    s=70,
                    linewidths=1.5,
                    zorder=4,
                )

        # Baseline: cons dashed line
        if bool(df["has_baseline"].values[0]) and "cons" in df.columns:
            bl_rows = df.loc[df["run_id"] == "baseline", "cons"]
            if len(bl_rows) > 0 and pd.notna(bl_rows.values[0]):
                ax.axhline(
                    float(bl_rows.values[0]),
                    color=CASES[name]["colors"][-1],
                    lw=1.3,
                    ls="--",
                    alpha=0.75,
                    zorder=2,
                )

        _draw_sigma_bands(ax)
        ax.axhline(1.0, color="#c0392b", lw=0.9, ls=":", alpha=0.85, zorder=3)
        ax.set_xticks(list(range(len(run_ids))))
        ax.set_xticklabels(run_ids, rotation=45, ha="right", fontsize=8)
        ax.tick_params(axis="x", pad=8)
        ax.set_title(
            f"{CASES[name]['label']} \u2014 {method}", fontsize=11, fontweight="bold"
        )
        ax.set_ylabel("FoS")
        ax.grid(axis="y", alpha=0.3, lw=0.5)
        ax.set_xlim(-0.5, len(run_ids) - 0.5)
        ax.set_ylim(0.4, 1.4)
        ax.set_yticks(np.arange(0.4, 1.41, 0.1))

        handles = [
            plt.Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="#555",
                markeredgecolor="#333",
                markersize=8,
                linestyle="None",
                label="Constrained",
            ),
            plt.Line2D(
                [0],
                [0],
                marker="x",
                color="#555",
                markersize=8,
                linestyle="None",
                label="Unconstrained",
            ),
            plt.Line2D(
                [0],
                [0],
                color=CASES[name]["colors"][-1],
                lw=1.3,
                ls="--",
                label="Baseline (cons)",
            ),
            plt.Line2D([0], [0], color="#c0392b", lw=0.9, ls=":", label="FoS = 1.0"),
        ]
        ax.legend(
            handles=handles,
            fontsize=7,
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
            borderaxespad=0,
            framealpha=0.85,
        )

    # Hide unused axes
    for j in range(ax_idx + 1, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_pct_change(dfs: dict, out_path: Path) -> None:
    """2 subplots (cons / nocons): % change from baseline (all cases).
    Cases without a true baseline use FoS=1.0 as the reference value.
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 11), gridspec_kw={"hspace": 0.6})
    fig.suptitle(
        "% Change in FoS from Baseline  (* Pernio: % from FoS=1.0)",
        fontsize=13,
        fontweight="bold",
    )

    draw_pct_combined_ax(axes[0], dfs, "cons", "Constrained")
    draw_pct_combined_ax(axes[1], dfs, "nocons", "Unconstrained")

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _cases_for_method(method: str) -> list:
    """Return _STRIP_CASES that have FoS_{method} data."""
    result = []
    for name in _STRIP_CASES:
        p = PROJECT_ROOT / "baseline_models" / f"{name}_runs.xlsx"
        if not p.exists():
            continue
        df_h = pd.read_excel(p, sheet_name="results", nrows=0)
        if f"FoS_{method}" in df_h.columns:
            result.append(name)
    return result


def _subplot_grid(n: int) -> tuple:
    """Return (nrows, ncols) for n subplots, roughly square."""
    import math

    ncols = math.ceil(math.sqrt(n))
    nrows = math.ceil(n / ncols)
    return nrows, ncols


def plot_deviation_strip(out_path: Path, method: str) -> None:
    """Strip plot of FoS − 1.0 (deviation from reality). Constrained only.
    Positive = unconservative, negative = conservative (consistent with failure).
    Color = embankment type. Fill = POP state.
    """
    import numpy as np

    df = _load_strip_data(f"FoS_{method}")
    df = df[df["variant"] == "cons"].copy()
    if df.empty:
        return

    n_locs = len(_STRIP_CASES)
    n_sub = len(_SUBSOIL_ORDER)
    group_w = n_locs + 1

    def xc(sub_idx, loc_idx, emb):
        return sub_idx * group_w + loc_idx + (emb % 5 - 2) * 0.09

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle(
        f"FoS deviation from 1.0 — {method}  (constrained | positive = unconservative)",
        fontsize=12,
        fontweight="bold",
    )

    for _, row in df.iterrows():
        s = row["subsoil"]
        if s not in _SUBSOIL_ORDER:
            continue
        si = _SUBSOIL_ORDER.index(s)
        case = row["case"]
        if case not in _STRIP_CASES:
            continue
        li = _STRIP_CASES.index(case)
        e = row["emb"]
        x = xc(si, li, e)
        color = _EMB_COLORS.get(e, "#000000")
        pop_matched = row["pop"] != 0
        dev = row["fos"] - 1.0
        ax.scatter(
            x,
            dev,
            marker="o",
            s=22,
            facecolors=color if pop_matched else "none",
            edgecolors=color,
            linewidths=0.4 if pop_matched else 1.6,
            zorder=4,
            alpha=0.55,
        )

    _draw_sigma_bands(ax, center=0.0)
    ax.axhline(0.0, color="#c0392b", lw=1.2, ls=":", alpha=0.9, zorder=3)
    ax.axhspan(-0.65, 0.0, alpha=0.04, color="#2196f3", zorder=0)

    xtick_pos, xtick_labels = [], []
    for si, s in enumerate(_SUBSOIL_ORDER):
        if si > 0:
            ax.axvline(si * group_w - 0.5, color="#cccccc", lw=1.0, zorder=1)
        for li, case in enumerate(_STRIP_CASES):
            xtick_pos.append(si * group_w + li)
            xtick_labels.append(_STRIP_LABELS[case])

    ax.set_xticks(xtick_pos)
    ax.set_xticklabels(xtick_labels, rotation=40, ha="right", fontsize=8)

    for si, s in enumerate(_SUBSOIL_ORDER):
        mid_x = si * group_w + (n_locs - 1) / 2
        ax.text(
            mid_x,
            0.54,
            _SUBSOIL_LABELS[s],
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.2", fc="#f0f0f0", ec="#cccccc", lw=0.8),
        )

    ax.set_xlim(-0.8, n_sub * group_w - 1.3)
    ax.set_ylim(-0.65, 0.65)
    ax.set_yticks(np.arange(-0.6, 0.61, 0.1))
    ax.set_ylabel("FoS − 1.0")
    ax.grid(axis="y", alpha=0.25, lw=0.5)

    present_embs = sorted(df["emb"].unique())
    handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=_EMB_COLORS[e],
            markeredgecolor="#333",
            markersize=7,
            linestyle="None",
            label=_EMB_LABELS[e],
        )
        for e in present_embs
    ]
    handles += [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#888",
            markeredgecolor="#888",
            markersize=7,
            linestyle="None",
            label="POP replaced",
        ),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="none",
            markeredgecolor="#888",
            markersize=7,
            linestyle="None",
            label="POP original",
        ),
        plt.Line2D([0], [0], color="#c0392b", lw=1.2, ls=":", label="FoS = 1.0"),
    ]
    ax.legend(
        handles=handles,
        fontsize=7,
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        framealpha=0.85,
        title="Embankment",
        title_fontsize=8,
    )

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_emb_sensitivity(out_path: Path, method: str) -> None:
    """Per-case subplot: x=subsoil, grey range bar (min–max across all E),
    individual points colored by embankment family. Constrained only.
    Shows how much embankment choice affects FoS at each subsoil level.
    """
    import numpy as np

    df = _load_strip_data(f"FoS_{method}")
    df = df[df["variant"] == "cons"].copy()
    if df.empty:
        return
    df["family"] = df["emb"].map(_EMB_TO_FAMILY)

    cases = _cases_for_method(method)
    if not cases:
        return

    nrows, ncols = _subplot_grid(len(cases))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(4.5 * ncols, 4.2 * nrows), squeeze=False, sharey=True
    )
    fig.suptitle(
        f"Embankment sensitivity — {method} (constrained)",
        fontsize=12,
        fontweight="bold",
    )

    x_pos = {s: i for i, s in enumerate(_SUBSOIL_ORDER)}
    for idx, case in enumerate(cases):
        ax = axes[idx // ncols][idx % ncols]
        dc = df[df["case"] == case]
        for s in _SUBSOIL_ORDER:
            ds = dc[dc["subsoil"] == s]
            if ds.empty:
                continue
            xi = x_pos[s]
            ax.vlines(
                xi,
                ds["fos"].min(),
                ds["fos"].max(),
                color="#cccccc",
                lw=5,
                zorder=2,
                alpha=0.9,
            )
            for _, row in ds.iterrows():
                fam = _EMB_TO_FAMILY.get(row["emb"], "Original")
                fc = _FAMILY_COLORS[fam]
                pop_matched = row["pop"] != 0
                ax.scatter(
                    xi,
                    row["fos"],
                    marker="o",
                    s=30,
                    facecolors=fc if pop_matched else "none",
                    edgecolors=fc,
                    linewidths=0.4 if pop_matched else 1.6,
                    zorder=4,
                    alpha=0.75,
                )

        _draw_sigma_bands(ax)
        ax.axhline(1.0, color="#c0392b", lw=1.0, ls=":", alpha=0.9, zorder=3)
        ax.set_xticks(range(len(_SUBSOIL_ORDER)))
        ax.set_xticklabels([_SUBSOIL_LABELS[s] for s in _SUBSOIL_ORDER])
        ax.set_title(_STRIP_LABELS[case], fontsize=10)
        ax.set_ylim(0.4, 1.6)
        ax.set_yticks(np.arange(0.4, 1.61, 0.2))
        ax.grid(axis="y", alpha=0.25, lw=0.5)
        if idx % ncols == 0:
            ax.set_ylabel("FoS")

    for j in range(len(cases), nrows * ncols):
        axes[j // ncols][j % ncols].set_visible(False)

    handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=_FAMILY_COLORS[fam],
            markeredgecolor=_FAMILY_COLORS[fam],
            markersize=7,
            linestyle="None",
            label=fam,
        )
        for fam in _EMB_FAMILIES
    ]
    handles += [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#888",
            markeredgecolor="#888",
            markersize=7,
            linestyle="None",
            label="POP replaced",
        ),
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="none",
            markeredgecolor="#888",
            markersize=7,
            linestyle="None",
            label="POP original",
        ),
        plt.Line2D([0], [0], color="#c0392b", lw=1.0, ls=":", label="FoS = 1.0"),
    ]
    fig.legend(
        handles=handles,
        fontsize=8,
        loc="lower center",
        ncol=4,
        bbox_to_anchor=(0.5, -0.04),
        framealpha=0.85,
    )
    fig.tight_layout(rect=[0, 0.07, 1, 1])
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_emb_family_bands(out_path: Path, method: str) -> None:
    """Per-case subplot: x=subsoil, colored line+shaded band per embankment family.
    Line = median FoS across family members at each subsoil level.
    Band = min–max range within the family. Constrained only.
    Directly compares CPT-derived vs lab-derived embankment approaches.
    """
    import numpy as np

    df = _load_strip_data(f"FoS_{method}")
    df = df[df["variant"] == "cons"].copy()
    if df.empty:
        return
    df["family"] = df["emb"].map(_EMB_TO_FAMILY)

    cases = _cases_for_method(method)
    if not cases:
        return

    nrows, ncols = _subplot_grid(len(cases))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(4.5 * ncols, 4.2 * nrows), squeeze=False, sharey=True
    )
    fig.suptitle(
        f"Embankment family FoS bands — {method} (constrained)",
        fontsize=12,
        fontweight="bold",
    )

    xvals = list(range(len(_SUBSOIL_ORDER)))
    for idx, case in enumerate(cases):
        ax = axes[idx // ncols][idx % ncols]
        dc = df[df["case"] == case]
        for fam in _EMB_FAMILIES:
            color = _FAMILY_COLORS[fam]
            df_fam = dc[dc["family"] == fam]
            xs_valid, medians, mins, maxs = [], [], [], []
            for i, s in enumerate(_SUBSOIL_ORDER):
                vals = df_fam[df_fam["subsoil"] == s]["fos"]
                if vals.empty:
                    continue
                xs_valid.append(i)
                medians.append(float(vals.median()))
                mins.append(float(vals.min()))
                maxs.append(float(vals.max()))
            if not xs_valid:
                continue
            ax.fill_between(xs_valid, mins, maxs, color=color, alpha=0.18, zorder=2)
            ax.plot(
                xs_valid,
                medians,
                color=color,
                lw=1.8,
                marker="o",
                markersize=5,
                zorder=3,
                label=fam,
                alpha=0.9,
            )

        _draw_sigma_bands(ax)
        ax.axhline(1.0, color="#c0392b", lw=1.0, ls=":", alpha=0.9, zorder=4)
        ax.set_xticks(xvals)
        ax.set_xticklabels([_SUBSOIL_LABELS[s] for s in _SUBSOIL_ORDER])
        ax.set_title(_STRIP_LABELS[case], fontsize=10)
        ax.set_ylim(0.4, 1.6)
        ax.set_yticks(np.arange(0.4, 1.61, 0.2))
        ax.grid(axis="y", alpha=0.25, lw=0.5)
        if idx % ncols == 0:
            ax.set_ylabel("FoS")

    for j in range(len(cases), nrows * ncols):
        axes[j // ncols][j % ncols].set_visible(False)

    handles = [
        plt.Line2D([0], [0], color=_FAMILY_COLORS[fam], lw=2, label=fam)
        for fam in _EMB_FAMILIES
    ]
    handles.append(
        plt.Line2D([0], [0], color="#c0392b", lw=1.0, ls=":", label="FoS = 1.0")
    )
    fig.legend(
        handles=handles,
        fontsize=8,
        loc="lower center",
        ncol=3,
        bbox_to_anchor=(0.5, -0.04),
        framealpha=0.85,
    )
    fig.tight_layout(rect=[0, 0.07, 1, 1])
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path.name}")


def plot_cpt_gain(out_path: Path, method: str) -> None:
    """ΔFoS relative to Original embankment for Eemdijk and IJkdijk.
    Two subplots side by side. X = subsoil. One line per CPT family
    (median of E variants) with a shaded min–max band. Constrained, POP=0 only.
    """
    import numpy as np

    _CPT_GROUPS = {
        "CPT Davis": ([6, 7], _FAMILY_COLORS["CPT Davis"]),
        "CPT Tan-phi": ([8, 9], _FAMILY_COLORS["CPT Tan-phi"]),
    }
    _TARGET_CASES = ["eemdijk", "ijkdijk"]

    df = _load_strip_data(f"FoS_{method}")
    df = df[(df["variant"] == "cons") & (df["pop"] == 0)].copy()
    if df.empty:
        return

    cases = [c for c in _TARGET_CASES if c in df["case"].unique()]
    if not cases:
        return

    fig, axes = plt.subplots(
        1, len(cases), figsize=(4.5 * len(cases), 4.2), squeeze=False, sharey=True
    )
    fig.suptitle(
        f"CPT embankment gain — {method} (constrained, original POP)\n"
        f"ΔFoS = FoS(CPT) − FoS(Original embankment)",
        fontsize=11,
        fontweight="bold",
    )

    xvals = list(range(len(_SUBSOIL_ORDER)))
    xlabels = [_SUBSOIL_LABELS[s] for s in _SUBSOIL_ORDER]

    print(f"\n  CPT gain summary — {method}")
    print(
        f"  {'Case':<14} {'Subsoil':<10} {'Family':<14} {'min':>7} {'median':>7} {'max':>7}"
    )

    for col, case in enumerate(cases):
        ax = axes[0][col]
        dc = df[df["case"] == case]

        for fam_name, (embs, color) in _CPT_GROUPS.items():
            xs, medians, mins, maxs = [], [], [], []
            for i, s in enumerate(_SUBSOIL_ORDER):
                base = dc[(dc["subsoil"] == s) & (dc["emb"] == 0)]["fos"]
                if base.empty:
                    continue
                fos_base = base.iloc[0]
                deltas = []
                for e in embs:
                    row = dc[(dc["subsoil"] == s) & (dc["emb"] == e)]["fos"]
                    if not row.empty:
                        deltas.append(row.iloc[0] - fos_base)
                if not deltas:
                    continue
                xs.append(i)
                medians.append(float(np.median(deltas)))
                mins.append(min(deltas))
                maxs.append(max(deltas))
                print(
                    f"  {_STRIP_LABELS[case]:<14} {_SUBSOIL_LABELS[s]:<10} "
                    f"{fam_name:<14} {min(deltas):+.3f}  {float(np.median(deltas)):+.3f}  {max(deltas):+.3f}"
                )

            if not xs:
                continue
            ax.fill_between(xs, mins, maxs, color=color, alpha=0.2, zorder=2)
            ax.plot(
                xs,
                medians,
                color=color,
                lw=2.0,
                marker="o",
                markersize=6,
                zorder=3,
                label=fam_name,
            )

        _draw_sigma_bands(ax, center=0.0)
        ax.axhline(0.0, color="#c0392b", lw=1.0, ls=":", alpha=0.9, zorder=4)
        ax.set_xticks(xvals)
        ax.set_xticklabels(xlabels)
        ax.set_title(_STRIP_LABELS[case], fontsize=11)
        ax.grid(axis="y", alpha=0.3, lw=0.5)
        if col == 0:
            ax.set_ylabel("ΔFoS  (CPT − Original emb)")

    # Symmetric y-axis around 0
    ymax = max(abs(lim) for ax in axes[0] for lim in ax.get_ylim())
    ymax = max(ymax, 0.1)
    for ax in axes[0]:
        ax.set_ylim(-ymax * 0.15, ymax * 1.15)

    handles = [
        plt.Line2D([0], [0], color=c, lw=2, label=f)
        for f, (_, c) in _CPT_GROUPS.items()
    ]
    handles.append(
        plt.Line2D([0], [0], color="#c0392b", lw=1.0, ls=":", label="ΔFoS = 0")
    )
    fig.legend(
        handles=handles,
        fontsize=9,
        loc="lower center",
        ncol=3,
        bbox_to_anchor=(0.5, -0.04),
        framealpha=0.85,
    )
    fig.tight_layout(rect=[0, 0.1, 1, 1])
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Saved: {out_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("Loading data...")
    # Only load cases whose Excel files actually exist
    dfs = {
        name: load_combined(name)
        for name in CASES
        if (PROJECT_ROOT / "baseline_models" / f"{name}_runs.xlsx").exists()
    }

    plots_dir = PROJECT_ROOT / "plots"
    plots_dir.mkdir(exist_ok=True)

    print("Plotting...")  # New strip plot (grouped by subsoil, all locations)
    _SAND_EMBS = [0, 6, 7, 8, 9]
    _EEM_IJK_CASES = ["eemdijk", "ijkdijk"]
    _EEM_IJK_SOILS = [
        0,
        4,
        5,
        10,
        11,
        13,
        14,
    ]  # Original, RY4, RY5, RY5.avg, RY5.caut — LNA dimmed

    for method in _strip_methods():
        # --- plot_strip (subsoil groups, case clusters) ---
        plot_subsoil_strip(plots_dir / f"plot_strip_{method}.png", method)
        plot_subsoil_strip(
            plots_dir / f"plot_strip_{method}_cons.png", method, variants=("cons",)
        )
        plot_subsoil_strip(
            plots_dir / f"plot_strip_{method}_cons_orig_emb.png",
            method,
            variants=("cons",),
            active_embs=[0],
        )
        plot_subsoil_strip(
            plots_dir / f"plot_strip_{method}_cons_sand_strength.png",
            method,
            variants=("cons",),
            active_embs=_SAND_EMBS,
        )
        if method == "upliftvan":
            plot_subsoil_strip(
                plots_dir / "plot_strip_upliftvan_cons_eem_ijk.png",
                method,
                variants=("cons",),
                active_cases=_EEM_IJK_CASES,
                active_subsoils=_EEM_IJK_SOILS,
            )

        # --- plot_casestrip (case groups, subsoil clusters) ---
        plot_case_strip(plots_dir / f"plot_casestrip_{method}.png", method)
        plot_case_strip(
            plots_dir / f"plot_casestrip_{method}_cons.png", method, variants=("cons",)
        )
        plot_case_strip(
            plots_dir / f"plot_casestrip_{method}_cons_orig_emb.png",
            method,
            variants=("cons",),
            active_embs=[0],
        )
        plot_case_strip(
            plots_dir / f"plot_casestrip_{method}_cons_sand_strength.png",
            method,
            variants=("cons",),
            active_embs=_SAND_EMBS,
        )
        if method == "upliftvan":
            plot_case_strip(
                plots_dir / "plot_casestrip_upliftvan_cons_eem_ijk.png",
                method,
                variants=("cons",),
                active_cases=_EEM_IJK_CASES,
                active_subsoils=_EEM_IJK_SOILS,
            )
            # Simplified: selected subsoils, no Original/RY4 emb, POP replaced only
            plot_case_strip(
                plots_dir / "plot_casestrip_upliftvan_cons_simplified.png",
                method,
                variants=("cons",),
                filter_subsoils=[3, 10, 13, 11, 14],
                filter_embs=[1, 2, 3, 6, 7, 8, 9, 10, 13, 11, 14],
                pop_replaced_only=True,
            )
            # Heatmap: FoS for all embankment×subsoil combos per case
            plot_fos_heatmaps(
                plots_dir / "plot_fos_heatmaps_upliftvan_cons.png", method, variant="cons"
            )
        # Focused subsoil trend plot (E=0, both POP variants)
        plot_subsoil_trend(plots_dir / f"plot_subsoil_trend_{method}.png", method)
        # Deviation from FoS=1.0 strip
        plot_deviation_strip(plots_dir / f"plot_deviation_{method}.png", method)
        # Embankment sensitivity (range bars per subsoil, per case)
        plot_emb_sensitivity(plots_dir / f"plot_emb_sensitivity_{method}.png", method)
        # Embankment family bands (CPT vs lab comparison)
        plot_emb_family_bands(plots_dir / f"plot_emb_families_{method}.png", method)
        # CPT gain over Original embankment
        plot_cpt_gain(plots_dir / f"plot_cpt_gain_{method}.png", method)
    # Combined cons+nocons plot (one subplot per FoS method)
    plot_combined(plots_dir / "plot_fos_combined.png")

    # % change from baseline (bergambacht v1 excluded, using v2 instead)
    dfs_orig = {k: v for k, v in dfs.items() if k != "bergambacht"}
    plot_pct_change(dfs_orig, plots_dir / "plot_pct_change.png")

    # Bergambacht v1 vs v2 comparison (only if v1 file is still present)
    if "bergambacht" in dfs and "bergambacht_v2" in dfs:
        plot_bergambacht_compare(
            dfs["bergambacht"],
            dfs["bergambacht_v2"],
            plots_dir / "plot_bergambacht_compare.png",
        )

    print("\nDone. 3 plots written to plots/.")


if __name__ == "__main__":
    main()
