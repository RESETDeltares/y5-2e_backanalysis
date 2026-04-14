from dataclasses import dataclass
from typing import Optional

from source.constants.constants import StrainRateEffectDistibution, IntermediatePrincipalStressEffectDistibution


@dataclass
class LoadCase:
    name: str
    CVal: str  # column in the parameter set to lookup
    istrain: bool = False

    # WATER
    waterline_bulge: Optional[str] = None  # 0.5 is standard RLN, otherwise to balaast level
    load_effect: Optional[float] = None  # load effect 50% or 100%
    train_class: str = 'D4'  #
    main_load: Optional[str] = None
    isdrained: Optional[bool] = None
    strain_rate_dependency_factor: Optional[float] = 1.0
    intermediate_principal_stress_factor_clay: Optional[float] = 1.0  # Rename clay and peat
    intermediate_principal_stress_factor_sand: Optional[float] = 1.0


CASES_CALIBRATION = {
    "LC1": LoadCase(name="LC1",
                    CVal="char_low",  # column in the parameter set to lookup
                    waterline_bulge="RLN",  # 0.5 is standard RLN
                    load_effect=1.0,  # load effect 50% or 100%
                    main_load="main_train_track",
                    isdrained=False,
                    istrain=True,
                    strain_rate_dependency_factor=StrainRateEffectDistibution.factor_95kar,  # 20% additional strain rate effect
                    intermediate_principal_stress_factor_clay=IntermediatePrincipalStressEffectDistibution.factor_clay_kar,
                    intermediate_principal_stress_factor_sand=IntermediatePrincipalStressEffectDistibution.factor_sand_kar

                    ),  # 20% additional strain rate effect
}

CASES_WIM = {
    "LC0b": LoadCase(name="LC0b",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN",  # 0.5 is standard RLN
                     load_effect=None,  # load effect 50% or 100%
                     main_load="main_train_track",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.0,
                     intermediate_principal_stress_factor_clay=1.0),

    "LC1a": LoadCase(name="LC1a",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN",  # 0.5 is standard RLN
                     load_effect=0.5,  # load effect 50% or 100%
                     main_load="main_train_track",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.2,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC1b": LoadCase(name="LC1b",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN",  # 0.5 is standard RLN
                     load_effect=0.25,  # load effect 50% or 100%
                     main_load="main_train_track",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.2,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC1c": LoadCase(name="LC1c",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN",  # 0.5 is standard RLN
                     load_effect=1.0,  # load effect 50% or 100%
                     main_load="main_train_track",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.2,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC1d": LoadCase(name="LC1d",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN_1",  # 0.5 is standard RLN
                     load_effect=0.5,  # load effect 50% or 100%
                     main_load="main_train_track",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.2,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC1e": LoadCase(name="LC1e",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN_2",  # 0.5 is standard RLN
                     load_effect=0.5,  # load effect 50% or 100%
                     main_load="main_train_track",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.2,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC1f": LoadCase(name="LC1f",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN_2",  # 0.5 is standard RLN
                     load_effect=0.5,  # load effect 50% or 100%
                     main_load="main_train_track",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.0,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC2a": LoadCase(name="LC2a",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN",  # 0.5 is standard RLN
                     load_effect=1.0,  # load effect 50% or 100%
                     main_load="main_train_track",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.0,
                     intermediate_principal_stress_factor_clay=1.0),  # 0% additional strain rate effect

    "LC3a": LoadCase(name="LC3a",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="high_groundwater",  # 0.5 is standard RLN
                     load_effect=0.5,  # load effect 50% or 100%
                     main_load="groundwater",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.0,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC3b": LoadCase(name="LC3b",
                     CVal="char_low",  # column in the parameter set to lookup
                     train_class='C2',
                     waterline_bulge="high_groundwater",  # 0.5 is standard RLN
                     load_effect=0.5,  # load effect 50% or 100%
                     main_load="groundwater",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.0,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC3c": LoadCase(name="LC3c",
                     CVal="char_low",  # column in the parameter set to lookup
                     train_class='D4',
                     waterline_bulge="high_groundwater_low",  # 0.5 is standard RLN
                     load_effect=0.5,  # load effect 50% or 100%
                     main_load="groundwater",
                     isdrained=False,
                     istrain=True,
                     strain_rate_dependency_factor=1.0,
                     intermediate_principal_stress_factor_clay=1.0),  # 20% additional strain rate effect

    "LC4a": LoadCase(name="LC4a",
                     CVal="char_low",  # column in the parameter set to lookup
                     waterline_bulge="RLN",  # 0.5 is standard RLN
                     load_effect=0,  # load effect 50% or 100%
                     main_load=None,
                     isdrained=True,
                     istrain=False,
                     strain_rate_dependency_factor=None,
                     intermediate_principal_stress_factor_clay=1.0)

}
