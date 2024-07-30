from enum import Enum


class EnergyType(Enum):
    Unknown = 0
    Bienergie_mazout = 1
    Bienergie_propane = 2
    Bienergie_gaz = 3
    Electrique = 4
    Electrique_avec_thermopompe = 5
    Mazout = 6
    Gaz = 7
    Propane = 8
    Mazout_plus_electricite = 9
    Propane_plus_electricite = 10
    Gaz_plus_electricite = 11


class HeatPumpType(Enum):
    Unknown = 0
    WATER_AIR = 1
    WATER_WATER = 2
    WATER_AIR_AND_WATER_WATER = 3


class CompassRose(Enum):
    E = 0
    ESE = 1
    SE = 2
    SSE = 3
    S = 4
    SSW = 5
    SW = 6
    WSW = 7
    W = 8
    WNW = 9
    NW = 10
    NNW = 11
    N = 12
    NNE = 13
    NE = 14
    ENE = 15
