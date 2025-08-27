from math import tan, cos, sin, radians

import Part
import copy
from FreeCAD import Vector
from Part import Wire, Shape, show

from Inserts.common.fuser import Fuser
from Inserts.common.geometry import shiftVector, createWire, invertX
from Inserts.common.hexes import createRoundedHexTile
from Inserts.common.pencil import Pencil
from Inserts.hex.configuration import GridDimensions, HexTileVertices, HexTileEdges


class CondensedWalls:
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

    def createMagnetHolesWall(self, startDown: bool, segmentCount: int, magnetHeight: float):
        pinWidthY = self.dimensions.pinWidth / cos(radians(30))

        fullSegmentLength = (self.dimensions.hexWidth + self.dimensions.adjacentDistance) / 2 / sin(radians(60))

        wallAngleFacingUp = not startDown
        currentPoint = Vector(0, pinWidthY if wallAngleFacingUp else 0)
        fusedMagnetHoles = self.createMagnetHole(currentPoint, wallAngleFacingUp, magnetHeight)

        for i in range(segmentCount):
            wallAngleFacingUp = not wallAngleFacingUp
            currentPoint = shiftVector(shiftVector(currentPoint, fullSegmentLength, self.getSegmentAngle(startDown, i + 1)), pinWidthY, 0 if wallAngleFacingUp else 180)
            fusedMagnetHoles = fusedMagnetHoles.fuse(self.createMagnetHole(currentPoint, wallAngleFacingUp, magnetHeight))

        return fusedMagnetHoles

    def createDoubleSnakeWallWire(self, startDown: bool, segmentCount: int) -> Wire:
        topWall = self.createSingleSnakeWall(startDown, segmentCount, True)
        bottomWall = self.createSingleSnakeWall(startDown, segmentCount, False)
        bottomWall.reverse()

        points = topWall + bottomWall

        return createWire(points)

    def getRowShift(self, rowIndex: int, columnIndex: int, down: bool) -> Vector:
        distanceYa = self.dimensions.getDistanceFromHexCentreToHexCorner(self.dimensions.hexWidth + self.dimensions.pinWidth)
        y = self.dimensions.getCondensedDistanceY() * rowIndex if down else self.dimensions.getCondensedDistanceY() * (rowIndex - 1) + 2 * distanceYa
        x = columnIndex * (self.dimensions.hexWidth + self.dimensions.adjacentDistance) / 2
        return Vector(x, y)

    def createInnerWalls(self, height: float):
        fusedWall = None

        for i in range(1, self.rowCount):
            startDown = i % 2 == 0
            wire = self.createDoubleSnakeWallWire(startDown, 3)
            wire.translate(self.getRowShift(i, 0, startDown))
            face = Part.Face(wire)
            fusedWall = face if fusedWall is None else fusedWall.fuse(face)

        return fusedWall.extrude(Vector(0, 0, height))

    def createOuterWalls(self, height: float):
        fusedWall = None

        for i in [0, self.rowCount]:
            shift = 1 if i == self.rowCount and i % 2 == 0 else 0
            for j in range(2):
                startDown = i == 0
                wire = self.createDoubleSnakeWallWire(startDown, 0)
                wire.translate(self.getRowShift(i, j * 2 + shift, startDown))
                face = Part.Face(wire)
                fusedWall = face if fusedWall is None else fusedWall.fuse(face)

        return fusedWall.extrude(Vector(0, 0, height))

    def createDividerWall(self, height: float) -> Part.Solid:
        side = self.dimensions.adjacentDistance / 2 / sin(radians(60))

        pencil = Pencil()
        pencil.draw(side, -60)
        pencil.draw(side, -120)
        pencil.up(self.dimensions.getHexSide())
        pencil.draw(side, 120)
        pencil.draw(side, 60)
        return pencil.extrude(height)

    def createDividerWalls(self, height: float) -> Part.Solid:
        fuser = Fuser()

        for row in range(self.rowCount):
            wallDivider = self.createDividerWall(height)
            x = self.dimensions.getCondensedDistanceX() / 2 * (row % 2) + self.dimensions.hexWidth / 2
            y = self.dimensions.getCondensedDistanceY() * row + self.dimensions.getDistanceFromHexCentreToOuterPinAngle() - self.dimensions.getHexSide() / 2
            wallDivider.translate(Vector(x, y))
            fuser.fuse(wallDivider)

        return fuser.getResult()

    def createMagnetHole(self, vector: Vector, top: bool, magnetHeight: float):
        v1 = Vector(0, -self.dimensions.extruderWidth / cos(radians(30)))
        v2 = shiftVector(v1, self.dimensions.magnetDiameter / 2 * (1 + tan(radians(30))), -120)
        v3 = shiftVector(v2, self.dimensions.pinWidth - self.dimensions.extruderWidth, 150)
        v4 = invertX(v3)
        v5 = invertX(v2)

        wire = createWire([v1, v2, v3, v4, v5])
        if not top:
            wire = wire.rotate(Vector(0, 0, 0), Vector(0, 0, 1), 180)
        wire = wire.translate(vector)
        face = Part.Face(wire)

        return face.extrude(Vector(0, 0, magnetHeight))

    def createMagnetCylindricalHole(self, vector: Vector, top: bool):
        # equal distance from the outside
        magnetShift = self.dimensions.pinWidth / cos(radians(30)) / (cos(radians(30)) + 1)
        location = shiftVector(vector, magnetShift, 180 if top else 0)

        return Part.makeCylinder(self.dimensions.magnetDiameter / 2, self.dimensions.magnetHeightFloor, location)

    def createMagnetHoles(self, magnetHeight: float):
        fusedMagnetHoles = None

        for i in range(1, self.rowCount):
            startDown = i % 2 == 0
            magnetHoles = self.createMagnetHolesWall(startDown, 3, magnetHeight)
            magnetHoles = magnetHoles.translate(self.getRowShift(i, 0, startDown))
            fusedMagnetHoles = magnetHoles if fusedMagnetHoles is None else fusedMagnetHoles.fuse(magnetHoles)

        for i in [0, self.rowCount]:
            shift = 1 if i == self.rowCount and i % 2 == 0 else 0
            for j in range(2):
                startDown = i == 0
                magnetHoles = self.createMagnetHolesWall(startDown, 0, magnetHeight)
                magnetHoles = magnetHoles.translate(self.getRowShift(i, j * 2 + shift, startDown))
                fusedMagnetHoles = fusedMagnetHoles.fuse(magnetHoles)

        return fusedMagnetHoles

class CondensedBoard:
    def __init__(self, dimensions: GridDimensions, rowCount: int):
        self.dimensions = dimensions
        self.rowCount = rowCount

    def chooseRoundedVertices(self, column: int, row: int, rowCount: int):
        if column == 0:
            if row % 2 == 0:
                return [HexTileVertices.NW, HexTileVertices.SW]
            if row == rowCount - 1:
                return [HexTileVertices.NW]

        else:
            if row % 2 == 1:
                return [HexTileVertices.SE, HexTileVertices.NE]
            if row == 0:
                return [HexTileVertices.SE]
            if row == rowCount - 1:
                return [HexTileVertices.NE]

        return []

    def createFloor(self, floorThickness: float = None, hexWidth: float = None):
        fusedFace = None
        sameRowHexDistanceX = self.dimensions.hexWidth + self.dimensions.adjacentDistance
        evenRowsShiftX = (self.dimensions.hexWidth +self.dimensions.adjacentDistance) / 2
        for i in range(self.rowCount):
            for j in range(2):
                shallowEdges = [HexTileEdges.W] if j == 0 else [HexTileEdges.E]
                roundedVertices = self.chooseRoundedVertices(j, i, self.rowCount)
                wire = createRoundedHexTile(hexWidth or self.dimensions.hexWidth, self.dimensions.pinRadius, roundedVertices, shallowEdges)
                wire.translate(Vector(evenRowsShiftX * (i % 2) + sameRowHexDistanceX * j, i * self.dimensions.getCondensedDistanceY()))
                face = Part.Face(wire)
                fusedFace = face if fusedFace is None else fusedFace.fuse(face)
        y = self.dimensions.getDistanceFromHexCentreToOuterPinAngle()
        fusedFace.translate(Vector(0, y))

        return fusedFace.extrude(Vector(0, 0, floorThickness or self.dimensions.floorThickness))

    def createCeiling(self) -> Shape:
        hexes = self.createFloor()
        ceilingDimensions = copy.copy(self.dimensions)
        ceilingDimensions.pinLength = ceilingDimensions.pinLength + 1.5

        wallsFactory = CondensedWalls(ceilingDimensions, self.rowCount)

        walls = wallsFactory.createInnerWalls(self.dimensions.pinHeight + self.dimensions.floorThickness)
        walls.translate(Vector(0, 0, -self.dimensions.pinHeight))
        return hexes.fuse(walls).removeSplitter()

    def createMagneticCeiling(self) -> Shape:
        ceiling = self.createFloor(self.dimensions.ceilingThickness + self.dimensions.magnetHeightCeiling)
        walls = self.createWalls(self.dimensions.ceilingThickness + self.dimensions.magnetHeightCeiling, False, self.dimensions.magnetHeightCeiling)
        ceiling = ceiling.fuse(walls)

        hexesLedge = self.createFloor(self.dimensions.ceilingLedgeThickness, self.dimensions.hexWidth - self.dimensions.ceilingLedgeDelta * 2)
        hexesLedge = hexesLedge.translate(Vector(0, 0, -self.dimensions.ceilingLedgeThickness))
        ceiling = ceiling.fuse(hexesLedge)

        # hexesHollow = self.createFloor(self.dimensions.ceilingThickness + self.dimensions.ceilingLedgeThickness - self.dimensions.floorThickness, self.dimensions.hexWidth - self.dimensions.ceilingHollowDelta * 2)
        # hexesHollow = hexesHollow.translate(Vector(0, 0, self.dimensions.floorThickness - self.dimensions.ceilingLedgeThickness))
        # ceiling = ceiling.cut(hexesHollow)

        # walls.translate(Vector(0, 0, -self.dimensions.pinHeight))

        return ceiling

    def createWalls(self, height: float, magnetsTop: bool, magnetHeight: float):
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)
        walls = wallFactory.createOuterWalls(height)

        if magnetHeight is not None:
            magnetHoles = wallFactory.createMagnetHoles(magnetHeight)
            if magnetsTop:
                magnetHoles = magnetHoles.translate(Vector(0, 0, height - magnetHeight))
            walls = walls.cut(magnetHoles)

        innerWall = wallFactory.createInnerWalls(height)

        dividerWalls = wallFactory.createDividerWalls(height)
        walls = walls.fuse(innerWall).fuse(dividerWalls)

        return walls

    def createBoard(self):
        floor = self.createFloor()
        floorFeature = Part.show(floor, "floor v2")
        floorFeature.ViewObject.ShapeColor = (0.4, 0.8, 0.4)

        walls = self.createWalls(self.dimensions.pinHeight + self.dimensions.floorThickness, True, self.dimensions.magnetHeightFloor)
        wallFeature = show(walls, "wall")
        wallFeature.ViewObject.ShapeColor = (0.2, 0.2, 0.7)
        wallFeature.ViewObject.Transparency = 50

        # magnetHolesFeature = show(magnetHoles, "magnet holes")
        # magnetHolesFeature.ViewObject.ShapeColor = (0.2, 0.7, 0.7)

    def createLid(self):
        # ceiling = self.createCeiling()
        # ceiling.translate(Vector(0, 0, self.dimensions.pinHeight + self.dimensions.floorThickness))
        # ceiling = ceiling.cut(walls)
        # ceilingFeature = Part.show(ceiling, "floor v2")
        # ceilingFeature.ViewObject.ShapeColor = (0.8, 0.4, 0.4)
        # ceilingFeature.ViewObject.Transparency = 50

        ceiling = self.createMagneticCeiling()
        # ceiling = ceiling.translate(Vector(0, 0, self.dimensions.pinHeight * 2))
        ceilingFeature = Part.show(ceiling, "ceiling")
        ceilingFeature.ViewObject.ShapeColor = (0.8, 0.4, 0.4)
        # ceilingFeature.ViewObject.Transparency = 50

