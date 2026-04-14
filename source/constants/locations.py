from dataclasses import dataclass
from typing import Optional

from source.constants.constants import LoadType


@dataclass
class Location:
    """
    A class to represent a location.
    """
    id: str
    name: str
    folder: str
    geocode: str
    load_type: LoadType
    ballast_level: Optional[float] = None  # in m used for LC3 and raised groundwater level


LOCATIONS_NEW = {
    "01": Location(id="Loc1",
                     name="Delft-Schiedam 76.8",
                     folder="1 - Delft -Schiedam 76.8",
                     geocode="S112",
                     load_type=LoadType.LINE,
                     ballast_level=-0.66,  # m
                     ),
    "02": Location(id="Loc",
                     name="Delft-Schiedam ",
                     folder="2 - Delft -Schiedam 78.1",
                     geocode="S112",
                     load_type=LoadType.BLOCK,
                     ballast_level=-1.77,  # m
                     ),
    "03": Location(id="Loc3",
                     name="Leeuwarden",
                     folder="3 - Leeuwarden - Groningen",
                     geocode="S002",
                     load_type=LoadType.BLOCK,
                     ballast_level=0.47,  # m
                     ),
    "04": Location(id="Loc4",
                     name="4 - Zwolle - Deventer",
                     folder="4 - Zwolle - Deventer",
                     geocode="S018",
                     load_type=LoadType.BLOCK,
                     ballast_level=2.32,  # m
                     ),

    "05": Location(id="Loc5",
                     name="5 - Eindhoven - Venlo",
                     folder="5 - Eindhoven - Venlo",
                     geocode="S055",
                     load_type=LoadType.BLOCK,
                     ballast_level=18.01,  # m
                     ),
    "06": Location(id="Loc6",
                     name="Lelystad",
                     folder="6 - Lelystad - Zwolle",
                     geocode="S161",
                     load_type=LoadType.LINE,
                     ballast_level=None,  # m
                     ),
    "07": Location(id="Loc7",
                     name="Maastricht",
                     folder="7 - Maastricht - Sittard",
                     geocode="",
                     load_type=LoadType.LINE,
                     ballast_level=69.36,  # m
                     ),
    "08": Location(id="Loc8",
                     name="Nijmegen",
                     folder="8",
                     geocode="",
                     load_type=LoadType.LINE,
                     ballast_level=17.04,  # m
                     ),
    "09": Location(id="Loc3",
                     name="",
                     folder="9",
                     geocode="S097",
                     load_type=LoadType.LINE,
                     ballast_level=1.82,  # m
                     ),
}

# LOCATIONS = {
#     "Loc1": Location(id="Loc1",
#                      name="Delft-Schiedam 76.8km",
#                      folder="dsn1-DS-76",
#                      geocode="S112",
#                      ballast_level=-0.66,  # m
#
#                      ),
#     "Loc2": Location(id="Loc2",
#                      name="Delft-Schiedam 78.1km",
#                      folder="dsn2-DS-78",
#                      geocode="S112",
#                      ballast_level=-1.77,  # m
#
#                      ),
#     "Loc3": Location(id="Loc3",
#                      name="Hurdegaryp",
#                      folder="dsn3-Hurdegaryp",
#                      geocode="S002",
#                      ballast_level=0.47,
#
#                      ),
#
#     "Loc4": Location(id="Loc4",
#                      name="Deventer-Zwolle",
#                      folder="dsn4-Wijhe",
#                      geocode="018",
#                      ballast_level=2.32
#                      ),
#
#     "Loc5": Location(id="Loc5",
#                      name="Nijmegen",
#                      folder="dsn5-Nijmegen",
#                      geocode="S044",
#                      ballast_level=None,
#                      ),
#     "Loc6": Location(id="Loc6",
#                      name="Einhoven",
#                      folder="dsn6-EindhovenVenlo",
#                      geocode="S055",
#                      ballast_level=None,
#                      ),
#     "Loc7": Location(id="Loc7",
#                      name='Breukelen',
#                      folder='dsn7-Breukelen',
#                      geocode='S097',
#                      ballast_level=None,
#                      ),
#
#     "Loc8": Location(id="Loc8",
#                      name='Zoetermeer',
#                      folder="dsn8-Zoetermer",
#                      geocode='S107',
#                      ballast_level=-0.79,
#                      ),
#
#     "Loc9": Location(id="Loc9",
#                      name='RotterdamGouda',
#                      folder='dsn9-RotterdamGouda',
#                      geocode='S132',
#                      ballast_level=None,
#                      ),
# }
