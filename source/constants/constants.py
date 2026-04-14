from enum import Enum
from typing import List
from dataclasses import dataclass
from pathlib import Path

DSTABILITY_BIN_FOLDER = r"C:\Program Files\Deltares\D-GEO Suite\D-Stability 2025.01\bin"


SOIL_COLLECTION_CONVERT = {
    "h_mg_zm": "h_mg_zm",
    "h_mg_zf": "h_mg_zf",
    "h_mg_zk": "h_mg_zk",
    "h_mp_zf": "h_mp_zf",
    "h_mr_kz_z": "h_mr_kz_z",
    "h_mr_kz_k": "h_mr_kz_k",
    "h_mkw_z_k": "h_mkw_z&k",
    "h_mp_k": "h_mp_k",
    "h_mp_ko": "h_mp_ko",
    "h_ml_ko": "h_ml_ko",
    "h_eg_zm_z": "h_eg_zm_z",
    "h_eg_zm_k": "h_eg_zm_k",
    "h_eg_z_k_k": "h_eg_z&k_k",
    "h_eg_z_k_z": "h_eg_z&k_z",
    "h_rg_zg": "h_rg_zg",
    "h_rg_zm": "h_rg_zm",
    "h_rg_zf": "h_rg_zf",
    "h_rr_o_z_k": "h_rr_o&z_k",
    "h_rr_o_z_z": "h_rr_o&z_z",
    "h_ro_z_k_k": "h_ro_z&k_k",
    "h_ro_z_k_z": "h_ro_z&k_z",
    "h_rk_k_k": "h_rk_k_k",
    "h_rk_k_z": "h_rk_k_z",
    "h_rk_k_v": "h_rk_k&v",
    "h_rk_ko": "h_rk_ko",
    "h_rk_vk": "h_rk_vk",
    "h_vhv_v": "h_vhv_v",
    "h_vbv_v": "h_vbv_v",
    "p_rbk_vk": "p_rbk_vk",
    "h_ova_zm": "h_ova_zm",
    "h_ova_zf": "h_ova_zf",
    "h_aa_z": "h_aa_z",
    "h_aa_kz": "h_aa_kz",
    "h_aa_ks": "h_aa_ks",
    "h_aa_ko": "h_aa_ko",
    "h_aa_onb": "h_aa_onb",
    "p_mg_zm": "p_mg_zm",
    "p_mg_zk": "p_mg_zk",
    "p_mp_k": "p_mp_k",
    "p_rg_zg": "p_rg_zg",
    "p_rg_zm": "p_rg_zm",
    "p_rg_zf": "p_rg_zf",
    "p_rk_k_s": "p_rk_k&s",
    "p_rbk_zm": "p_rbk_zm",
    "p_rbk_z_s_z": "p_rbk_z&s_z",
    "p_rbk_z_s_s": "p_rbk_z&s_s",
    "p_rbk_kz": "p_rbk_kz",
    "p_wrd_zm": "p_wrd_zm",
    "p_wdz_zf": "p_wdz_zf",
    "p_wls_s": "p_wls_s",
    "p_gs_zg": "p_gs_zg",
    "p_ggs_zg_z": "p_ggs_zg_z",
    "p_ggs_zg_k": "p_ggs_zg_k",
    "p_gkl_kz_k": "p_gkl_kz_k",
    "p_gkl_kz_z": "p_gkl_kz_z",
    "p_om_zf": "p_om_zf",
    "p_om_k": "p_om_k",
    "p_ova_sd": "p_ova_sd",
    "t_mm_k": "t_mm_k",
    "t_mm_z": "t_mm_z",
    "t_mm_br": "t_mm_br",
    "t_mm_st": "t_mm_st",
    "k_mm_st": "k_mm_st",
    "k_mm_s": "k_mm_s",
    "example_1": "example_1",
    "h_aa_onb_k": "h_aa_onb_k",
    "h_aa_onb_z": "h_aa_onb_z",
    "empty": "empty",
}


@dataclass
class ModelFactorStatistics:
    model_factor_bishop_block_mean: float = 1.0
    model_factor_bishop_block_std: float = 0.05
    model_factor_bishop_line_mean: float = 1.05
    model_factor_bishop_line_std: float = 0.05

    model_factor_upliftvan_block_mean: float = 0.95
    model_factor_upliftvan_block_std: float = 0.05
    model_factor_upliftvan_line_mean: float = 1.0
    model_factor_upliftvan_line_std: float = 0.05

    model_factor_spencer_block_mean: float = 0.95
    model_factor_spencer_block_std: float = 0.05
    model_factor_spencer_line_mean: float = 1.0
    model_factor_spencer_line_std: float = 0.05


@dataclass
class TrainLoadRLN:
    train_block_load_main_d4 = 35  # kPa
    train_block_load_main_c2 = 31  # kPa
    train_line_load_main_d4 = 26.16
    train_line_load_main_c2 = None


@dataclass
class TrainLoadStatistics:
    """Statistics for the train loads."""

    train_block_load_main_d4_mean = None


@dataclass
class ClayAdjacentShansepParameters:
    """Shansep parameters for clay adjacent to the embankment."""

    S_mean = 0.01
    S_std = 0
    S_95kar = 0.01

    m_mean = 0.8
    m_std = 0.01
    m_95kar = 0.78366  # from PTK (log distribution 0.05)  TODO: should not be hardcoded: use ptk library or scipy (choose a percentile)

    POP_mean = 20  # kPa
    POP_std = 10
    POP_95kar = 8.22  # from PTK (log distribution 0.05)

    cut_off = 0


@dataclass
class FibrousPeatUnderShansepParameters:
    """Shansep parameters for fibrous peat under the embankment.
    Axial strain = 2%

    """

    S_mean = 0.588  # from Alexander
    S_std = 0.034  # from Alexander
    S_95kar = 0.5338  # from PTK (log distribution 0.05)

    m_mean = 0.7  # from Alexander
    m_std = 0.012  # from Alexander
    m_95kar = 0.68044  # from PTK (log distribution 0.05)

    POP_mean = 2.788  # from Alexander (kPa)
    POP_std = 0.788  # from Alexander
    POP_95kar = 1.7005  # from PTK (log distribution 0.05)


@dataclass
class FibrousPeatAdjacentShansepParameters:
    """Shansep parameters for fibrous peat adjacent to the embankment.
    S axial strain 2%
    m and POP values are the same for the peat in the active zone (onder embankment)
    """

    S_mean = 0.01  # from Alexander
    S_std = 0  # from Alexander
    S_95kar = 0.01

    m_mean = 0.7  # from Alexander
    m_std = 0.012  # from Alexander
    m_95kar = 0.68044  # from PTK (log distribution 0.05)

    POP_mean = 2.788  # from Alexander (kPa)
    POP_std = 0.788  # from Alexander
    POP_95kar = 1.7005  # from PTK (log distribution 0.05)


@dataclass
class EmbankmentSandParameters:
    phi_mean = 45  # backcalculated by Mark
    phi_std = 8  # backcalculated by Mark
    phi_95kar = 33.147  # from PTK
    psi = 0
    c = 0


@dataclass
class StrainRateEffectDistibution:
    factor_mean: float = 1.2  # from Alexander
    factor_std: float = 0.03  # from Alexander
    factor_95kar: float = 1.1513  # from PTK (log distribution 0.05)


@dataclass
class IntermediatePrincipalStressEffectDistibution:
    factor_sand_mean: float = 1.08  # from Alexander
    factor_sand_std: float = 0.03  # from Alexander
    factor_sand_kar: float = (
        1.05  # from Alexander (PTK returns 1.0314 which is lower than Lower limit)
    )

    factor_clay_mean: float = 1.06  # from Alexander
    factor_clay_std: float = 0.04  # from Alexander
    factor_clay_kar: float = (
        1.0  # from Alexander (PTK returns 0.99 which is lower than Lower limit)
    )


@dataclass
class ClaySUTableFactor:
    mean = 1.0
    std = 0.05


class CalculationMethod(Enum):
    """Enum for the calculation method."""

    BISHOP = 1
    UPLIFTVAN = 2
    SPENCER = 3


CALCULATION_METHOD_ANALYSIS_TYPE = {
    CalculationMethod.BISHOP:    'BishopBruteForce',
    CalculationMethod.UPLIFTVAN: 'UpliftVanParticleSwarm',
    CalculationMethod.SPENCER:   'SpencerGenetic',
}


class SoilParameterTable(Enum):
    """Enum for the soil parameter table."""

    LNA = 1
    TABLE_2024 = 2  # this is the table made in 2024, it is used for the 2024 cases
    TABLE_2025 = 3  # this will activate the custom soil parameters of Alexander made in June 2025.


class SoilGeoClassification(Enum):
    """Enum for the soil geo classification according to Alexander"""

    TABLE = 1  # use the LNA table (mostly for sand)
    SILTY_CLAY = 2
    CLAY_ORGANIC = 3
    CLAY = 4
    FIBROUS_PEAT = 5
    CPT = 6  # use CPT interpretation for the soil parameters
    EMBANKMENT_SAND = 7
    EMBANKMENT_CLAY = 8
    UNKNWON = 9


class OnderNaast(Enum):
    """Enum for the OnderNaast classification."""

    ONDER = 1
    NAAST = 2
    NEITHER = 3
    ONBEKEND = 4

    def __str__(self):
        """Return the string representation of the enum."""
        return self.name.lower()


class LoadType(Enum):
    """Enum for the load type."""

    BLOCK = "block"
    LINE = "line"
