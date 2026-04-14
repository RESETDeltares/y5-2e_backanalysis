# Backcalculations Project

Iterative backcalculation workflow for geotechnical slope stability analysis using D-Stability.

## 📁 Project Structure

```
backcalculations/
├── baseline_models/           # Place your 5 baseline STIX files here
├── attempts_config/           # JSON configurations for each attempt
│   ├── baseline.json
│   └── attempt_1_example.json
├── results/                   # Output folder
│   ├── baseline/              # Results for each attempt
│   ├── attempt_1/
│   └── plots/                 # Comparison visualizations
├── data/                      # Parameter tables (Excel files)
├── source/                    # Core calculation code
├── run_attempt.py            # Run a single attempt
├── compare_attempts.py       # Generate comparison plots
└── attempts_tracking.xlsx    # Master tracking table (auto-generated)
```

## 🚀 Quick Start

### 1. Setup Baseline Models

Place your 5 baseline STIX files in the `baseline_models/` folder:
```
baseline_models/
├── cross_section_1.stix
├── cross_section_2.stix
├── cross_section_3.stix
├── cross_section_4.stix
└── cross_section_5.stix
```

### 2. Install Dependencies

```bash
# Activate your Python environment
.venv\Scripts\activate

# Install required packages (already installed in calibration project)
# pip install pandas openpyxl plotly
```

### 3. Run Baseline

```bash
python run_attempt.py --config attempts_config/baseline.json
```

This will:
- Process all 5 cross-sections
- Run D-Stability calculations
- Extract Factor of Safety (FoS)
- Create `attempts_tracking.xlsx` with baseline results

### 4. Run Additional Attempts

Create a new configuration file (or copy `attempt_1_example.json`):

```json
{
  "attempt_name": "attempt_2",
  "description": "Testing drained conditions",
  "parameters": {
    "load_factor": 1.0,
    "calculation_method": "UPLIFTVAN",
    "is_drained": true,
    "drainage_modifications": true,
    "notes": "Changed to drained analysis"
  }
}
```

Run it:
```bash
python run_attempt.py --config attempts_config/attempt_2.json
```

### 5. Compare Results

Generate comparison plots and summary:
```bash
python compare_attempts.py
```

This creates:
- `results/plots/fos_comparison_by_cross_section.html` - Bar chart
- `results/plots/average_fos_trend.html` - Trend line
- `results/plots/delta_from_baseline_heatmap.html` - Change heatmap
- `results/plots/summary_report.txt` - Text summary

## 📊 Tracking Table

`attempts_tracking.xlsx` contains all attempts in one place:

| Attempt | Description | Timestamp | calc_method | is_drained | FoS_XS1 | FoS_XS2 | ... | Avg_FoS |
|---------|-------------|-----------|-------------|------------|---------|---------|-----|---------|
| baseline | Original | 2026-01-30 10:00 | UPLIFTVAN | False | 1.25 | 1.18 | ... | 1.22 |
| attempt_1 | Increased clay | 2026-01-30 10:15 | UPLIFTVAN | False | 1.30 | 1.22 | ... | 1.27 |
| attempt_2 | Drained test | 2026-01-30 10:30 | UPLIFTVAN | True | 1.35 | 1.28 | ... | 1.32 |

## ⚙️ Configuration Parameters

Available parameters in JSON config files:

### Basic Settings
- `attempt_name`: Unique identifier for this attempt
- `description`: What you're testing
- `calculation_method`: "BISHOP", "UPLIFTVAN", or "SPENCER"
- `is_drained`: true/false for drainage conditions

### Soil Modifications
```json
"soil_modifications": {
  "clay_S_factor": 1.2,      // Multiply clay S parameter by 1.2
  "clay_m_factor": 1.0,
  "clay_POP_factor": 1.0,
  "sand_phi_factor": 1.1     // Multiply sand friction angle by 1.1
}
```

### Other Options
- `drainage_modifications`: true/false - Switch to drained analysis
- `water_table_change_m`: +/- meters to adjust water table
- `load_factor`: Multiply loads by this factor

## 🔄 Typical Workflow

1. **Baseline**: Run original models, establish reference FoS
2. **Attempt 1**: Test hypothesis (e.g., increase clay strength)
3. **Compare**: Check results vs baseline
4. **Iterate**: 
   - If FoS improved: Continue refinement
   - If FoS worse: Try different approach
5. **Repeat**: Attempt 2, 3, 4... until satisfied

## 📈 Understanding Results

### Factor of Safety (FoS)
- **FoS > 1.0**: Stable (higher is safer)
- **FoS = 1.0**: Limit equilibrium
- **FoS < 1.0**: Unstable (failure)

### Comparison Metrics
- **Average FoS**: Overall performance across all cross-sections
- **Delta from Baseline**: How much did FoS change?
  - Positive delta (+): Improvement
  - Negative delta (-): Degradation

## 🛠️ Extending the Code

### Adding Custom Modifications

Edit `run_attempt.py` in the `apply_modifications()` function to add custom parameter changes:

```python
def apply_modifications(stix_data: dict, config: Dict, stix_path: Path) -> dict:
    params = config['parameters']
    
    # Your custom modifications here
    if 'custom_parameter' in params:
        # Modify STIX data based on custom_parameter
        pass
    
    return stix_data
```

### Adding New Plots

Edit `compare_attempts.py` to add custom visualizations.

## 📝 Tips

- **Name attempts descriptively**: e.g., `attempt_clay_+20pct` instead of `attempt_1`
- **Document changes**: Use the `description` and `notes` fields
- **Keep baseline intact**: Don't modify baseline models directly
- **Commit often**: If using Git, commit after each successful attempt
- **Review Excel file**: Open `attempts_tracking.xlsx` to see all results at once

## ⚠️ Troubleshooting

### "No STIX files found"
- Make sure baseline STIX files are in `baseline_models/` folder

### "D-Stability Console.exe not found"
- Update path in `source/constants/constants.py`:
  ```python
  DSTABILITY_BIN_FOLDER = r"C:\Your\Path\To\D-Stability\bin"
  ```

### "Module not found" errors
- Run from project root: `D:\codes\backcalculations>`
- Ensure Python path is correct in scripts

## 📞 Support

For questions about the workflow, refer to the original `calibration` project or contact the team.

---

**Happy Backcalculating! 🎯**
