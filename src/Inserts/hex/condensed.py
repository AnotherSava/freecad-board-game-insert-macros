import math
from math import tan, cos, sin, radians, ceil, floor

import Part
from FreeCAD import Vector
from Part import Wire

from Inserts.common import magnets
from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuse
from Inserts.common.geometry import shiftVector, createWire, extrudeWire
from Inserts.common.hexagon import Hexagon, HexagonConfiguration
from Inserts.common.hexes import createRoundedHexTile
from Inserts.common.magnets import MagnetDetails, getWidestRadius
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
    lidInfillThickness: float
    lidExternalWallThickness: float

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

    def getLidHeight(self) -> float:
        return self.ceilingThickness + self.magnetHeightCeiling

    def getMagnetHoleLocation(self, row: int, column: int) -> Vector:
        hexCentreToHoleUp = Vector(0, self.getDistanceFromHexCentreToOuterPinAngle() - getWidestRadius(self.magnetDiameter, self.thinnestWall) / cos(radians(30)))
        if (row + column) % 2 == 0: # magnet is on the bottom of the hex
            hexCentre = self.getHexCentre(row, math.floor(column / 2))
            return hexCentre - hexCentreToHoleUp
        else: # magnet is on the top of the hex
            hexCentre = self.getHexCentre(row - 1, math.floor(column / 2))
            return hexCentre + hexCentreToHoleUp

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

        return createWire(*points)

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

    def createMagnetHoles(self, magnetHeight: float, magnetOnTop: bool, baseHeight: float) -> (Part.Solid, Part.Solid):
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)

        magnetDetails = []

        for i in wallFactory.getExtraMagnetRowIndices():
            magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(i, 0)))
            magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(i, 3)))

        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(0, 0)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(0, 2)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(self.rowCount, 1)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(self.rowCount, 3)))

        return magnets.createMagnetHolders(self.dimensions.magnetDiameter, magnetHeight, magnetOnTop, baseHeight, self.dimensions.thinnestWall, magnetDetails)

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

    def createWalls(self, height: float, magnetsTop: bool, magnetHeight: float, colourWalls: Colour) -> (MultiColourFuser, Part.Solid):
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)
        fuser = MultiColourFuser()

        fuser.fuseAll(wallFactory.createWalls(height, colourWalls, Colour.BASE))
        fuser.fuse(colourWalls, wallFactory.createDividerWalls(height))

        magnetHoles = wallFactory.createMagnetHoles(magnetHeight)
        if magnetsTop:
            magnetHoles = magnetHoles.translate(Vector(0, 0, height - magnetHeight))
        fuser.cut(magnetHoles)

        return fuser, magnetHoles

    def createBoard(self) -> MultiColourFuser:
        fuser = MultiColourFuser()
        fuser.fuse(Colour.BASE, self.createFloor(self.dimensions.floorThickness))
        fuser.fuseAll(self.createWalls(self.dimensions.pinHeight + self.dimensions.floorThickness, True, self.dimensions.magnetHeightFloor, Colour.BASE))
        return fuser

    def createHexagon(self, row: int, column: int) -> Hexagon:
        return Hexagon(self.dimensions.hexWidth, self.dimensions.getLidHeight(), self.dimensions.getHexCentre(row, column))

    def createHexagonConfiguration(self, row: int, column: int) -> HexagonConfiguration:
        config = HexagonConfiguration(self.dimensions.getLidHeight(), self.dimensions.lidInfillThickness, self.dimensions.lidExternalWallThickness).withRays(0)

        adjacentDistanceDelta = self.dimensions.adjacentDistance / 2 / cos(radians(30))
        pinWidthDelta = (self.dimensions.pinWidth - self.dimensions.adjacentDistance / 2) / cos(radians(30))

        if column == 0:
            if row == 0:
                config.withWalls(0, 0, 0, HexTileEdges.SW, HexTileEdges.W)
                config.withWalls(0, 0, adjacentDistanceDelta, HexTileEdges.SE)
                config.withWalls(0, adjacentDistanceDelta, 0, HexTileEdges.NW)
                config.withRays(adjacentDistanceDelta, HexTileVertices.NE)
            elif row % 2 == 0:
                config.withWalls(0, adjacentDistanceDelta, 0, HexTileEdges.NW)
                config.withWalls(0, 0, 0, HexTileEdges.W)
                config.withWalls(0, 0, adjacentDistanceDelta, HexTileEdges.SW)
                config.withRays(adjacentDistanceDelta, HexTileVertices.NE, HexTileVertices.SE)
            elif row == self.rowCount - 1:
                config.withWalls(0, 0, 0, HexTileEdges.NW)
                config.withWalls(0, 0, pinWidthDelta, HexTileEdges.W)
                config.withWalls(0, adjacentDistanceDelta, 0, HexTileEdges.NE)
                config.withRays(adjacentDistanceDelta, HexTileVertices.SE)
                config.withRays(pinWidthDelta, HexTileVertices.S)
            else:
                config.withWalls(0, pinWidthDelta, pinWidthDelta, HexTileEdges.W)
                config.withRays(adjacentDistanceDelta, HexTileVertices.NE, HexTileVertices.SE)
                config.withRays(pinWidthDelta, HexTileVertices.N, HexTileVertices.S)
        else:
            if row == 0:
                config.withWalls(0, 0, pinWidthDelta, HexTileEdges.E)
                config.withWalls(0, 0, 0, HexTileEdges.SE)
                config.withWalls(0, adjacentDistanceDelta, 0, HexTileEdges.SW)
                config.withRays(adjacentDistanceDelta, HexTileVertices.NW)
                config.withRays(pinWidthDelta, HexTileVertices.N)
            elif row % 2 == 0:
                config.withWalls(0, pinWidthDelta, pinWidthDelta, HexTileEdges.E)
                config.withRays(adjacentDistanceDelta, HexTileVertices.SW, HexTileVertices.NW)
                config.withRays(pinWidthDelta, HexTileVertices.S, HexTileVertices.N)
            elif row == self.rowCount - 1:
                config.withWalls(0, 0, 0, HexTileEdges.NE, HexTileEdges.E)
                config.withWalls(0, 0, adjacentDistanceDelta, HexTileEdges.NW)
                config.withWalls(0, adjacentDistanceDelta, 0, HexTileEdges.SE)
                config.withRays(adjacentDistanceDelta, HexTileVertices.SW)
            else:
                config.withWalls(0, 0, adjacentDistanceDelta, HexTileEdges.NE)
                config.withWalls(0, 0, 0, HexTileEdges.E)
                config.withWalls(0, adjacentDistanceDelta, 0, HexTileEdges.SE)
                config.withRays(adjacentDistanceDelta, HexTileVertices.NW, HexTileVertices.SW)

        return config

    def getVertex(self, hexagon: Hexagon, vertex: HexTileVertices, external: bool, offset: float) -> Vector:
        return hexagon.getVertex(vertex, (1 if external else self.dimensions.lidHoleMultiplier) + hexagon.getRayMultiplierForEdgeOffset(offset))

    def createCustomWire(self, column: int, offset: float, internal: list[HexTileVertices]):
        hexagon = self.createHexagon(int(self.rowCount / 2), column)

        adjacentDistanceDelta = self.dimensions.adjacentDistance / 2 / cos(radians(30))

        customOffsets = [HexTileVertices.NW, HexTileVertices.SW] if column == 1 else [HexTileVertices.NE, HexTileVertices.SE]

        topWire = createWire(*(self.getVertex(hexagon, vertex, vertex not in internal, offset + (adjacentDistanceDelta if vertex in customOffsets else 0)) for vertex in HexTileVertices.iterate()))
        bottomWire = createWire(*(self.getVertex(hexagon, vertex, vertex in internal, offset + (adjacentDistanceDelta if vertex in customOffsets else 0)) for vertex in HexTileVertices.iterate()))

        bottomWire.translate(Vector(0, 0, -self.dimensions.getLidHeight()))

        boardCentre = (self.dimensions.getHexCentre(0, 0) + self.dimensions.getHexCentre(self.rowCount - 1, 1)) / 2

        fuser = Fuser()
        for orientation in [0, 180]:
            shape = Part.makeLoft([topWire, bottomWire], solid=True)
            shape.rotate(boardCentre, Vector(0, 0, 1), orientation).translate(Vector(0, 0, self.dimensions.getLidHeight()))
            fuser.fuse(shape)

        return fuser.solid

    def createHandleShape(self, offset: float) -> Part.Solid:
        part1 = self.createCustomWire(1, offset, [HexTileVertices.S, HexTileVertices.SW])
        part2 = self.createCustomWire(0, offset, [HexTileVertices.SE])

        return fuse(part1, part2)

    def createLid(self) -> MultiColourFuser:
        fuser = MultiColourFuser()

        for row in range(self.rowCount):
            for column in range(2):
                fuser.fuse(Colour.BASE, self.createHexagon(row, column).createGrid(self.createHexagonConfiguration(row, column)))

        # walls, magnetHoles = self.createWalls(self.dimensions.getLidHeight(), False, self.dimensions.magnetHeightCeiling, Colour.WALLED_MESH)
        # fuser.fuseColour(Colour.BASE, walls)

        # fuser.cut(magnetHoles)
        fuser.fuse(Colour.BASE, self.createHandleShape(0))
        fuser.cut(self.createHandleShape(-self.dimensions.lidInfillThickness * 1.2)) # due to curving

        bases, holes = self.createMagnetHoles(self.dimensions.magnetHeightCeiling, False, self.dimensions.getLidHeight())
        fuser.fuse(Colour.BASE, bases)
        fuser.cut(holes)

        return fuser
