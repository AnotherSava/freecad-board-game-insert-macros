from math import cos, sin, radians, tan

from FreeCAD import Vector

from Inserts.common.geometry import createVector
from dataclasses import dataclass
from enum import IntEnum


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
    adjacentDistance: float # distance between horizontally adjacent tiles
    magnetDiameter: float
    magnetHeightFloor: float
    magnetHeightCeiling: float
    extruderWidth: float

    def getHexSide(self):
        return self.hexWidth * tan(radians(30))

    def getHexSizeY(self):
        return self.hexWidth / cos(radians(30))

    def getDistanceFromHexCentreToOuterPinAngle(self):
        return self.getDistanceFromHexCentreToHexCorner(self.pinWidth * 2 + self.hexWidth)

    def getDistanceFromHexCentreToHexCorner(self, hexWidth: float):
        return hexWidth / 2 / cos(radians(30))

    def getCondensedDistanceY(self):
        return (self.hexWidth + self.pinWidth) / cos(radians(30)) - self.getCondensedDistanceX() / 2 * tan(radians(30))

    def getCondensedDistanceX(self):
        return self.hexWidth + self.adjacentDistance
