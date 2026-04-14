"""
Compare Backcalculation Attempts

This script reads attempts_tracking.xlsx and generates visualizations
comparing Factor of Safety across different attempts and cross-sections.

Usage:
    python compare_attempts.py
"""

import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Add source to path
sys.path.insert(0, str(Path(__file__).parent))


def load_tracking_data(tracking_file: Path) -> pd.DataFrame:
    """Load the attempts tracking table"""
    if not tracking_file.exists():
        print(f"ERROR: Tracking file not found: {tracking_file}")
        print("Run some attempts first using run_attempt.py")
        sys.exit(1)

    return pd.read_excel(tracking_file)


def plot_fos_comparison(df: pd.DataFrame, output_folder: Path):
    """
    Create bar chart comparing FoS across attempts for each cross-section

    Args:
        df: Tracking dataframe
        output_folder: Where to save plots
    """
    # Find FoS columns (start with "FoS_")
    fos_cols = [col for col in df.columns if col.startswith("FoS_") and col != "FoS"]

    if not fos_cols:
        print("No FoS data found in tracking table")
        return

    # Extract cross-section names
    xs_names = [col.replace("FoS_", "") for col in fos_cols]

    # Create grouped bar chart
    fig = go.Figure()

    for idx, row in df.iterrows():
        attempt_name = row["Attempt"]
        fos_values = [row[col] for col in fos_cols]

        fig.add_trace(
            go.Bar(
                name=attempt_name,
                x=xs_names,
                y=fos_values,
                text=[f"{v:.3f}" if pd.notna(v) else "N/A" for v in fos_values],
                textposition="outside",
            )
        )

    fig.update_layout(
        title="Factor of Safety Comparison Across Attempts",
        xaxis_title="Cross Section",
        yaxis_title="Factor of Safety",
        barmode="group",
        font=dict(size=14),
        height=600,
        width=1200,
        legend=dict(orientation="v", yanchor="top", y=0.99, xanchor="right", x=0.99),
    )

    # Add reference line at FoS = 1.0
    fig.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="red",
        annotation_text="FoS = 1.0 (Limit)",
        annotation_position="right",
    )

    # Save
    output_file = output_folder / "fos_comparison_by_cross_section.html"
    fig.write_html(output_file)
    print(f"✓ Saved: {output_file}")

    return fig


def plot_average_fos_trend(df: pd.DataFrame, output_folder: Path):
    """
    Create line plot showing average FoS trend across attempts

    Args:
        df: Tracking dataframe
        output_folder: Where to save plots
    """
    if "Avg_FoS" not in df.columns:
        print("No average FoS data found")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Attempt"],
            y=df["Avg_FoS"],
            mode="lines+markers+text",
            text=[f"{v:.3f}" for v in df["Avg_FoS"]],
            textposition="top center",
            marker=dict(size=12, color="blue"),
            line=dict(width=3),
        )
    )

    fig.update_layout(
        title="Average Factor of Safety Trend Across Attempts",
        xaxis_title="Attempt",
        yaxis_title="Average FoS",
        font=dict(size=14),
        height=500,
        width=1000,
    )

    # Add reference line
    if len(df) > 0:
        baseline_fos = df.iloc[0]["Avg_FoS"]
        fig.add_hline(
            y=baseline_fos,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Baseline ({baseline_fos:.3f})",
            annotation_position="right",
        )

    # Save
    output_file = output_folder / "average_fos_trend.html"
    fig.write_html(output_file)
    print(f"✓ Saved: {output_file}")

    return fig


def plot_delta_from_baseline(df: pd.DataFrame, output_folder: Path):
    """
    Create heatmap showing change in FoS relative to baseline

    Args:
        df: Tracking dataframe
        output_folder: Where to save plots
    """
    # Find FoS columns
    fos_cols = [col for col in df.columns if col.startswith("FoS_") and col != "FoS"]

    if len(df) < 2 or not fos_cols:
        print("Need at least 2 attempts to calculate deltas")
        return

    # Get baseline (first row)
    baseline = df.iloc[0]

    # Calculate deltas
    delta_data = []
    xs_names = [col.replace("FoS_", "") for col in fos_cols]

    for idx, row in df.iloc[1:].iterrows():  # Skip baseline
        attempt_name = row["Attempt"]
        deltas = []
        for col in fos_cols:
            if pd.notna(row[col]) and pd.notna(baseline[col]):
                delta = row[col] - baseline[col]
                deltas.append(delta)
            else:
                deltas.append(None)
        delta_data.append(deltas)

    # Create heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=delta_data,
            x=xs_names,
            y=df.iloc[1:]["Attempt"].tolist(),
            text=[
                [f"{v:+.3f}" if v is not None else "N/A" for v in row]
                for row in delta_data
            ],
            texttemplate="%{text}",
            textfont={"size": 12},
            colorscale="RdYlGn",
            zmid=0,
            colorbar=dict(title="ΔFoS"),
        )
    )

    fig.update_layout(
        title="Change in FoS Relative to Baseline",
        xaxis_title="Cross Section",
        yaxis_title="Attempt",
        font=dict(size=14),
        height=400 + len(df) * 30,
        width=1000,
    )

    # Save
    output_file = output_folder / "delta_from_baseline_heatmap.html"
    fig.write_html(output_file)
    print(f"✓ Saved: {output_file}")

    return fig


def create_summary_report(df: pd.DataFrame, output_folder: Path):
    """
    Create a text summary report

    Args:
        df: Tracking dataframe
        output_folder: Where to save report
    """
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("BACKCALCULATION ATTEMPTS SUMMARY REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"\nTotal Attempts: {len(df)}")
    report_lines.append(
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    report_lines.append("\n" + "-" * 70)

    # Find FoS columns
    fos_cols = [col for col in df.columns if col.startswith("FoS_") and col != "FoS"]

    for idx, row in df.iterrows():
        report_lines.append(f"\n{'='*70}")
        report_lines.append(f"Attempt: {row['Attempt']}")
        report_lines.append(f"Description: {row['Description']}")
        report_lines.append(f"Timestamp: {row['Timestamp']}")
        report_lines.append(f"{'-'*70}")

        # FoS results
        report_lines.append("Factor of Safety Results:")
        for col in fos_cols:
            xs_name = col.replace("FoS_", "")
            fos_val = row[col]
            if pd.notna(fos_val):
                report_lines.append(f"  {xs_name:30s}: {fos_val:.3f}")
            else:
                report_lines.append(f"  {xs_name:30s}: N/A")

        if "Avg_FoS" in row and pd.notna(row["Avg_FoS"]):
            report_lines.append(f"  {'Average':30s}: {row['Avg_FoS']:.3f}")

        # Calculate delta from baseline if not baseline
        if idx > 0 and "Avg_FoS" in df.columns:
            baseline_avg = df.iloc[0]["Avg_FoS"]
            if pd.notna(row["Avg_FoS"]) and pd.notna(baseline_avg):
                delta = row["Avg_FoS"] - baseline_avg
                report_lines.append(f"  {'Delta from Baseline':30s}: {delta:+.3f}")

    # Save report
    report_file = output_folder / "summary_report.txt"
    with open(report_file, "w") as f:
        f.write("\n".join(report_lines))

    print(f"✓ Saved: {report_file}")

    # Also print to console
    print("\n" + "\n".join(report_lines))


def main():
    """Main execution"""
    project_root = Path(__file__).parent
    tracking_file = project_root / "attempts_tracking.xlsx"
    output_folder = project_root / "results" / "plots"
    output_folder.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("COMPARING BACKCALCULATION ATTEMPTS")
    print("=" * 70)

    # Load data
    df = load_tracking_data(tracking_file)
    print(f"\nLoaded {len(df)} attempts from tracking table")

    # Generate plots
    print("\nGenerating visualizations...")
    plot_fos_comparison(df, output_folder)
    plot_average_fos_trend(df, output_folder)
    plot_delta_from_baseline(df, output_folder)

    # Generate summary report
    print("\nGenerating summary report...")
    create_summary_report(df, output_folder)

    print("\n" + "=" * 70)
    print("✓ Comparison complete! Check the results/plots/ folder")
    print("=" * 70)


if __name__ == "__main__":
    main()
