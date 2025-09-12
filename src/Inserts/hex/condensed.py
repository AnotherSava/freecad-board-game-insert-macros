from math import tan, cos, sin, radians, ceil, floor

import Part
from FreeCAD import Vector
from Part import Wire

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser
from Inserts.common.geometry import shiftVector, createWire, invertX, extrudeWire
from Inserts.common.hexes import createRoundedHexTileWire, createRoundedHexTile, createCustomRoundedHexTile
from Inserts.common.pencil import Pencil
from Inserts.hex.configuration import HexTileVertices, HexTileEdges
from dataclasses import dataclass


@dataclass
class GridDimensions:
    hexWidth: float
    pinWidth: float
    pinLength: float
    pinRadius: float
    pinHeight: float
    floorThickness: float
    ceilingThickness: float
    adjacentDistance: float # distance between horizontally adjacent tiles
    magnetDiameter: float
    magnetHeightFloor: float
    magnetHeightCeiling: float
    thinnestWall: float
    maxRowsPerMagnet: int
    lidHoleAngle: float
    lidHoleMultiplier: float

    def getHexSide(self):
        return self.hexWidth * tan(radians(30))

    def getDistanceFromHexCentreToOuterPinAngle(self):
        return self.getDistanceFromHexCentreToHexCorner(self.pinWidth * 2 + self.hexWidth)

    def getDistanceFromHexCentreToHexCorner(self, hexWidth: float):
        return hexWidth / 2 / cos(radians(30))

    def getCondensedDistanceY(self):
        return (self.hexWidth + self.pinWidth) / cos(radians(30)) - self.getCondensedDistanceX() / 2 * tan(radians(30))

    def getCondensedDistanceX(self):
        return self.hexWidth + self.adjacentDistance

    def getHexCentre(self, row: int, column: int) -> Vector:
        sameRowHexDistanceX = self.hexWidth + self.adjacentDistance
        evenRowsShiftX = (self.hexWidth + self.adjacentDistance) / 2
        return Vector(evenRowsShiftX * (row % 2) + sameRowHexDistanceX * column, row * self.getCondensedDistanceY() + self.getDistanceFromHexCentreToOuterPinAngle())

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

        return fuser.solid

    def createMagnetHole(self, vector: Vector, top: bool, magnetHeight: float):
        longerSideDelta = (self.dimensions.magnetDiameter / 2) * (1 + tan(radians(30)))
        holeWidth = self.dimensions.pinWidth - self.dimensions.thinnestWall
        shorterSideDelta = longerSideDelta - holeWidth * tan(radians(30))

        pencil = Pencil()
        pencil.draw(longerSideDelta, 60)
        pencil.draw(holeWidth, -30)
        pencil.draw(shorterSideDelta, -120)
        pencil.draw(shorterSideDelta, -60)
        pencil.draw(holeWidth, -150)
        hole = pencil.extrude(magnetHeight)

        hole.translate(Vector(0, self.dimensions.thinnestWall / cos(radians(30))))

        if top:
            hole.rotate(Vector(0, 0, 0), Vector(0, 0, 1), 180)
        hole.translate(vector)

        return hole

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

        return fuser.solid

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

    def createFloor(self, floorThickness: float, straightEdges = False) -> Fuser:
        fuser = Fuser()
        for i in range(self.rowCount):
            for j in range(2):
                shallowEdges = [] if straightEdges else [HexTileEdges.W] if j == 0 else [HexTileEdges.E]
                roundedVertices = self.chooseRoundedVertices(j, i, self.rowCount)
                fuser.fuse(createRoundedHexTile(self.dimensions.hexWidth, floorThickness, self.dimensions.getHexCentre(i, j), self.dimensions.pinRadius, roundedVertices, shallowEdges))

        return fuser

    def createWalls(self, height: float, magnetsTop: bool, magnetHeight: float, colourWalls: Colour) -> MultiColourFuser:
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)
        fuser = MultiColourFuser()

        fuser.fuseAll(wallFactory.createWalls(height, colourWalls, Colour.BASE))
        fuser.fuse(colourWalls, wallFactory.createDividerWalls(height))

        magnetHoles = wallFactory.createMagnetHoles(magnetHeight)
        if magnetsTop:
            magnetHoles = magnetHoles.translate(Vector(0, 0, height - magnetHeight))
        fuser.cut(magnetHoles)

        return fuser

    def createBoard(self) -> MultiColourFuser:
        fuser = MultiColourFuser()
        fuser.fuse(Colour.BASE, self.createFloor(self.dimensions.floorThickness))
        fuser.fuseAll(self.createWalls(self.dimensions.pinHeight + self.dimensions.floorThickness, True, self.dimensions.magnetHeightFloor, Colour.BASE))
        return fuser

    def createSingleHandleHexRecess(self, orientation: float) -> Fuser:
        height = self.dimensions.ceilingThickness + self.dimensions.magnetHeightCeiling
        centre = (self.dimensions.getHexCentre(0, 0) + self.dimensions.getHexCentre(self.rowCount - 1, 1)) / 2
        tileCentre = self.dimensions.getHexCentre(int(self.rowCount / 2), 1)

        shallowEdges = []
        roundedVertices = list(HexTileVertices)

        shift = height * cos(radians(self.dimensions.lidHoleAngle))
        extrusionVector = -Vector(shift * cos(radians(60)), shift * sin(radians(60)), height)
        fuser = Fuser(createCustomRoundedHexTile(self.dimensions.hexWidth * self.dimensions.lidHoleMultiplier, extrusionVector, tileCentre, self.dimensions.pinRadius, roundedVertices, shallowEdges))

        return fuser.rotate(centre, Vector(0, 0, 1), orientation).translate(Vector(0, 0, height))

    def createHandleRecess(self) -> Part.Solid:
        assert self.rowCount % 2 == 0

        fuser = Fuser()
        for orientation in [0, 180]:
            fuser.fuse(self.createSingleHandleHexRecess(orientation))

        return fuser.solid

    def createLid(self) -> MultiColourFuser:
        height = self.dimensions.ceilingThickness + self.dimensions.magnetHeightCeiling

        fuser = MultiColourFuser(Colour.WALLED_MESH, self.createFloor(height, True))

        fuser.fuseAll(self.createWalls(height, False, self.dimensions.magnetHeightCeiling, Colour.WALLED_MESH))

        fuser.cut(self.createHandleRecess())

        return fuser