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

    def getUnitVector(self, length = 1) -> Vector:
        return createVector(length, self.value)

    def getNextCounterClockWise(self, count: int = 1) -> 'HexTileEdges':
        return HexTileEdges((self.value + 60 * count) % 360)

    def getNextClockWise(self, count: int = 1) -> 'HexTileEdges':
        return HexTileEdges((self.value - 60 * count) % 360)

    def getVertices(self):
        return HexTileVertices((self.value + 240) % 360), HexTileVertices((self.value + 300) % 360)

class HexTileManifestEdges(IntEnum):
    NW = 120
    SW = 180
    S = 240
    SE = 300
    NE = 0
    N = 60

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

    # Unit vector for hexagon edge CW from this vertex (normalized directions)
    def getEdgeClockWise(self) -> HexTileEdges:
        return HexTileEdges((self.value + 60) % 360)

    # Vertex of the hexagon with a specific width
    def getVector(self, hexShortDiagonal: float) -> Vector:
        return hexShortDiagonal / 2 / cos(radians(30)) * self.getUnitVector()

    def getNextClockWise(self) -> 'HexTileVertices':
        return HexTileVertices((self.value - 60) % 360)

    def getNextCounterClockWise(self) -> 'HexTileVertices':
        return HexTileVertices((self.value + 60) % 360)

    @classmethod
    def iterate(cls, start: 'HexTileVertices' = N):
        sortedVertices = sorted(cls, key=lambda v: v.value)
        startIndex = sortedVertices.index(start)
        for i in range(len(sortedVertices)):
            yield sortedVertices[(startIndex + i) % len(sortedVertices)]
