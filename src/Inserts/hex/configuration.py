from math import cos, sin, radians, tan

import numpy as np

from Inserts.common.geometry import createVector
from dataclasses import dataclass
from enum import IntEnum, auto
from FreeCAD import Vector


class HexTimeShiftDirection(IntEnum):
    UP = auto()
    DOWN = auto()

class HexTileEdges(IntEnum):
    NW = 120
    W = 180
    SW = 240
    SE = 300
    E = 0
    NE = 60

    def getUnitVector(self) -> Vector:
        return createVector(1, self.value)

class HexTileVertices(IntEnum):
    N = 0
    NW = 60
    SW = 120
    S = 180
    SE = 240
    NE = 300

    # Unit vector for hexagon vertex from its centre
    def getUnitVector(self) -> Vector:
        return Vector(-sin(radians(self.value)), cos(radians(self.value)))

    # Unit vector for hexagon edge CCW from this vertex (normalized directions)
    def getEdgeCounterClockWise(self) -> HexTileEdges:
        return HexTileEdges((self.value + 120) % 360)

    # Vertex of the hexagon with a specific width
    def getVector(self, hexWidth: float) -> Vector:
        return hexWidth / 2 / cos(radians(30)) * self.getUnitVector()

    def getNextClockWise(self) -> 'HexTileVertices':
        return HexTileVertices((self.value - 60) % 360)

    def getNextCounterClockWise(self) -> 'HexTileVertices':
        return HexTileVertices((self.value + 60) % 360)

@dataclass
class GridConfiguration:
    firstColumnHexCount: int
    secondColumnHexCount: int
    columnsTotal: int
    shiftDirection: HexTimeShiftDirection = None # is not none only if secondColumnCount == firstColumnCount

    def __post_init__(self):
        if self.firstColumnHexCount == self.secondColumnHexCount and self.shiftDirection is None:
            raise ValueError("Shift direction must be specified")

    def getHexCountInColumn(self, column):
        return 0 if column < 0 or column >= self.columnsTotal \
            else self.firstColumnHexCount if column % 2 == 0 \
            else self.secondColumnHexCount

    def getBottomPinsRowIndexForColumn(self, column):
        if column % 2 == 0:
            return 0 if self.shiftDirection is HexTimeShiftDirection.UP or self.secondColumnHexCount < self.firstColumnHexCount else 1

        return 0 if self.shiftDirection is HexTimeShiftDirection.DOWN or self.secondColumnHexCount > self.firstColumnHexCount else 1

@dataclass
class GridDimensions:
    hexWidth: float
    pinWidth: float
    pinLength: float
    pinRadius: float
    pinHeight: float
    floorThickness: float
    ceilingThickness: float
    ceilingLedgeThickness: float
    ceilingLedgeDelta: float
    ceilingHollowDelta: float
    adjacentDistance: float = None # distance between adjacent tiles that are not separated by a pin
    magnetDiameter: float = 2
    magnetHeightFloor: float = 3
    magnetHeightCeiling: float = 1
    extruderWidth: float = 0.42

    def getHexSizeY(self):
        return self.hexWidth / cos(radians(30))

    # distance between adjacent hex tile centres
    def getHexCentreDistance(self):
        return self.hexWidth + self.pinWidth

    # distance between adjacent hex tile centres on axis x
    def getHexCentreDistanceX(self):
        return self.getHexCentreDistance() * cos(radians(60))

    # distance between adjacent hex tile centres on axis y
    def getHexCentreDistanceY(self):
        return self.getHexCentreDistance() * sin(radians(60))

    def getDistanceFromHexCentreToOuterPinAngle(self):
        return self.getDistanceFromHexCentreToHexCorner(self.pinWidth * 2 + self.hexWidth)

    def getDistanceFromHexCentreToHexCorner(self, hexWidth: float):
        return hexWidth / 2 / cos(radians(30))

    def getCondensedDistanceY(self):
        sameRowHexDistanceX = self.hexWidth + self.adjacentDistance
        return (self.hexWidth + self.pinWidth) / cos(radians(30)) - sameRowHexDistanceX / 2 * tan(radians(30))

# value represents angle (CCW from y axis)
class HexPinSide(IntEnum):
    TOP = 0
    LEFT = 120
    RIGHT = 240

class PinConfiguration:
    def __init__(self, configuration: GridConfiguration):
        self.configuration = configuration

        self.sizeX = self.configuration.columnsTotal + 2
        self.sizeY = self.configuration.firstColumnHexCount + self.configuration.secondColumnHexCount + 1

        self.pinBoard = np.empty((self.sizeX, self.sizeY), dtype=object)

    def addRays(self, column, row, rays):
        currentRays = self.pinBoard[column, row]
        self.pinBoard[column, row] = rays if currentRays is None else list(set(currentRays) | set(rays))

    def doesPinExist(self, column, row):
        return 0 <= column < self.sizeX and 0 <= row < self.sizeY and self.pinBoard[column, row]

    def findMissingRay(self, column, row):
        missingRays = set(HexPinSide) - set(self.pinBoard[column, row])
        if len(missingRays) > 1:
            raise ValueError("Pin expected to have at least 2 rays")
        return None if not missingRays else missingRays.pop()
