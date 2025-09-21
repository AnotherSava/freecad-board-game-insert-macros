from math import cos, sin, acos, radians, degrees, tan

from FreeCAD import Vector
import Part

from Inserts.common import fuser
from Inserts.common.fuser import Fuser
from Inserts.common.geometry import createWire, extrudeWire, createVector
from Inserts.common.hexes import getHexSide
from Inserts.hex.configuration import HexTileVertices, HexTileEdges
from dataclasses import dataclass


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
    def __init__(self, height: float, rayThickness: float = None, wallThickness: float = None):
        self.height = height
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
    def __init__(self, length: float, height: float, centre: Vector = Vector()):
        self.length = length
        self.height = height
        self.centre = centre

        self.rayLength = length / 2 / cos(radians(30))
        self.side = getHexSide(length)

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

    def getVertexVector(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        return createVector(self.rayLength * multiplier, vertex.value)

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
            ray = extrudeWire(wire, configuration.height)
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
            fuser.fuse(extrudeWire(wire, configuration.height))

        # central hex
        delta = self.getRayMultiplierForEdgeOffset(configuration.rayThickness / 2)
        fuser.fuse(self.createSolid(0.5 + delta))
        fuser.cut(self.createSolid(0.5 - delta))

        return fuser.solid
