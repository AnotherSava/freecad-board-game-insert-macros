from math import cos, sin, acos, radians, degrees, tan

from FreeCAD import Vector
import Part

from Inserts.common.fuser import Fuser
from Inserts.common.geometry import createWire, extrudeWire, createVector
from Inserts.hex.configuration import HexTileVertices, HexTileEdges
from dataclasses import dataclass


@dataclass
class HexagonWallConfiguration:
    offsetDistance: float
    offsetClockWise: float
    offsetCounterClockWise: float


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

    def withWalls(self, offsetDistance: float = 0, offsetClockWise: float = 0, offsetCounterClockWise: float = 0, *edges: HexTileEdges) -> 'HexagonConfiguration':
        for edge in edges if len(edges) > 0 else HexTileEdges:
            self.walls[edge] = HexagonWallConfiguration(offsetDistance, offsetClockWise, offsetCounterClockWise)

        return self

    def withRays(self, offsetDistance: float = 0, *vertices: HexTileVertices) -> 'HexagonConfiguration':
        for vertex in vertices if len(vertices) > 0 else HexTileVertices:
            self.rays[vertex] = HexagonRayConfiguration(offsetDistance)

        return self


class Hexagon:
    def __init__(self, length: float, height: float, centre: Vector = Vector()):
        self.rayLength = length / 2 / cos(radians(30))
        self.height = height
        self.centre = centre

    def createSolid(self, multiplier: float = 1) -> Part.Solid:
        wire = createWire(*(self.getVertex(vertex, multiplier) for vertex in HexTileVertices.iterate()))
        return extrudeWire(wire, self.height)

    def getVertex(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        return self.getVertexVector(vertex, multiplier) + self.centre

    def getVertexVector(self, vertex: HexTileVertices, multiplier: float = 1) -> Vector:
        return createVector(self.rayLength * multiplier, vertex.value)

    def getEdgeVector(self, edge: HexTileEdges) -> Vector:
        v1, v2 = edge.getVertices()
        return self.getVertexVector(v1) - self.getVertexVector(v2)

    def getRayMultiplierForEdgeOffset(self, offset: float) -> float:
        return offset / sin(radians(60)) / self.rayLength

    def createGrid(self, configuration: HexagonConfiguration) -> Part.Solid:
        fuser = Fuser()
        for vertex, config in configuration.rays.items():
            multiplier = 1 + config.offsetDistance / self.rayLength
            v = self.getVertexVector(vertex, multiplier)
            perp = v.cross(Vector(0, 0, 1)).normalize() * configuration.rayThickness / 2
            wire = createWire(perp, v + perp, v - perp, -perp)
            wire.translate(self.centre)
            ray = extrudeWire(wire, configuration.height)
            fuser.fuse(ray.common(self.createSolid(multiplier)))

        for edge, config in configuration.walls.items():
            v1, v2 = edge.getVertices()

            d3 = self.getEdgeVector(edge.getNextCounterClockWise()).normalize() * configuration.wallThickness * cos(radians(30))
            d4 = self.getEdgeVector(edge.getNextClockWise()).normalize() * configuration.wallThickness * cos(radians(30))

            d5 = self.getEdgeVector(edge).normalize() * config.offsetClockWise
            d6 = -self.getEdgeVector(edge).normalize() * config.offsetCounterClockWise

            wire = createWire(self.getVertex(v1) + d5, self.getVertex(v2) + d6, self.getVertex(v2) - d3 + d6, self.getVertex(v1) + d4 + d5)
            fuser.fuse(extrudeWire(wire, configuration.height))

        multiplier = self.getRayMultiplierForEdgeOffset(configuration.rayThickness / 2)
        fuser.fuse(self.createSolid(0.5 + multiplier))
        fuser.cut(self.createSolid(0.5 - multiplier))

        return fuser.solid
