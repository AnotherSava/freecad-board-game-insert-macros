from math import radians, tan, sin, cos

import Part
from FreeCAD import Vector

from Inserts.common.pencil import Pencil
from Inserts.hex.configuration import HexTileVertices, HexTileEdges


def getHexSide(shortDiagonal: float):
    return shortDiagonal * tan(radians(30))

def getDiagonal(shortDiagonal: float = None):
    return shortDiagonal / cos(radians(30))

def getDistanceY(shortDiagonal: float, shortDiagonalGap: float, diagonalGap: float = None):
    diagonalGap = shortDiagonalGap if diagonalGap is None else diagonalGap
    return diagonalGap / cos(radians(30)) - shortDiagonalGap / 2 * tan(radians(30)) + getDiagonal(shortDiagonal) / 2 + getHexSide(shortDiagonal) / 2

def drawAroundVertex(pencil: Pencil, vertex: HexTileVertices, roundingRadius: float, isRound: bool):
    roundingDelta = roundingRadius * tan(radians(30))

    if isRound:
        pencil.arcWithRadius(roundingRadius, vertex.getEdgeClockWise().value + 90, 60)
    else:
        pencil.draw(roundingDelta, vertex.getEdgeClockWise().value)
        pencil.draw(roundingDelta, vertex.getEdgeCounterClockWise().value)

def createRoundedHexTile(tileLength: float, tileHeight: float, centre: Vector, roundingRadius: float, shallowEdgeAngle: float, shorterSideMultiplier: float, roundedVertices: list[HexTileVertices], shallowEdges: list[HexTileEdges]) -> Part.Solid:
    roundingDelta = roundingRadius * tan(radians(30))
    pencil = Pencil(centre + HexTileVertices.N.getVector(tileLength))

    for vertex in [HexTileVertices.NW, HexTileVertices.SE]:
        sideEdge = vertex.getEdgeCounterClockWise()
        side = getHexSide(tileLength)
        edgeLength = side - roundingDelta * 2

        if sideEdge in shallowEdges:
            edgeLength = side * shorterSideMultiplier + (tileLength / cos(radians(30))) * (1 - shorterSideMultiplier) - roundingDelta * 2
            side *= shorterSideMultiplier

        pencil.draw(side - roundingDelta, vertex.getEdgeClockWise().value)
        drawAroundVertex(pencil, vertex, roundingRadius, vertex in roundedVertices)

        if sideEdge not in shallowEdges:
            pencil.draw(edgeLength, sideEdge.value)
        else:
            r2 = (edgeLength / 2) / sin(radians(shallowEdgeAngle / 2)) - roundingRadius
            pencil.arcWithRadius(roundingRadius, sideEdge.value + 90, shallowEdgeAngle / 2)
            pencil.arcWithRadius(r2, sideEdge.value - 90 + shallowEdgeAngle / 2, -shallowEdgeAngle)
            pencil.arcWithRadius(roundingRadius, sideEdge.value + 90 - shallowEdgeAngle / 2, shallowEdgeAngle / 2)

        nextVertex = vertex.getNextCounterClockWise()
        drawAroundVertex(pencil, nextVertex, roundingRadius, nextVertex in roundedVertices)
        pencil.draw(side - roundingDelta, nextVertex.getEdgeCounterClockWise().value)

    return pencil.extrude(tileHeight)
