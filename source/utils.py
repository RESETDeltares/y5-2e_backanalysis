import json
import os
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from probabilistic_library import StandardNormal


def read_dgs(filename):
    r"""
    """

    stix = zipfile.ZipFile(filename)
    namelist = stix.namelist()[:]
    try:
        namelist.remove('checksum')
    except: pass
    data = {name.replace('.json' ,''): json.loads(stix.read(name).decode("utf-8")) for name in namelist}

    return data

def get_calc_settings_map(data: dict) -> dict:
    """
    Scans all calculationsettings entries in STIX data and returns a mapping
    from AnalysisType to the dict key in data.

    Example return:
      {'BishopBruteForce': 'calculationsettings/calculationsettings',
       'UpliftVanParticleSwarm': 'calculationsettings/calculationsettings_1'}
    """
    result = {}
    for key, value in data.items():
        if key.startswith('calculationsettings/'):
            analysis_type = value.get('AnalysisType')
            if analysis_type:
                result[analysis_type] = key
    return result


def write_dgs(filename: Path, data):
    """
    """

    data['projectinfo']['Path'] = str(filename)

    file = zipfile.ZipFile(filename, 'w')

    for a in data:

        with open(str(filename)[:-5 ] +'.json', 'w+') as fp:
            json.dump(data[a], fp, sort_keys=False, indent=4)
        fp.close()

        zipi= zipfile.ZipInfo()
        zipi.filename= a+ '.json'
        zipi.compress_type = zipfile.ZIP_DEFLATED
        filedata = open(str(filename)[:-5] + ".json", "rb").read()
        file.writestr(zipi, filedata)

        os.remove(str(filename)[:-5] + '.json')

        time.sleep(0.01)

    file.close()

    return



def convert_stix(stix_file: Path) -> str:
    """Convert the given stix file to the new stix format
    Args:
        stix_file : Path to the file
    Returns:
        str: The new path (we add _converted to the original name)
    """
    import subprocess
    DSTABILITY_BIN_FOLDER = r"C:\Program Files (x86)\Deltares\D-GEO Suite\D-Stability 2024.02\bin"

    exe = str(Path(DSTABILITY_BIN_FOLDER) / "D-Stability Migration Console.exe")
    subprocess.run([exe, stix_file, stix_file])
    return stix_file



def read_save_results(project, res_folder: Path):
    dp =  project.design_point
    beta = dp.reliability_index

    print(f"Beta = {beta}")

    pf = StandardNormal.get_q_from_u(beta)
    print(f"Probability of failure = {pf}")

    for alpha in dp.alphas:
        print(f"{alpha.variable.name}: alpha = {alpha.alpha}, x = {alpha.x}")

    if dp.is_converged:
        print(f"Converged (convergence = {dp.convergence} < {project.settings.variation_coefficient})")
    else:
        print(f"Not converged (convergence = {dp.convergence} > {project.settings.variation_coefficient})")

    print(f"Model runs = {dp.total_model_runs}")

    # save results in txt
    res_path = res_folder.joinpath("res" + '.txt')
    with open(res_path, 'w') as f:
        f.write(f"Beta = {beta}\n")
        f.write(f"Probability of failure = {pf}\n")
        for alpha in dp.alphas:
            f.write(f"{alpha.variable.name}: alpha = {alpha.alpha}, x = {alpha.x}\n")
        if dp.is_converged:
            f.write(f"Converged (convergence = {dp.convergence} < {project.settings.variation_coefficient})\n")
        else:
            f.write(f"Not converged (convergence = {dp.convergence} > {project.settings.variation_coefficient})\n")
        f.write(f"Model runs = {dp.total_model_runs}\n")


def get_soil_parameter_table_LNA(path: Path) -> pd.DataFrame:
    parameter_table = Path(__file__).parent.parent.joinpath("data", "ParameterTable_LNA.xlsx")


    # CREATE LOOK_UP TABLES
    Table_1 = pd.read_excel(parameter_table,
                            sheet_name='stochastic_parameters_LN',
                            skiprows=10)
    Table_2 = pd.read_excel(parameter_table,
                            sheet_name='stochastic_parameters_LN_add',
                            skiprows=10)
    Table = pd.concat([Table_1, Table_2], axis=0, ignore_index=True)
    return Table


def get_soil_code(soil: dict):
    scode = soil['Code'].lower()
    scode = scode.lower()
    scode = scode.replace('_lna', '')
    scode = scode.replace('_onder', '')
    scode = scode.replace('_naast', '')
    return scode