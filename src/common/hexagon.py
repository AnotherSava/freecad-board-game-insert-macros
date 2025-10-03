from enum import IntEnum
from math import cos, sin, radians, tan

from FreeCAD import Vector
import Part

from common.fuser import Fuser
from common.geometry import createWire, extrudeWire, createVector
from dataclasses import dataclass



def getHexSide(shortDiagonal: float):
    return shortDiagonal * tan(radians(30))


def getDiagonal(shortDiagonal: float = None):
    return shortDiagonal / cos(radians(30))


def getDistanceY(shortDiagonal: float, shortDiagonalGap: float, diagonalGap: float = None):
    diagonalGap = shortDiagonalGap if diagonalGap is None else diagonalGap
    return diagonalGap / cos(radians(30)) - shortDiagonalGap / 2 * tan(radians(30)) + getDiagonal(shortDiagonal) / 2 + getHexSide(shortDiagonal) / 2


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


@dataclass
class HexagonWallConfiguration:
    offsetDistance: float
    offsetClockWise: float
    offsetCounterClockWise: float
    display: bool


@dataclass
class HexagonRayConfiguration:
    offsetDistance: float


class HexagonConfiguration:
    def __init__(self, rayThickness: float = None, wallThickness: float = None):
        self.rayThickness = rayThickness
        self.wallThickness = wallThickness
        self.walls = {}
        self.rays = {}

    def withVisibleWalls(self, offsetDistance: float = 0, offsetClockWise: float = 0, offsetCounterClockWise: float = 0, *edges: HexTileEdges) -> 'HexagonConfiguration':
        for edge in edges if len(edges) > 0 else HexTileEdges:
            self.walls[edge] = HexagonWallConfiguration(offsetDistance, offsetClockWise, offsetCounterClockWise, True)

        return self

    def withHiddenWalls(self, offsetDistance: float = 0, *edges: HexTileEdges) -> 'HexagonConfiguration':
        for edge in edges if len(edges) > 0 else HexTileEdges:
            self.walls[edge] = HexagonWallConfiguration(offsetDistance, 0, 0, False)

        return self

    def withRays(self, offsetDistance: float = 0, *vertices: HexTileVertices) -> 'HexagonConfiguration':
        for vertex in vertices if len(vertices) > 0 else HexTileVertices:
            self.rays[vertex] = HexagonRayConfiguration(offsetDistance)

        return self

    def getVertexOffset(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        cwEdge = vertex.getEdgeClockWise()
        ccwEdge = vertex.getEdgeCounterClockWise()

        cwOffset = 0 if cwEdge not in self.walls else self.walls[cwEdge].offsetDistance
        ccwOffset = 0 if ccwEdge not in self.walls else self.walls[ccwEdge].offsetDistance

        return (cwEdge.getUnitVector(ccwOffset) - ccwEdge.getUnitVector(cwOffset)) / cos(radians(30)) * multiplier

class Hexagon:
    def __init__(self, shortDiagonal: float, height: float, centre: Vector = Vector()):
        self.shortDiagonal = shortDiagonal
        self.height = height
        self.centre = centre

        self.rayLength = shortDiagonal / 2 / cos(radians(30))
        self.side = getHexSide(shortDiagonal)

    def getSide(self):
        return getHexSide(self.shortDiagonal)

    def getDiagonal(self):
        return getDiagonal(self.shortDiagonal)

    def createRaySolid(self, configuration: HexagonConfiguration) -> Part.Solid:
        vertices = [self.getOffsetVertex(vertex, configuration.rays[vertex].offsetDistance if vertex in configuration.rays else 0) for vertex in HexTileVertices.iterate()]
        return extrudeWire(createWire(*vertices), self.height)

    def createSolid(self, multiplier: float = 1) -> Part.Solid:
        wire = createWire(*(self.getVertex(vertex, multiplier) for vertex in HexTileVertices.iterate()))
        return extrudeWire(wire, self.height)

    def createWalledSolid(self, config: HexagonConfiguration) -> Part.Solid:
        wire = createWire(*(self.getWallsIntersection(vertex, config) for vertex in HexTileVertices.iterate()))
        return extrudeWire(wire, self.height)

    def getWallsIntersection(self, vertex: HexTileVertices, config: HexagonConfiguration, multiplier: float = 1) -> Vector:
        return self.getVertex(vertex, multiplier) + config.getVertexOffset(vertex, multiplier)

    def getVertex(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        return self.getVertexVector(vertex, multiplier) + self.centre

    def getOffsetVertex(self, vertex: HexTileVertices, offset: float) -> Vector:
        return self.getOffsetVertexVector(vertex, offset) + self.centre

    def getVertexVector(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        return createVector(self.rayLength * multiplier, vertex.value)

    def getOffsetVertexVector(self, vertex: HexTileVertices, offset: float) -> Vector:
        return createVector(self.rayLength + offset, vertex.value)

    def getRayMultiplierForEdgeOffset(self, offset: float) -> float:
        return offset / sin(radians(60)) / self.rayLength

    def createGrid(self, configuration: HexagonConfiguration) -> Part.Solid:
        fuser = Fuser()

        # rays
        for vertex, config in configuration.rays.items():
            multiplier = 1 + config.offsetDistance / self.rayLength
            v = self.getVertexVector(vertex, multiplier)
            perp = createVector(configuration.rayThickness / 2, vertex.value + 90)
            wire = createWire(perp, v + perp, v - perp, -perp)
            wire.translate(self.centre)
            ray = extrudeWire(wire, self.height)
            cutRay = ray.common(self.createSolid(multiplier)) if multiplier > 1 else ray.common(self.createWalledSolid(configuration))
            fuser.fuse(cutRay)

        # walls
        for edge, config in configuration.walls.items():
            if not config.display:
                continue

            v1, v2 = edge.getVertices()

            ccwWallThicknessShift = edge.getNextCounterClockWise().getUnitVector(configuration.wallThickness * cos(radians(30)))
            cwWallThicknessShift = -edge.getNextClockWise().getUnitVector(configuration.wallThickness * cos(radians(30)))

            v1vertex = self.getWallsIntersection(v1, configuration) - edge.getUnitVector(config.offsetClockWise)
            v2vertex = self.getWallsIntersection(v2, configuration) + edge.getUnitVector(config.offsetCounterClockWise)

            wire = createWire(v1vertex, v2vertex, v2vertex + ccwWallThicknessShift, v1vertex + cwWallThicknessShift)
            fuser.fuse(extrudeWire(wire, self.height))

        # central hex
        delta = self.getRayMultiplierForEdgeOffset(configuration.rayThickness / 2)
        fuser.fuse(self.createSolid(0.5 + delta))
        fuser.cut(self.createSolid(0.5 - delta))

        return fuser.solid
