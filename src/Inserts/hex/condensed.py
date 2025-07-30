from math import tan, cos, sin, radians

import Part
from FreeCAD import Vector
from Part import Wire
from Part import show

from Inserts.common.geometry import shiftVector, createWire, createRoundedHexTile
from Inserts.hex.configuration import GridDimensions, HexTileVertices, HexTileEdges


class CondensedBoard:
    def __init__(self, dimensions: GridDimensions, rowCount: int):
        self.dimensions = dimensions
        self.rowCount = rowCount

    def getShortSegmentLength(self, startDown: bool, top: bool, segmentIndex: int = 0) -> float:
        segmentDown = self.isSegmentDown(startDown, segmentIndex)
        return self.dimensions.pinLength + (0 if (segmentDown != top) == (segmentIndex > 0) else self.dimensions.pinWidth * tan(radians(30)))

    def isSegmentDown(self, startDown: bool, segmentIndex: int = 0) -> int:
        return startDown == (segmentIndex % 2 == 0)

    def getSegmentAngle(self, startDown: bool, segmentIndex: int = 0) -> int:
        return -120 if self.isSegmentDown(startDown, segmentIndex) else -60

    def createSingleSnakeWall(self, startDown: bool, segmentCount: int, top: bool) -> list[Vector]:
        fullSegmentLength = (self.dimensions.hexWidth + self.dimensions.adjacentDistance) / 2 / sin(radians(60))

        currentPoint = Vector(0, self.dimensions.pinWidth / cos(radians(30)) if top else 0)

        points = [shiftVector(currentPoint, self.getShortSegmentLength(startDown, top), self.getSegmentAngle(startDown) + 180), currentPoint]

        for i in range(segmentCount):
            currentPoint = shiftVector(currentPoint, fullSegmentLength, self.getSegmentAngle(startDown, i + 1))
            points.append(currentPoint)

        points.append(shiftVector(currentPoint, self.getShortSegmentLength(startDown, top, segmentCount + 1), self.getSegmentAngle(startDown, segmentCount + 1)))

        return points

    def createDoubleSnakeWallWire(self, startDown: bool, segmentCount: int) -> Wire:
        topWall = self.createSingleSnakeWall(startDown, segmentCount, True)
        bottomWall = self.createSingleSnakeWall(startDown, segmentCount, False)
        bottomWall.reverse()

        points = topWall + bottomWall

        return createWire(points)

    def getRowShift(self, rowIndex: int, columnIndex: int, down: bool) -> Vector:
        distanceYa = self.dimensions.getDistanceFromHexCentreToHexCorner(self.dimensions.hexWidth + self.dimensions.pinWidth)
        y = self.getDistanceY() * rowIndex if down else self.getDistanceY() * (rowIndex - 1) + 2 * distanceYa
        x = columnIndex * (self.dimensions.hexWidth + self.dimensions.adjacentDistance) / 2
        return Vector(x, y)

    def createWalls(self):
        fusedWall = None

        for i in range(1, self.rowCount):
            startDown = i % 2 == 0 and i != self.rowCount
            segmentCount = 3 if 0 < i < self.rowCount else 2
            wire = self.createDoubleSnakeWallWire(startDown, segmentCount)
            wire.translate(self.getRowShift(i, 0 if i < self.rowCount else 1, startDown))
            face = Part.Face(wire)
            fusedWall = face if fusedWall is None else fusedWall.fuse(face)

        for i in [0, self.rowCount]:
            shift = 1 if i == self.rowCount and i % 2 == 0 else 0
            for j in range(2):
                startDown = i == 0
                wire = self.createDoubleSnakeWallWire(startDown, 0)
                wire.translate(self.getRowShift(i, j * 2 + shift, startDown))
                face = Part.Face(wire)
                fusedWall = face if fusedWall is None else fusedWall.fuse(face)

        return fusedWall.extrude(Vector(0, 0, self.dimensions.pinHeight + self.dimensions.floorThickness))

    def getDistanceY(self):
        sameRowHexDistanceX = self.dimensions.hexWidth + self.dimensions.adjacentDistance
        return (self.dimensions.hexWidth + self.dimensions.pinWidth) / cos(radians(30)) - sameRowHexDistanceX / 2 * tan(radians(30))

    def createFloor(self):
        fusedFace = None
        sameRowHexDistanceX = self.dimensions.hexWidth + self.dimensions.adjacentDistance
        evenRowsShiftX = self.dimensions.hexWidth / 2
        for i in range(self.rowCount):
            for j in range(2):
                shallowEdges = [HexTileEdges.W] if j == 0 else [HexTileEdges.E]
                roundedVertices = [HexTileVertices.NW, HexTileVertices.SW] if j == 0 else [HexTileVertices.NE, HexTileVertices.SE]
                wire = createRoundedHexTile(self.dimensions.hexWidth, self.dimensions.pinRadius, roundedVertices, shallowEdges)
                wire.translate(Vector(evenRowsShiftX * (i % 2) + sameRowHexDistanceX * j, i * self.getDistanceY()))
                face = Part.Face(wire)
                fusedFace = face if fusedFace is None else fusedFace.fuse(face)
        y = self.dimensions.getDistanceFromHexCentreToOuterPinAngle()
        fusedFace.translate(Vector(0, y))

        return fusedFace.extrude(Vector(0, 0, self.dimensions.floorThickness))
        # return fusedFace.extrude(Vector(0, 0, self.dimensions.pinHeight + self.dimensions.floorThickness))

    def createBoard(self):
        outerBound = self.createFloor()
        floorFeature = Part.show(outerBound, "floor v2")
        floorFeature.ViewObject.ShapeColor = (0.4, 0.8, 0.4)

        wall = self.createWalls()
        wallFeature = show(wall, "wall")
        wallFeature.ViewObject.ShapeColor = (0.2, 0.2, 0.7)
