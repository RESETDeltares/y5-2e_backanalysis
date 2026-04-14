from typing import Optional

import pandas as pd
from pathlib import Path
import numpy as np
from geolib.soils import Soil

from source.constants.constants import CalculationMethod, SoilParameterTable, SoilGeoClassification, OnderNaast, \
    ClayAdjacentShansepParameters, \
    FibrousPeatUnderShansepParameters, FibrousPeatAdjacentShansepParameters, EmbankmentSandParameters, LoadType, \
    TrainLoadRLN
from source.constants.load_cases import LoadCase
from source.constants.locations import Location
from source.constants.safety_format import SafetyFormat, SAFETY_FORMATS_DEFAULT
from source.utils import read_dgs, get_soil_parameter_table_LNA, get_soil_code


def adjust_su_table(data, su_factor, pop=0., cut_off=0.):
    for soil in data['soils']['Soils']:

        SuTableNeeded = False

        if soil['ShearStrengthModelTypeAbovePhreaticLevel'] == ['Su']:
            soil['ShearStrengthModelTypeAbovePhreaticLevel'] = 'SuTable'
            SuTableNeeded = True
        if soil['ShearStrengthModelTypeBelowPhreaticLevel'] == ['Su']:
            soil['ShearStrengthModelTypeBelowPhreaticLevel'] = 'SuTable'
            SuTableNeeded = True
        if SuTableNeeded:
            S = soil['SuShearStrengthModel']['ShearStrengthRatio']
            m = soil['SuShearStrengthModel']['StrengthIncreaseExponent']

            sig_vp_points = np.linspace(0, 200, 101)
            # SHANSEP equation based on POP and minimum
            su_points = su_factor * sig_vp_points * S * (1 + pop / sig_vp_points) ** m
            su_points[su_points < cut_off] = cut_off

            su_table_points = [{'EffectiveStress': sig_vp, 'Su': Su} for (sig_vp, Su) in zip(sig_vp_points, su_points)]
            soil['SuTable']['SuTablePoints'] = su_table_points


def float_0(x):
    """Return a floting point number or 0 if conversion fails.
    Soil without parameters are set to 0. Example: H_Aa_z does not have S_mean and m parameters, We assign to 0.
    """
    try:
        return float(x)
    except:
        # print('*** error in "float(',x,')"')
        return float(0)


def remove_unused_soils(data: dict) -> dict:
    """Remove all the unncessary soils in the stix to avoid having too many stochastic variables"""
    layers = data['soillayers/soillayers']['SoilLayers']
    soils = data['soils']['Soils']
    soil_vis = data['soilvisualizations']['SoilVisualizations']
    nails_soil_properties = data['nailpropertiesforsoils']['NailPropertiesForSoils']

    soil_ids_in_model = set([layer['SoilId'] for layer in layers])

    soils_in_model = [soil for soil in soils if soil['Id'] in soil_ids_in_model]
    data['soils']['Soils'] = soils_in_model
    data['soilvisualizations']['SoilVisualizations'] = [soil for soil in soil_vis if
                                                        soil['SoilId'] in soil_ids_in_model]
    data['nailpropertiesforsoils']['NailPropertiesForSoils'] = [soil for soil in nails_soil_properties if
                                                                soil['SoilId'] in soil_ids_in_model]

    return data


def modify_soil_properties_load_case(data: dict,
                                     soil_parameter_type: SoilParameterTable,
                                     load_case: LoadCase,
                                     safety_format: Optional[SafetyFormat] = None,
                                     ) -> dict:
    """

    :param data: stix data
    :param table_name: Path to the soil parameters table
    :param load_case: Load Case configuration
    :return:
    """
    parameter_table = Path(__file__).parent.parent.joinpath("data", "ParameterTable_LNA.xlsx")

    # Fetch partial factors
    f_partial = safety_format

    Table = get_soil_parameter_table_LNA(parameter_table)
    TableSoils = [l.lower() for l in Table['Code']]

    for sv in data['soilvisualizations']['SoilVisualizations']:
        sv['Color'] = '#00000000'

    layers = data['soillayers/soillayers']['SoilLayers']
    soils = data['soils']['Soils']

    for layer in layers:

        soil = next(s for s in soils if s["Id"] == layer['SoilId'])
        if "onder" in soil['Code'].lower():

            onder_naast = OnderNaast.ONDER
        elif "naast" in soil['Code'].lower():
            onder_naast = OnderNaast.NAAST
        else:
            onder_naast = OnderNaast.NEITHER
        scode = get_soil_code(soil)

        I = TableSoils.index(scode)
        soil_type = Table['mapping'][I]
        CVal = load_case.CVal

        if soil_parameter_type == SoilParameterTable.TABLE_2024:
            apply_table_parameters(Table, soil, CVal, I, f_partial, load_case)
        elif soil_parameter_type == SoilParameterTable.TABLE_2025:

            gamma_d = float_0(Table['gamma_dry_' + CVal][I])
            gamma_w = float_0(Table['gamma_wet_' + CVal][I])
            soil["VolumetricWeightAbovePhreaticLevel"] = gamma_d / safety_format.gamma_weight
            soil["VolumetricWeightBelowPhreaticLevel"] = gamma_w / safety_format.gamma_weight

            SU_TABLE_path = Path(__file__).parent.parent.joinpath("data", "SU_TABLES.xlsx")
            SU_TABLE_clay = pd.read_excel(SU_TABLE_path, sheet_name='clay')
            SU_TABLE_clay_organic = pd.read_excel(SU_TABLE_path, sheet_name='organic_clay')
            SU_TABLE_clay_silty = pd.read_excel(SU_TABLE_path, sheet_name='silty_clay')

            def apply_CUSTOM_SU_TABLE(soil, table: pd.DataFrame, SU_increase_factor: float):
                soil['ShearStrengthModelTypeAbovePhreaticLevel'] = 'SuTable'
                soil['ShearStrengthModelTypeBelowPhreaticLevel'] = 'SuTable'

                su_points = table['Su_5'] * SU_increase_factor / safety_format.gamma_su  # apply partial factor and load case increase

                su_table_points = [{'EffectiveStress': sig_vp, 'Su': Su } for (sig_vp, Su) in
                                   zip(table['EffectiveStress'], su_points)]
                soil['SuTable']['SuTablePoints'] = su_table_points

            def apply_adjacent_clay_SU_TABLE(soil):
                S = ClayAdjacentShansepParameters.S_95kar
                m = ClayAdjacentShansepParameters.m_95kar
                POP = ClayAdjacentShansepParameters.POP_95kar
                cut_off = 0

                convert_shansep_to_su_table(soil, S, m, POP, cut_off=cut_off, gamma_su=f_partial.gamma_su,
                                            SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)

            if soil_type == SoilGeoClassification.TABLE.name:
                apply_table_parameters(Table, soil, CVal, I, f_partial, load_case)

            elif soil_type == SoilGeoClassification.CLAY.name:
                if onder_naast == OnderNaast.ONDER:
                    apply_CUSTOM_SU_TABLE(soil, SU_TABLE_clay,
                                          SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)

                elif onder_naast == OnderNaast.NAAST:
                    apply_adjacent_clay_SU_TABLE(soil)

            elif soil_type == SoilGeoClassification.CLAY_ORGANIC.name:
                if onder_naast == OnderNaast.ONDER:
                    apply_CUSTOM_SU_TABLE(soil, SU_TABLE_clay_organic,
                                          SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)

                elif onder_naast == OnderNaast.NAAST:
                    apply_adjacent_clay_SU_TABLE(soil)

            elif soil_type == SoilGeoClassification.SILTY_CLAY.name:
                if onder_naast == OnderNaast.ONDER:
                    apply_CUSTOM_SU_TABLE(soil, SU_TABLE_clay_silty,
                                          SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)

                elif onder_naast == OnderNaast.NAAST:
                    apply_adjacent_clay_SU_TABLE(soil)

            elif soil_type == SoilGeoClassification.FIBROUS_PEAT.name:
                if onder_naast == OnderNaast.ONDER:
                    S = FibrousPeatUnderShansepParameters.S_95kar
                    m = FibrousPeatUnderShansepParameters.m_95kar
                    POP = FibrousPeatUnderShansepParameters.POP_95kar
                    cut_off = 0

                    convert_shansep_to_su_table(soil, S, m, POP, cut_off=cut_off, gamma_su=f_partial.gamma_su,
                                                SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)


                elif onder_naast == OnderNaast.NAAST:
                    S = FibrousPeatAdjacentShansepParameters.S_95kar
                    m = FibrousPeatAdjacentShansepParameters.m_95kar
                    POP = FibrousPeatAdjacentShansepParameters.POP_95kar
                    cut_off = 0

                    convert_shansep_to_su_table(soil, S, m, POP, cut_off=cut_off, gamma_su=f_partial.gamma_su,
                                                SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)


            elif soil_type == SoilGeoClassification.EMBANKMENT_CLAY.name:
                apply_CUSTOM_SU_TABLE(soil, SU_TABLE_clay_organic,
                                      SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)
                # raise ValueError("Should not be reached, To be reconsidered")
            elif soil_type == SoilGeoClassification.EMBANKMENT_SAND.name:
                model = soil['MohrCoulombAdvancedShearStrengthModel']
                # Apply intermediate stress factor to sin(phi) then back-calculated phi
                phi = np.degrees(np.arcsin(np.sin(np.radians(
                    EmbankmentSandParameters.phi_95kar)) * load_case.intermediate_principal_stress_factor_sand / safety_format.gamma_phi))

                model['FrictionAngle'] = phi
                model['Cohesion'] = EmbankmentSandParameters.c
                model['Dilatancy'] = EmbankmentSandParameters.psi


            elif soil_type == SoilGeoClassification.CPT.name:
                print(
                    f"::: Soil {soil['Code']} is classified as CPT, no parameters are set. Soil properties from LNA are conserved.")
                continue  # do nothing and keep LNA
            else:
                raise ValueError(f"Unknown soil classification: {soil_type} {scode}")
        else:
            raise NotImplementedError(
                "Wrong parameter table type provided. Use SoilParameterTable.TABLE_2024 or SoilParameterTable.TABLE_2025")

        for sv in data['soilvisualizations']['SoilVisualizations']:
            if sv['SoilId'] == soil['Id']:
                sv['Color'] = Table['color'][I]

    return data


def apply_table_parameters(Table: pd.DataFrame, soil: Soil, CVal: str, I: int, safety_format: SafetyFormat,
                           load_case: LoadCase):
    gamma_d = float_0(Table['gamma_dry_' + CVal][I])
    gamma_w = float_0(Table['gamma_wet_' + CVal][I])
    phi = float_0(Table['phi_' + CVal][I])
    S = float_0(Table['S_' + CVal][I])
    m = float_0(Table['m_' + CVal][I])
    POP = float_0(Table['POP_' + CVal][I])

    #
    # TO BE DECIDED ON:
    # cut_off = float_0(Table['Sumin_'+CVal][I]) / f_partial['su']
    cut_off = float_0(Table['Sumin_' + CVal][I])

    phi_f = np.degrees(np.arctan(np.tan(np.radians(phi)) / safety_format.gamma_phi))
    c_eff = 0.

    soil["IsProbabilistic"] = False
    soil["VolumetricWeightAbovePhreaticLevel"] = gamma_d / safety_format.gamma_weight
    soil["VolumetricWeightBelowPhreaticLevel"] = gamma_w / safety_format.gamma_weight

    #
    # MohrCoulombClassicShearStrengthModel
    model = soil['MohrCoulombClassicShearStrengthModel']

    model['FrictionAngle'] = phi_f
    model['FrictionAngleStochasticParameter']['IsProbabilistic'] = False

    model['Cohesion'] = c_eff
    model['CohesionStochasticParameter']['IsProbabilistic'] = False

    #
    # MohrCoulombAdvancedShearStrengthModel
    model = soil['MohrCoulombAdvancedShearStrengthModel']

    model['FrictionAngle'] = phi_f
    model['FrictionAngleStochasticParameter']['IsProbabilistic'] = False

    model['Cohesion'] = c_eff
    model['CohesionStochasticParameter']['IsProbabilistic'] = False

    # SuShearStrengthModel
    convert_shansep_to_su_table(soil, S, m, POP, cut_off=cut_off, gamma_su=safety_format.gamma_su,
                                SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)

    # for sv in data['soilvisualizations']['SoilVisualizations']:
    #     if sv['SoilId'] == soil['Id']:
    #         sv['Color'] = Table['color'][I]


def apply_table_parameters_stochastic(soil, soil_code: str, load_case: LoadCase, params: dict):
    soil_params = params.get(soil_code, None)



    if soil['ShearStrengthModelTypeAbovePhreaticLevel'] == 'MohrCoulombAdvanced':
        phi = np.degrees(np.arcsin(np.sin(np.radians(soil_params['phi'])) * params[
            'inter_principal_stress_sand_effect']))
        soil['MohrCoulombAdvancedShearStrengthModel']['FrictionAngle'] = phi

    elif soil['ShearStrengthModelTypeAbovePhreaticLevel'] == 'MohrCoulombClassic':
        phi = np.degrees(np.arcsin(np.sin(np.radians(soil_params['phi'])) * params[
            'inter_principal_stress_sand_effect']))
        soil['MohrCoulombClassicShearStrengthModel']['FrictionAngle'] = phi

    elif soil['ShearStrengthModelTypeAbovePhreaticLevel'] in ['SuShearStrengthModel', 'SuTable']:
        S = soil_params['S']
        m = soil_params['m']
        POP = soil_params['POP']
        sumin = soil_params['sumin']

        convert_shansep_to_su_table(soil, S, m, POP, cut_off=sumin, gamma_su=1.0,
                                    SU_increase_factor=load_case.strain_rate_dependency_factor * load_case.intermediate_principal_stress_factor_clay)


def assign_probabilistic_soil_params(data: dict, params: dict, load_case: LoadCase, soil_parameter_table: SoilParameterTable) -> dict:
    """

    :param data:
    :param params:
    :param load_case:
    :param soil_parameter_table
    :return:
    """
    if soil_parameter_table == SoilParameterTable.TABLE_2024:
        soils = data['soils']['Soils']

        for soil in soils:
            soil_code = soil['Code']
            soil_params = params.get(soil_code, None)

            Table = get_soil_parameter_table_LNA(soil_parameter_table)
            TableSoils = [l.lower() for l in Table['Code']]

            scode = get_soil_code(soil)
            I = TableSoils.index(scode)
            soil_type = Table['mapping'][I]

            if soil_type == SoilGeoClassification.CPT.name:
                print(
                    f"::: Soil {soil['Code']} is classified as CPT, no parameters are set. Soil properties from LNA are conserved.")
                continue  # do nothing and keep LNA
            else:
                soil["IsProbabilistic"] = False
                soil["VolumetricWeightAbovePhreaticLevel"] = soil_params["VolumetricWeightAbovePhreaticLevel"]
                soil["VolumetricWeightBelowPhreaticLevel"] = soil_params["VolumetricWeightBelowPhreaticLevel"]
                apply_table_parameters_stochastic(soil, soil_code, load_case, params)

    elif soil_parameter_table == SoilParameterTable.TABLE_2025:
        soils = data['soils']['Soils']

        SU_TABLE_path = Path(__file__).parent.parent.joinpath("data", "SU_TABLES.xlsx")
        SU_TABLE_clay = pd.read_excel(SU_TABLE_path, sheet_name='clay')
        SU_TABLE_clay_organic = pd.read_excel(SU_TABLE_path, sheet_name='organic_clay')
        SU_TABLE_clay_silty = pd.read_excel(SU_TABLE_path, sheet_name='silty_clay')

        for soil in soils:

            scode = get_soil_code(soil)

            if "onder" in soil['Code']:
                onder_naast = OnderNaast.ONDER
            elif "naast" in soil['Code']:
                onder_naast = OnderNaast.NAAST
            else:
                onder_naast = OnderNaast.NEITHER

            parameter_table = Path(__file__).parent.parent.joinpath("data", "ParameterTable_LNA.xlsx")

            Table = get_soil_parameter_table_LNA(parameter_table)
            TableSoils = [l.lower() for l in Table['Code']]
            I = TableSoils.index(scode)
            soil_type = Table['mapping'][I]

            soil_code = soil['Code']
            soil_params = params.get(soil_code, None)

            soil["IsProbabilistic"] = False
            soil["VolumetricWeightAbovePhreaticLevel"] = soil_params["VolumetricWeightAbovePhreaticLevel"]
            soil["VolumetricWeightBelowPhreaticLevel"] = soil_params["VolumetricWeightBelowPhreaticLevel"]

            def _apply_stochastic_su_table_fibrous_peat(soil: dict, params: dict, onder_or_naast: OnderNaast):

                if onder_or_naast == OnderNaast.ONDER:
                    S = params['fibrous_peat_onder']['S']
                elif onder_or_naast == OnderNaast.NAAST:
                    S = params['fibrous_peat_naast']['S']

                m = params['fibrous_peat']['m']
                POP = params['fibrous_peat']['POP']
                sumin = params['fibrous_peat'].get('Sumin', 0.0)
                inter_principal_stress_clay_effect = params['inter_principal_stress_clay_effect']
                strain_rate_effect = params['strain_rate_effect']

                convert_shansep_to_su_table(soil, S, m, POP, cut_off=sumin, gamma_su=1.0,
                                            SU_increase_factor=inter_principal_stress_clay_effect * strain_rate_effect)

            def _apply_stochastic_su_table_clay_adjacent(soil: dict, params: dict):
                S = params['clay_naast']['S']
                m = params['clay_naast']['m']
                POP = params['clay_naast']['POP']
                sumin = params['clay_naast'].get('Sumin', 0.0)
                inter_principal_stress_clay_effect = params['inter_principal_stress_clay_effect']
                strain_rate_effect = params['strain_rate_effect']

                convert_shansep_to_su_table(soil, S, m, POP, cut_off=sumin, gamma_su=1.0,
                                            SU_increase_factor=inter_principal_stress_clay_effect * strain_rate_effect)

            def _apply_stochastic_su_table_clay_onder(soil: dict, params: dict, table: pd.DataFrame):
                clay_onder_SU_factor = params['clay_onder_SU_factor']
                inter_principal_stress_clay_effect = params['inter_principal_stress_clay_effect']
                strain_rate_effect = params['strain_rate_effect']
                SU_increase_factor = inter_principal_stress_clay_effect * strain_rate_effect

                soil['ShearStrengthModelTypeAbovePhreaticLevel'] = 'SuTable'
                soil['ShearStrengthModelTypeBelowPhreaticLevel'] = 'SuTable'

                su_list = np.exp(table['ln(su_mean)'] * clay_onder_SU_factor)
                su_table_points = [{'EffectiveStress': sig_vp, 'Su': Su * SU_increase_factor} for (sig_vp, Su) in
                                   zip(table['EffectiveStress'], su_list)]
                soil['SuTable']['SuTablePoints'] = su_table_points

            if soil_type == SoilGeoClassification.TABLE.name:
                apply_table_parameters_stochastic(soil, soil_code, load_case, params)
                pass

            elif soil_type == SoilGeoClassification.CLAY.name:
                if onder_naast == OnderNaast.ONDER:
                    _apply_stochastic_su_table_clay_onder(soil, params, SU_TABLE_clay)
                    pass
                elif onder_naast == OnderNaast.NAAST:
                    _apply_stochastic_su_table_clay_adjacent(soil, params)
                    pass


            elif soil_type == SoilGeoClassification.SILTY_CLAY.name:
                if onder_naast == OnderNaast.ONDER:
                    _apply_stochastic_su_table_clay_onder(soil, params, SU_TABLE_clay_silty)
                elif onder_naast == OnderNaast.NAAST:
                    _apply_stochastic_su_table_clay_adjacent(soil, params)


            elif soil_type == SoilGeoClassification.CLAY_ORGANIC.name:
                if onder_naast == OnderNaast.ONDER:
                    _apply_stochastic_su_table_clay_onder(soil, params, SU_TABLE_clay_organic)
                elif onder_naast == OnderNaast.NAAST:
                    _apply_stochastic_su_table_clay_adjacent(soil, params)
                else:  # For embankment clay "H_Aa_onb_k", we apply the same parameters as for organic clay below
                    _apply_stochastic_su_table_clay_onder(soil, params, SU_TABLE_clay_organic)

            elif soil_type == SoilGeoClassification.FIBROUS_PEAT.name:
                _apply_stochastic_su_table_fibrous_peat(soil, params, onder_naast)

            elif soil_type == SoilGeoClassification.EMBANKMENT_CLAY.name:
                _apply_stochastic_su_table_clay_onder(soil, params, SU_TABLE_clay_organic)

            elif soil_type == SoilGeoClassification.EMBANKMENT_SAND.name:
                soil['ShearStrengthModelTypeAbovePhreaticLevel'] = 'MohrCoulombAdvanced'
                model = soil['MohrCoulombAdvancedShearStrengthModel']
                # Apply intermediate stress factor to sin(phi) then back-calculated phi
                phi = np.degrees(np.arcsin(np.sin(np.radians(params['embankment_sand']['phi'])) * params[
                    'inter_principal_stress_sand_effect']))

                model['FrictionAngle'] = phi
                model['Cohesion'] = 0
                model['Dilatancy'] = 0


            elif soil_type == SoilGeoClassification.CPT.name:
                print(
                    f"::: Soil {soil['Code']} is classified as CPT, no stochastic parameters are set. Soil properties from origin stix file are conserved.")
                continue  # do nothing and keep LNA

                # soil["IsProbabilistic"] = False
                # soil["VolumetricWeightAbovePhreaticLevel"] = soil_params["VolumetricWeightAbovePhreaticLevel"]
                # soil["VolumetricWeightBelowPhreaticLevel"] = soil_params["VolumetricWeightBelowPhreaticLevel"]
                # apply_table_parameters_stochastic(soil, soil_params, safety_format, load_case)

            else:
                raise ValueError(f"Unknown soil classification: {soil_type} {scode}")

    else:
        raise NotImplementedError(f"Unknown soil parameter table: {soil_parameter_table}")

    return data


def convert_shansep_to_su_table(soil: dict, S: float, m: float, POP: float, cut_off: float, gamma_su: float,
                                SU_increase_factor: float):
    """
    Converts SHANSEP parameters to a SuTable for the given soil.

    :param soil: Soil object to modify
    :param S: Shear strength ratio
    :param m: Strength increase exponent
    :param POP: Preconsolidation pressure offset (kPa)
    :param cut_off: Minimum shear strength value
    :param gamma_su: partial factor for shear strength
    :param SU_increase_factor: Factor to increase shear strength for load case

    """
    SuTableNeeded = False
    if soil['ShearStrengthModelTypeBelowPhreaticLevel'] in ['Su', 'SuTable', 'SuShearStrengthModel']:
        soil['ShearStrengthModelTypeBelowPhreaticLevel'] = 'SuTable'
        SuTableNeeded = True
    if soil['ShearStrengthModelTypeAbovePhreaticLevel'] in ['Su', 'SuTable', 'SuShearStrengthModel']:
        soil['ShearStrengthModelTypeAbovePhreaticLevel'] = 'SuTable'
        SuTableNeeded = True

    if SuTableNeeded and S < 0.0001:
        print(f'{soil["Code"]}::: S_mean too small; changing material to drained')
        soil['ShearStrengthModelTypeAbovePhreaticLevel'] = 'MohrCoulombAdvanced'
        SuTableNeeded = False

    if SuTableNeeded:
        soil['ShearStrengthModelTypeAbovePhreaticLevel'] = 'SuTable'
        soil['ShearStrengthModelTypeBelowPhreaticLevel'] = 'SuTable'
        soil['SuShearStrengthModel']['ShearStrengthRatio'] = S
        soil['SuShearStrengthModel']['StrengthIncreaseExponent'] = m
        soil['SuTable']['StrengthIncreaseExponent'] = m
        sig_vp_points = np.linspace(1.e-16, 200, 101)
        #
        # SHANSEP equation based on POP and minimum Su
        su_points = sig_vp_points * S * (1 + POP / sig_vp_points) ** m
        su_points = su_points * SU_increase_factor / gamma_su  # apply partial factor and load case increase
        su_points[su_points < cut_off] = cut_off
        sig_vp_points[0] = 0.

        su_table_points = [{'EffectiveStress': sig_vp, 'Su': Su} for (sig_vp, Su) in
                           zip(sig_vp_points, su_points)]
        soil['SuTable']['SuTablePoints'] = su_table_points


def set_drained(data, set_above=True, set_below=True):
    '''
    sets all material to drained, based on boolean values of 'set_above' and 'set_below'
    '''

    for soil in data['soils']['Soils']:
        if set_above:
            soil['ShearStrengthModelTypeAbovePhreaticLevel'] = 'MohrCoulombAdvanced'
        if set_below:
            soil['ShearStrengthModelTypeBelowPhreaticLevel'] = 'MohrCoulombAdvanced'

    return data


def change_train_loads(data: dict, load_case: LoadCase, gamma_train_load: float, analysis_side: str,
                       location: Location,
                       char_train_load: Optional[float] = None):
    """
    Assumption:
        - Stix name ends either with R or L for the side of the analysis
        - Load name for the train load contains 'Train' and the "right" or "left"
        - Consolidation ratio of the train load is 0% for undrained layers and 100% for drained layers in the original stix file
    :param data:
    :param load_case:
    :param analysis_side:
    :param char_train_load: Characteristic train load, if not provided, the load is calculated based on the class
    :return:
    """

    ## 1. Check if the analysis side is correct
    if analysis_side not in ["L", "R"]:
        raise ValueError(f"Unknown analysis side: {analysis_side}")

    ## 2. Normalize the name of the load depending on the number of tracks considered.
    # count number of loads for which there are train in name:
    train_loads = [load for load in data['loads/loads']['UniformLoads'] if 'Train' in load['Label']]
    if len(train_loads) == 0:
        print("No train loads found in the stix file.")
        return data

    elif len(train_loads) == 1:  # correct name of the load for single track
        load = train_loads[0]
        if analysis_side == 'L':
            load['Label'] = 'Train Load left'
        else:
            load['Label'] = 'Train Load right'

    elif len(train_loads) == 2:  # dont do anything here, normal case
        pass

    ## 3. Define the train load magnitude based on the load case and location
    if load_case.train_class == "D4" and location.load_type == LoadType.BLOCK:
        train_main_load = TrainLoadRLN.train_block_load_main_d4
    elif load_case.train_class == "D4" and location.load_type == LoadType.LINE:
        train_main_load = TrainLoadRLN.train_line_load_main_d4
    elif load_case.train_class == "C2" and location.load_type == LoadType.BLOCK:
        train_main_load = TrainLoadRLN.train_block_load_main_c2
    elif load_case.train_class == "C2" and location.load_type == LoadType.LINE:
        train_main_load = TrainLoadRLN.train_line_load_main_c2
    else:
        raise ValueError(f"Unknown train class {load_case.train_class} for location {location.id}")
    train_other_load = 0.8 * train_main_load

    ## 4. Get partial factor for the train load
    partial_factor_load = gamma_train_load

    ## 5. Adjust the load magnitude and consolidation ratio
    for load in data['loads/loads']['UniformLoads']:

        ## Adjust load magnitude
        if 'Train' in load['Label']:

            if load_case.main_load == "main_train_track":
                main_train_load = train_main_load * partial_factor_load
                other_train_load = train_other_load * partial_factor_load  # this 0.8 times the main train load
            else:
                main_train_load = train_main_load * 1.0
                other_train_load = train_other_load * 1.0

            if char_train_load is not None:  # for probabilistic analysis, char value is provided as input
                main_train_load = char_train_load
                other_train_load = char_train_load * 0.8

            if 'left' in load['Label'].lower():
                if analysis_side == "L":
                    load['Magnitude'] = main_train_load
                else:
                    load['Magnitude'] = other_train_load

            if 'right' in load['Label'].lower():
                if analysis_side == "R":
                    load['Magnitude'] = main_train_load
                else:
                    load['Magnitude'] = other_train_load

            ## Adjust consolidation ratio only for train loads
            for layer in load["Consolidations"]:
                if layer["Degree"] != 100 and load_case.load_effect is not None:
                    # IMPORTANT 100% pore pressure response mean 0% consolidation in D-Stability
                    layer["Degree"] = (1 - load_case.load_effect) * 100  # must be in %
                else:
                    layer["Degree"] = 100  # must be in %

    if not load_case.istrain:
        set_no_train(data)

    return data


def set_no_train(data):
    for loads in data['loads/loads']['UniformLoads']:
        if 'Train' in loads['Label']:
            loads['Magnitude'] = 0.

    return data


def raise_watertable_probabilistic(data: dict, params: dict) -> dict:
    """

    :param data:
    :param params:
    :return:
    """
    points = data['waternets/waternets']['HeadLines'][0]['Points']

    # get max
    Z = [p['Z'] for p in points]
    Zmax = np.max(Z)

    dz = params["PL1_bulge"]
    for p in points:
        if p['Z'] + .01 > Zmax:
            p['Z'] += dz

    # tighten the buldge when it increases in height, otherwise the waterline might intersect the slope of the embankment
    points[1]['X'] += 2
    points[4]['X'] -= 2
    return data


def raise_watertable(data: dict, load_case: LoadCase, location: Location) -> dict:
    """
    Assumptions:
        - the first headline is to be raised (PL1)
        - the first headline is parametrized with 6 points; Point 3 and 4 are the top of the bulge and therefore need to be raised.
        - For the RLN case, we move the bulge 0.5m above the second headline (PL2)
        - For the high groundwater case, we move the bulge to the ballast level in the model

    :param data:
    :param load_case:
    :param location: Location object containing the ballast level
    :return: modified stix data
    """
    points = data['waternets/waternets']['HeadLines'][0]['Points']

    # get max
    Z = [p['Z'] for p in points]
    Zmax = np.max(Z)

    if load_case.waterline_bulge == "RLN":
        pass  # do nothing as the initial file should be already correctly configured

    elif load_case.waterline_bulge == "RLN_1":
        # We move PL1 0.5meter above PL2
        level_PL2 = data['waternets/waternets']['HeadLines'][1]['Points'][0]['Z']

        dz = 1
        if level_PL2 + dz < location.ballast_level:
            for p in points:
                if p['Z'] + .01 > Zmax:
                    p['Z'] += dz

    elif load_case.waterline_bulge == "RLN_2":
        # We move PL1 0.5meter above PL2
        level_PL2 = data['waternets/waternets']['HeadLines'][1]['Points'][0]['Z']

        dz = 2
        if level_PL2 + dz < location.ballast_level:
            for p in points:
                if p['Z'] + .01 > Zmax:
                    p['Z'] += dz
        else:
            for p in points:
                if p['Z'] + .01 > Zmax:
                    p['Z'] = location.ballast_level

    elif load_case.waterline_bulge == "high_groundwater":
        # double list comprehension for point in layer and for layer in data['geometries/geometry']["Layers"]

        # find the  point with closest X to 0 and get the Z value
        for p in points:
            if p['Z'] + .01 > Zmax:
                p['Z'] = location.ballast_level

        # tighten the buldge when it increases in height, otherwise the waterline might intersect the slope of the embankment
        points[1]['X'] += 2
        points[4]['X'] -= 2

    elif load_case.waterline_bulge == 'high_groundwater_low':
        for p in points:
            if p['Z'] + .01 > Zmax:
                p['Z'] = location.ballast_level - 0.5

        # tighten the buldge when it increases in height, otherwise the waterline might intersect the slope of the embankment
        points[1]['X'] += 2
        points[4]['X'] -= 2


    else:
        raise ValueError(f"Unknown waterline bulge type: {load_case.waterline_bulge}")

    return data


def set_uplift_van(data):
    '''
    Dont do anything here, it should come from the inpout file.
    :param data:
    :return:
    '''
    # res = data['results/bishopbruteforce/bishopbruteforceresult']
    # circle_center_bishop = res['Circle']["Center"]
    #
    calc = data['calculationsettings/calculationsettings_1']
    # tangent_lines_bishop = data['calculationsettings/calculationsettings']['BishopBruteForce'][
    #     'TangentLines']  # BottomTangentLineZ  #Space #NumberOFTangentLines
    #
    calc['AnalysisType'] = 'UpliftVanParticleSwarm'
    calc['UpliftVanParticleSwarm']['SlipPlaneConstraints'] = calc['BishopBruteForce']['SlipPlaneConstraints']
    # calc['UpliftVanParticleSwarm']['SearchAreaA']["Height"] = 5
    # calc['UpliftVanParticleSwarm']['SearchAreaA']["TopLeft"] = circle_center_bishop
    # calc['UpliftVanParticleSwarm']['SearchAreaA']["Width"] = 5
    #
    # calc['UpliftVanParticleSwarm']['SearchAreaB']["Height"] = 5
    # calc['UpliftVanParticleSwarm']['SearchAreaB']["TopLeft"] = dict(X=circle_center_bishop['X'] - 10,
    #                                                                 Z=circle_center_bishop['Z'] - 4)
    # calc['UpliftVanParticleSwarm']['SearchAreaB']["Width"] = 5
    #
    # calc['UpliftVanParticleSwarm']["TangentArea"]["Height"] = tangent_lines_bishop["Space"] * tangent_lines_bishop[
    #     "NumberOfTangentLines"]
    # calc['UpliftVanParticleSwarm']["TangentArea"]["Topz"] = tangent_lines_bishop["BottomTangentLineZ"] + \
    #                                                         tangent_lines_bishop["Space"] * tangent_lines_bishop[
    #                                                             "NumberOfTangentLines"]

    return data


def set_spencer(data, stix_path):
    calc = data['calculationsettings/calculationsettings']
    calc['AnalysisType'] = 'Spencer'
    calc['Spencer']['SlipPlaneConstraints'] = calc['BishopBruteForce']['SlipPlaneConstraints']

    template_spencer_stix = stix_path.parent.joinpath('template_method', 'SPENCER.stix')
    template_data = read_dgs(template_spencer_stix)
    calc_template = template_data['calculationsettings/calculationsettings']['SpencerGenetic']
    input_slipplane_A = calc_template['SlipPlaneA']
    input_slipplane_B = calc_template['SlipPlaneB']

    calc['AnalysisType'] = 'SpencerGenetic'
    calc['SpencerGenetic']['SlipPlaneA'] = input_slipplane_A
    calc['SpencerGenetic']['SlipPlaneB'] = input_slipplane_B
    calc['SpencerGenetic']['SlipPlaneConstraints']['IsEnabled'] = True
    calc['SpencerGenetic']['SlipPlaneConstraints']['MinimumThrustLinePercentageInsideSlices'] = 80
    calc['SpencerGenetic']['SlipPlaneConstraints']['MinimumAngleBetweenSlices'] = 50

    return data


def set_calculation_method(data: dict, calculation_method: CalculationMethod, stix_path: Optional[Path]) -> dict:
    if calculation_method == CalculationMethod.BISHOP:
        pass
        # assert calc['AnalysisType'] == 'BishopBruteForce'  # do nothing, this is the base case

    elif calculation_method == CalculationMethod.SPENCER:
        data = set_spencer(data, stix_path)
    elif calculation_method == CalculationMethod.UPLIFTVAN:
        data = set_uplift_van(data)

    else:
        raise NotImplementedError(f"Calculation method {calculation_method} not implemented")
    return data


def remove_states(data: dict) -> dict:
    """
    Remove all the states from the stix file
    :param data:
    :return:
    """
    data['states/states']['StatePoints'] = []

    return data


def set_fixed_slip_plane(data: dict):
    calc_bishop = data['calculationsettings/calculationsettings']
    calc_bishop['AnalysisType'] = 'Bishop'
    calc_bishop['Bishop']["Circle"] = data['results/bishopbruteforce/bishopbruteforceresult']['Circle']

    calc_uplift = data['calculationsettings/calculationsettings_1']
    res_upliftswarm =  data['results/upliftvanparticleswarm/upliftvanparticleswarmresult']
    calc_uplift['AnalysisType'] = 'UpliftVan'
    calc_uplift['UpliftVan']['SlipPlane'] = {"FirstCircleCenter" : {'X': None, 'Z': None}, "FirstCircleRadius": None,
                                             "SecondCircleCenter": {"X": None, "Z": None}}

    z_B = res_upliftswarm['TangentLine']
    Z_A_left = res_upliftswarm['LeftCenter']['Z']
    Z_A_right = res_upliftswarm['RightCenter']['Z']
    radius_left = abs(z_B - Z_A_left)
    radius_right = abs(z_B - Z_A_right)

    if radius_left > radius_right:
        first_circle = res_upliftswarm['LeftCenter']
        second_circle = res_upliftswarm['RightCenter']
        radius =  radius_left
    else:
        first_circle = res_upliftswarm['RightCenter']
        second_circle = res_upliftswarm['LeftCenter']
        radius = radius_right


    calc_uplift['UpliftVan']['SlipPlane']["FirstCircleCenter"] = first_circle
    calc_uplift['UpliftVan']['SlipPlane']["SecondCircleCenter"] = second_circle
    calc_uplift['UpliftVan']['SlipPlane']["FirstCircleRadius"] = radius
    return data

