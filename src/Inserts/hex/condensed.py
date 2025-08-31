from math import tan, cos, sin, radians, ceil, floor

import Part
from FreeCAD import Vector
from Part import Wire

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser
from Inserts.common.geometry import shiftVector, createWire, invertX, extrudeWire
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
            if i == segmentCount - 1:
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

    def createWalls(self, height: float, colourBase: Colour, colourMagnets: Colour) -> MultiColourFuser:
        indices = self.getExtraMagnetRowIndices()
        fuser = MultiColourFuser()

        for row in range(1, self.rowCount):
            startDown = row % 2 == 0
            wire = self.createDoubleSnakeWallWire(startDown, 3)
            wire.translate(self.getRowShift(row, 0, startDown))
            fuser.fuse(colourBase, extrudeWire(wire, height))

        for row in [0, self.rowCount]:
            shift = 1 if row == self.rowCount and row % 2 == 0 else 0
            startDown = row == 0
            for j in range(2):
                wire = self.createDoubleSnakeWallWire(startDown, 0)
                wire.translate(self.getRowShift(row, j * 2 + shift, startDown))
                fuser.fuse(colourMagnets, extrudeWire(wire, height))

        for row in indices:
            for j in range(2):
                startDown = (row + j) % 2 == 0
                wire = self.createDoubleSnakeWallWire(startDown, 0)
                wire.translate(self.getRowShift(row, j * 3, startDown))
                fuser.replace(colourMagnets, extrudeWire(wire, height))

        return fuser

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

    def roundTowardsCentre(self, number: float, centre: float) -> int:
        return ceil(number) if number < centre else floor(number)

    def getExtraMagnetRowIndices(self) -> list[int]:
        extraMagnetRowCount = ceil(self.rowCount / self.dimensions.maxRowsPerMagnet) - 1

        spacing = self.rowCount / (extraMagnetRowCount + 1)
        centre = self.rowCount / 2

        return [self.roundTowardsCentre((i + 1) * spacing, centre) for i in range(extraMagnetRowCount)]

    def createMagnetHoles(self, magnetHeight: float) -> Part.Solid:
        fuser = Fuser()

        for i in self.getExtraMagnetRowIndices():
            startDown = i % 2 == 0
            magnetHoles = self.createMagnetHolesWall(startDown, 3, magnetHeight)
            magnetHoles = magnetHoles.translate(self.getRowShift(i, 0, startDown))
            fuser.fuse(magnetHoles)

        for i in [0, self.rowCount]:
            shift = 1 if i == self.rowCount and i % 2 == 0 else 0
            for j in range(2):
                startDown = i == 0
                magnetHoles = self.createMagnetHolesWall(startDown, 0, magnetHeight)
                magnetHoles = magnetHoles.translate(self.getRowShift(i, j * 2 + shift, startDown))
                fuser.fuse(magnetHoles)

        return fuser.getResult()

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
        fuser = Fuser()
        for i in range(self.rowCount):
            for j in range(2):
                shallowEdges = [HexTileEdges.W] if j == 0 else [HexTileEdges.E]
                roundedVertices = self.chooseRoundedVertices(j, i, self.rowCount)
                wire = createRoundedHexTile(hexWidth or self.dimensions.hexWidth, self.dimensions.pinRadius, roundedVertices, shallowEdges)
                wire.translate(self.dimensions.getHexCentre(i, j))
                face = Part.Face(wire)
                fuser.fuse(face)

        return fuser.getResult().extrude(Vector(0, 0, floorThickness or self.dimensions.floorThickness))

    def createMagneticLidLedge(self) -> MultiColourFuser:
        hexesLedge = self.createFloor(self.dimensions.ceilingLedgeThickness, self.dimensions.hexWidth - self.dimensions.ceilingLedgeDelta * 2)
        hexesLedge.translate(Vector(0, 0, -self.dimensions.ceilingLedgeThickness - 0.05))
        return MultiColourFuser(Colour.MESH, hexesLedge)

    def createWalls(self, height: float, magnetsTop: bool, magnetHeight: float, colourBase: Colour, colourMagnets: Colour) -> MultiColourFuser:
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)
        fuser = MultiColourFuser()

        fuser.fuseAll(wallFactory.createWalls(height, colourBase, colourMagnets))
        fuser.fuse(colourBase, wallFactory.createDividerWalls(height))

        if magnetHeight is not None:
            magnetHoles = wallFactory.createMagnetHoles(magnetHeight)
            if magnetsTop:
                magnetHoles = magnetHoles.translate(Vector(0, 0, height - magnetHeight))
            fuser.cut(magnetHoles)

        return fuser

    def createBoard(self) -> MultiColourFuser:
        fuser = MultiColourFuser()
        fuser.fuse(Colour.BLACK, self.createFloor())
        fuser.fuseAll(self.createWalls(self.dimensions.pinHeight + self.dimensions.floorThickness, True, self.dimensions.magnetHeightFloor, Colour.BLACK, Colour.BLACK))
        return fuser

    def createLid(self):
        height = self.dimensions.ceilingThickness + self.dimensions.magnetHeightCeiling

        fuser = MultiColourFuser(Colour.WALLED_MESH, self.createFloor(height))

        fuser.fuseAll(self.createWalls(height, False, self.dimensions.magnetHeightCeiling, Colour.WALLED_MESH, Colour.BLACK))
        fuser.fuseAll(self.createMagneticLidLedge())

        fuser.show(40)
