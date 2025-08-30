from math import cos, radians, tan

import Part

from Inserts.common.geometry import shiftVector
from Inserts.hex.configuration import HexTileVertices, HexTileEdges


def createRoundedHexTile(tileWidth: float, roundingRadius: float = 0, roundedVertices: list[HexTileVertices] = [], shallowEdges: list[HexTileEdges] = []):
    # Align arc shortening distance with one in createPinRayWire
    arcOffset = roundingRadius / 2 / cos(radians(30))

    edges = list()

    # Create shortened edges with arc connections
    for currentVertex in HexTileVertices.iterate():
        nextVertex = currentVertex.getNextCounterClockWise()

        # Shorten the edge by arcOffset at each end if needed
        v1 = currentVertex.getVector(tileWidth)
        edgeCounterClockWise = currentVertex.getEdgeCounterClockWise()
        if currentVertex in roundedVertices:
            v1 += edgeCounterClockWise.getUnitVector() * arcOffset

        v2 = nextVertex.getVector(tileWidth)
        if nextVertex in roundedVertices:
            v2 -= edgeCounterClockWise.getUnitVector() * arcOffset

        # Add edge
        if edgeCounterClockWise in shallowEdges:
            arcMid = shiftVector((v2 + v1) / 2, (v2 - v1).Length / 2 * tan(radians(15)), edgeCounterClockWise.value + 90)
            edges.append(Part.Arc(v1, arcMid, v2).toShape())
        else:
            edges.append(Part.LineSegment(v1, v2).toShape())

        if nextVertex in roundedVertices:
            # Add arc at the corner connecting this edge to the next
            arcStart = v2
            arcEnd = nextVertex.getVector(tileWidth) + nextVertex.getEdgeCounterClockWise().getUnitVector() * arcOffset
            arcMidOffset = roundingRadius * (1 - cos(radians(30)))
            arcMid = (arcStart + arcEnd) / 2 + nextVertex.getUnitVector() * arcMidOffset

            edges.append(Part.Arc(arcStart, arcMid, arcEnd).toShape())

    return Part.Wire(edges)
