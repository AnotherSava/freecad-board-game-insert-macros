import math
from math import tan, cos, sin, radians, ceil, floor

import Part
from FreeCAD import Vector

from Inserts.common import magnets
from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuse
from Inserts.common.geometry import createWire
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
    shortWallCoefficient: float
    pinRadius: float
    pinHeight: float
    hexRecessCoefficient: float
    floorThickness: float
    ceilingThickness: float
    adjacentDistance: float # distance between horizontally adjacent tiles
    magnetDiameter: float
    magnetDiameterFloor: float
    magnetHeightFloor: float
    magnetHeightCeiling: float
    thinnestWall: float
    maxRowsPerMagnet: int
    lidHoleAngle: float
    lidHoleMultiplier: float
    lidInfillThickness: float
    lidExternalWallThickness: float

    def getHexSide(self, hexWidth: float = None):
        return (hexWidth or self.hexWidth) * tan(radians(30))

    def getDistanceFromHexCentreToOuterPinAngle(self):
        return self.getDistanceFromHexCentreToHexCorner(self.pinWidth * 2 + self.hexWidth)

    def getDistanceFromHexCentreToHexCorner(self, hexWidth: float = None):
        return (hexWidth or self.hexWidth) / 2 / cos(radians(30))

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

    def getMagnetHoleLocation(self, row: int, column: int, magnetDiameter: float) -> Vector:
        hexCentreToHoleUp = Vector(0, self.getDistanceFromHexCentreToOuterPinAngle() - getWidestRadius(magnetDiameter, self.thinnestWall) / cos(radians(30)))
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

    def createWallTip(self, pencil: Pencil, angle: float, shortFirst: bool, shortEndCoefficient: float, thickness: float, curveRadius: float):
        side = self.dimensions.getHexSide(self.dimensions.hexWidth + self.dimensions.adjacentDistance)
        shortTipLength = side * shortEndCoefficient
        longTipLength = shortTipLength + thickness * tan(radians(30))

        if shortFirst:
            pencil.draw(shortTipLength, angle)
            pencil.draw(thickness - curveRadius, angle + 90)
            pencil.arcWithRadius(curveRadius, angle + 180, 90)
            pencil.draw(longTipLength - curveRadius, angle + 180)
        else:
            pencil.draw(longTipLength - curveRadius, angle)
            pencil.arcWithRadius(curveRadius, angle + 90, 90)
            pencil.draw(thickness - curveRadius, angle + 90)
            pencil.draw(shortTipLength, angle + 180)

    def createCustomWall(self, row: int, column: int, top: bool, segmentCount: int, shortEndCoefficient: float, thickness: float, height: float, curveRadius: float = None) -> Part.Solid:
        side = self.dimensions.getHexSide(self.dimensions.hexWidth + self.dimensions.adjacentDistance)
        pencil = Pencil()
        nextAngle = -120

        for i in range(segmentCount):
            pencil.draw(side, nextAngle)
            nextAngle = 180 - nextAngle

        self.createWallTip(pencil, nextAngle, segmentCount % 2 == 0, shortEndCoefficient, thickness, curveRadius or self.dimensions.pinRadius)

        nextAngle = -nextAngle
        for i in range(segmentCount):
            pencil.draw(side, nextAngle)
            nextAngle = 180 - nextAngle

        self.createWallTip(pencil, 120, False, shortEndCoefficient, thickness, curveRadius or self.dimensions.pinRadius)

        wall = pencil.extrude(height)

        if not top:
            wall = wall.mirror(Vector(), Vector(0, 1, 0)) # invert X axis
            wall.translate(Vector(0, -self.dimensions.getDistanceFromHexCentreToHexCorner()))
        else:
            wall.translate(Vector(0, self.dimensions.getDistanceFromHexCentreToHexCorner()))

        wall.translate(self.dimensions.getHexCentre(row, column))

        return wall

    def createWalls(self, height: float) -> Fuser:
        fuser = Fuser()

        for row in range(self.rowCount - 1):
            top = row % 2 == 0
            fuser.fuse(self.createCustomWall(row if top else row + 1, 0, top, 3, self.dimensions.shortWallCoefficient, self.dimensions.pinWidth, height))

        for column in range(2):
            fuser.fuse(self.createCustomWall(0, column, False, 0, self.dimensions.shortWallCoefficient, self.dimensions.pinWidth, height))
            fuser.fuse(self.createCustomWall(self.rowCount - 1, column, True, 0, self.dimensions.shortWallCoefficient, self.dimensions.pinWidth, height))

        fuser.fuse(self.createDividerWalls(height))

        return fuser

    def createAntiWalls(self, height: float) -> Fuser:
        fuser = Fuser()

        thickness = self.dimensions.pinWidth * self.dimensions.hexRecessCoefficient
        curveRadius = min(self.dimensions.pinRadius, thickness - self.dimensions.pinWidth)
        side = self.dimensions.getHexSide(self.dimensions.hexWidth + self.dimensions.adjacentDistance)
        shortTipCoefficient = 1 - self.dimensions.shortWallCoefficient - self.dimensions.pinWidth * tan(radians(30)) / side

        for row in range(self.rowCount - 1):
            if row % 2 == 0:
                fuser.fuse(self.createCustomWall(row + 1, -1, False, 0, shortTipCoefficient, thickness, height, curveRadius))
                fuser.fuse(self.createCustomWall(row, 2, True, 0, shortTipCoefficient, thickness, height, curveRadius))
            else:
                fuser.fuse(self.createCustomWall(row, -1, True, 0, shortTipCoefficient, thickness, height, curveRadius))
                fuser.fuse(self.createCustomWall(row + 1, 2, False, 0, shortTipCoefficient, thickness, height, curveRadius))

        for column in range(3):
            fuser.fuse(self.createCustomWall(-1, column - 1, True, 0, shortTipCoefficient, thickness, height, curveRadius))
            fuser.fuse(self.createCustomWall(self.rowCount, column, False, 0, shortTipCoefficient, thickness, height, curveRadius))

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

    def roundTowardsCentre(self, number: float, centre: float) -> int:
        return ceil(number) if number < centre else floor(number)

    def getExtraMagnetRowIndices(self) -> list[int]:
        extraMagnetRowCount = ceil(self.rowCount / self.dimensions.maxRowsPerMagnet) - 1

        spacing = self.rowCount / (extraMagnetRowCount + 1)
        centre = self.rowCount / 2

        return [self.roundTowardsCentre((i + 1) * spacing, centre) for i in range(extraMagnetRowCount)]


class CondensedBoard:
    def __init__(self, dimensions: GridDimensions, rowCount: int):
        self.dimensions = dimensions
        self.rowCount = rowCount

    def createMagnetHoles(self, magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, baseHeight: float) -> (Part.Solid, Part.Solid):
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)

        magnetDetails = []

        for i in wallFactory.getExtraMagnetRowIndices():
            magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(i, 0, magnetDiameter)))
            magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(i, 3, magnetDiameter)))

        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(0, 0, magnetDiameter)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(0, 2, magnetDiameter)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(self.rowCount, 1, magnetDiameter)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetHoleLocation(self.rowCount, 3, magnetDiameter)))

        return magnets.createMagnetHolders(magnetDiameter, magnetHeight, magnetOnTop, baseHeight, self.dimensions.thinnestWall, magnetDetails)

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

    def createBoard(self) -> MultiColourFuser:
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)

        fuser = Fuser()
        fuser.fuse(self.createFloor(self.dimensions.floorThickness))
        fuser.fuse(wallFactory.createWalls(self.dimensions.pinHeight + self.dimensions.floorThickness))

        bases, holes = self.createMagnetHoles(self.dimensions.magnetDiameterFloor, self.dimensions.magnetHeightFloor, True, self.dimensions.pinHeight + self.dimensions.floorThickness)
        # fuser.fuse(bases)
        # fuser.cut(holes)

        fuser.cut(wallFactory.createAntiWalls(self.dimensions.pinHeight + self.dimensions.floorThickness))

        return MultiColourFuser(Colour.BASE, fuser)

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

        bases, holes = self.createMagnetHoles(self.dimensions.magnetDiameter, self.dimensions.magnetHeightCeiling, False, self.dimensions.getLidHeight())
        fuser.fuse(Colour.BASE, bases)
        fuser.cut(holes)

        return fuser
