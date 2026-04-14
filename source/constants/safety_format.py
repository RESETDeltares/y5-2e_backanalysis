from dataclasses import dataclass
from typing import Optional


@dataclass
class SafetyFormat:
    name: str
    CC: str  # consequence class
    gamma_c: float
    gamma_phi: float
    gamma_su: float
    gamma_train_load: float
    gamma_weight: float = 1.0
    gamma_water_line: float = 1.0
    gamma_strain_rate: float = 1.0
    gamma_intermediate_principal_stress_clay: float = 1.0
    gamma_intermediate_principal_stress_sand: float = 1.0
    # blockload lineload
    # 3d factor


SAFETY_FORMATS_DEFAULT = {
    'ONE': SafetyFormat(
        name="ONE",
        CC="ONE",
        gamma_c=1.0,
        gamma_phi=1.0,
        gamma_su=1.0,
        gamma_train_load=1.0
    ),
    'V_CC2': SafetyFormat(
        name="V_CC2",
        CC="VCC2",
        gamma_c=1.3,
        gamma_phi=1.2,
        gamma_su=1.5,
        gamma_train_load=1.2
    ),
    'V_CC3': SafetyFormat(
        name="V_CC3",
        CC="VCC3",
        gamma_c=1.45,
        gamma_phi=1.25,
        gamma_su=1.75,
        gamma_train_load=1.3
    ),
    'A_CC2': SafetyFormat(
        name="A_CC2",
        CC="ACC2",
        gamma_c=1.1,
        gamma_phi=1.1,
        gamma_su=1.2,
        gamma_weight=1.0,
        gamma_train_load=1.1
    ),

    'A_CC3': SafetyFormat(
        name="A_CC3",
        CC="ACC3",
        gamma_c=1.3,
        gamma_phi=1.2,
        gamma_su=1.5,
        gamma_weight=1.0,
        gamma_train_load=1.2
    )
}
