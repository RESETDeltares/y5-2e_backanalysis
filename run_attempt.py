"""
Run Backcalculation Attempt

This script runs a single calibration attempt on all baseline cross-sections.
Results are automatically logged to attempts_tracking.xlsx for comparison.

Usage:
    1. Click Run (uses config below) or
    2. python run_attempt.py --config attempts_config/baseline.json
"""

# ============================================================================
# CONFIGURATION - Change this to run different attempts
# ============================================================================
CONFIG_FILE = "baseline.json"  # Change this to your desired config file
# ============================================================================

import json
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import Dict, Optional

# Add source to path
sys.path.insert(0, str(Path(__file__).parent))

from source.utils import read_dgs, write_dgs
from source.constants.constants import DSTABILITY_BIN_FOLDER, CalculationMethod
from source.stix_modifier import (
    modify_soil_properties_load_case,
    set_calculation_method,
)
import subprocess


def load_config(config_path: Path) -> Dict:
    """Load attempt configuration from JSON file"""
    with open(config_path, "r") as f:
        return json.load(f)


def apply_modifications(stix_data: dict, config: Dict, stix_path: Path) -> dict:
    """
    Apply parameter modifications to a STIX file based on config

    Args:
        stix_data: Loaded STIX file data
        config: Configuration dictionary with modifications
        stix_path: Path to the STIX file

    Returns:
        Modified STIX data
    """
    params = config["parameters"]

    # Set calculation method
    calc_method_map = {
        "BISHOP": CalculationMethod.BISHOP,
        "UPLIFTVAN": CalculationMethod.UPLIFTVAN,
        "SPENCER": CalculationMethod.SPENCER,
    }
    calc_method = calc_method_map.get(params.get("calculation_method", "UPLIFTVAN"))
    stix_data = set_calculation_method(stix_data, calc_method, stix_path)

    # Apply soil modifications if specified
    if "soil_modifications" in params and params["soil_modifications"]:
        # TODO: Implement soil parameter modifications
        # This would modify clay_S, clay_m, phi_sand, etc.
        # For now, pass through - you can extend this based on needs
        pass

    # Apply drainage changes
    if params.get("drainage_modifications", False):
        # Set to drained conditions
        for soil in stix_data["soils"]["Soil"]:
            if "ShearStrengthModelTypeAbovePhreaticLevel" in soil:
                soil["ShearStrengthModelTypeAbovePhreaticLevel"] = "MohrCoulomb"
                soil["ShearStrengthModelTypeBelowPhreaticLevel"] = "MohrCoulomb"

    return stix_data


def run_dstability(stix_file: Path, calc_method: str) -> float:
    """
    Run D-Stability Console and extract Factor of Safety

    Args:
        stix_file: Path to STIX file
        calc_method: Calculation method ('BISHOP' or 'UPLIFTVAN')

    Returns:
        Factor of Safety value
    """
    exepath = str(Path(DSTABILITY_BIN_FOLDER) / "D-Stability Console.exe")

    # Determine which calculation to run (1=Bishop, 2=UpliftVan)
    calc_id = "1" if calc_method == "BISHOP" else "2"

    # Run D-Stability
    subprocess.run(
        [exepath, str(stix_file), "1", calc_id], capture_output=True, check=True
    )

    # Read results
    stix_data = read_dgs(stix_file)

    # Extract FoS based on method
    if calc_method == "BISHOP":
        # result_key = "results/bishop/bishopresult"
        result_key = "results/bishopbruteforce/bishopbruteforceresult"
    else:
        #result_key = "results/upliftvan/upliftvanresult"
        result_key = "results/upliftvanparticleswarm/upliftvanparticleswarmresult"

    try:
        fos = stix_data[result_key]["FactorOfSafety"]
    except KeyError:
        # Try alternative result paths
        try:
            fos = stix_data["results/bishopbruteforce/bishopbruteforceresult"][
                "FactorOfSafety"
            ]
        except KeyError:
            fos = None

    return fos


def run_attempt(config_path: Path, baseline_folder: Path, output_folder: Path) -> Dict:
    """
    Run a complete backcalculation attempt on all models

    Args:
        config_path: Path to configuration JSON
        baseline_folder: Folder containing baseline STIX files
        output_folder: Folder to save modified STIX files

    Returns:
        Dictionary with results for each cross-section
    """
    config = load_config(config_path)
    attempt_name = config["attempt_name"]

    print(f"\n{'='*60}")
    print(f"Running Attempt: {attempt_name}")
    print(f"Description: {config['description']}")
    print(f"{'='*60}\n")

    # Create output subfolder for this attempt
    attempt_output = output_folder / attempt_name
    attempt_output.mkdir(exist_ok=True)

    results = {
        "attempt_name": attempt_name,
        "description": config["description"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "parameters": config["parameters"],
        "cross_sections": {},
    }

    # Process each baseline STIX file
    stix_files = list(baseline_folder.glob("*.stix"))

    if not stix_files:
        print(f"WARNING: No STIX files found in {baseline_folder}")
        return results

    for stix_path in stix_files:
        xs_name = stix_path.stem
        print(f"\nProcessing: {xs_name}")

        # Load baseline STIX
        stix_data = read_dgs(stix_path)

        # Apply modifications
        modified_data = apply_modifications(stix_data, config, stix_path)

        # Save modified STIX
        output_stix = attempt_output / f"{xs_name}_{attempt_name}.stix"
        write_dgs(output_stix, modified_data)
        print(f"  Saved: {output_stix.name}")

        # Run D-Stability
        print(f"  Running D-Stability...")
        calc_method = config["parameters"].get("calculation_method", "UPLIFTVAN")

        try:
            fos = run_dstability(output_stix, calc_method)
            print(f"  FoS = {fos:.3f}")
            results["cross_sections"][xs_name] = fos
        except Exception as e:
            print(f"  ERROR: {e}")
            results["cross_sections"][xs_name] = None

    return results


def log_to_tracking_table(results: Dict, tracking_file: Path):
    """
    Append results to the master tracking Excel file

    Args:
        results: Results dictionary from run_attempt
        tracking_file: Path to attempts_tracking.xlsx
    """
    # Create row data
    row_data = {
        "Attempt": results["attempt_name"],
        "Description": results["description"],
        "Timestamp": results["timestamp"],
    }

    # Add parameters as columns
    for param_key, param_val in results["parameters"].items():
        if isinstance(param_val, dict):
            # For nested dicts, flatten
            for sub_key, sub_val in param_val.items():
                row_data[f"{param_key}_{sub_key}"] = sub_val
        else:
            row_data[param_key] = param_val

    # Add FoS results for each cross-section
    for xs_name, fos in results["cross_sections"].items():
        row_data[f"FoS_{xs_name}"] = fos

    # Calculate average FoS
    fos_values = [v for v in results["cross_sections"].values() if v is not None]
    if fos_values:
        row_data["Avg_FoS"] = sum(fos_values) / len(fos_values)

    # Load or create tracking table
    if tracking_file.exists():
        df = pd.read_excel(tracking_file)
        # Append new row
        new_df = pd.DataFrame([row_data])
        df = pd.concat([df, new_df], ignore_index=True)
    else:
        # Create new table
        df = pd.DataFrame([row_data])

    # Save back to Excel
    df.to_excel(tracking_file, index=False)
    print(f"\n✓ Results logged to: {tracking_file}")


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Run backcalculation attempt")
    parser.add_argument(
        "--config", 
        type=str, 
        default=f"attempts_config/{CONFIG_FILE}",
        help=f"Path to configuration JSON file (default: {CONFIG_FILE})"
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default="baseline_models",
        help="Folder with baseline STIX files",
    )
    parser.add_argument(
        "--output", type=str, default="results", help="Output folder for results"
    )

    args = parser.parse_args()
    
    # Show which config is being used
    print("\n" + "="*70)
    print(f"  Running with config: {Path(args.config).name}")
    print("="*70 + "\n")

    # Setup paths
    project_root = Path(__file__).parent
    config_path = project_root / args.config
    baseline_folder = project_root / args.baseline
    output_folder = project_root / args.output
    tracking_file = project_root / "attempts_tracking.xlsx"

    # Validate
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    if not baseline_folder.exists():
        print(f"ERROR: Baseline folder not found: {baseline_folder}")
        print(f"Please place your baseline STIX files in: {baseline_folder}")
        sys.exit(1)

    # Create output folder
    output_folder.mkdir(exist_ok=True)

    # Run attempt
    results = run_attempt(config_path, baseline_folder, output_folder)

    # Log results
    log_to_tracking_table(results, tracking_file)

    print(f"\n{'='*60}")
    print(f"✓ Attempt '{results['attempt_name']}' completed successfully!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
