import math
from dataclasses import dataclass
from math import tan, cos, sin, radians, ceil, floor

import Part
from FreeCAD import Vector

from Inserts.common import magnets
from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuse
from Inserts.common.geometry import createWire, createVector
from Inserts.common.hexagon import Hexagon, HexagonConfiguration
from Inserts.common.hexes import createRoundedHexTile, getDiagonal, getDistanceY, getHexSide
from Inserts.common.magnets import MagnetDetails, getWidestRadius, MagnetDimensions
from Inserts.common.pencil import Pencil
from Inserts.hex.configuration import HexTileVertices, HexTileEdges
from Inserts.hex.images import Images


@dataclass
class GridDimensions:
    hexShortDiagonal: float
    pinWidth: float
    wallTipLengthCoefficient: float
    wallTipWidthCoefficient: float
    pinRadius: float
    hexRadius: float
    shallowEdgeAngle: float
    shorterSideMultiplier: float
    pinHeight: float
    floorThickness: float
    ceilingThickness: float
    adjacentDistance: float # distance between horizontally adjacent tiles
    magnetDiameter: float
    magnetDiameterFloor: float
    magnetHeightFloor: float
    magnetHeightCeiling: float
    magnetBaseWall: float
    maxRowsPerMagnet: int
    lidHoleAngle: float
    lidHoleMultiplier: float
    lidInfillThickness: float
    lidExternalWallThickness: float
    lidSideDelta: float # slightly reduced on sides to make it stackable even with larger magnets

    def getHexSide(self, hexShortDiagonal: float = None) -> float:
        return getHexSide(hexShortDiagonal or self.hexShortDiagonal)

    def getDistanceFromHexCentreToOuterPinAngle(self) -> float:
        return self.getDistanceFromHexCentreToHexCorner(self.pinWidth * 2 + self.hexShortDiagonal)

    def getDistanceFromHexCentreToHexCorner(self, hexShortDiagonal: float = None) -> float:
        return getDiagonal(hexShortDiagonal or self.hexShortDiagonal) / 2

    def getCondensedDistanceY(self) -> float:
        return getDistanceY(self.hexShortDiagonal, self.adjacentDistance, self.pinWidth)

    def getCondensedDistanceX(self) -> float:
        return self.hexShortDiagonal + self.adjacentDistance

    def getHexCentre(self, row: int, column: int) -> Vector:
        sameRowHexDistanceX = self.hexShortDiagonal + self.adjacentDistance
        evenRowsShiftX = (self.hexShortDiagonal + self.adjacentDistance) / 2
        return Vector(evenRowsShiftX * (row % 2) + sameRowHexDistanceX * column, row * self.getCondensedDistanceY() + self.getDistanceFromHexCentreToOuterPinAngle())

    def getLidHeight(self) -> float:
        return self.ceilingThickness + self.magnetHeightCeiling

    def getMagnetLocation(self, row: int, column: int, rowCount: int, magnetDiameter: float) -> Vector:
        hexCentreToHoleUp = Vector(0, self.getDistanceFromHexCentreToHexCorner(self.pinWidth * (1 + self.wallTipWidthCoefficient) + self.hexShortDiagonal) - getWidestRadius(magnetDiameter, self.magnetBaseWall) / cos(radians(30)))

        if 0 < row < rowCount -1:
            hexCentreToHoleUp -= Vector(2 * self.pinWidth * (1 - self.wallTipWidthCoefficient) * sin(radians(30)))

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

    def createWallTip(self, pencil: Pencil, nextAngle: float, shortFirst: bool, thickness: float, wallTipWidthCoefficient: float, curveRadius: float):
        if shortFirst:
            pencil.draw(thickness * wallTipWidthCoefficient - curveRadius, nextAngle)
            pencil.arcWithRadius(curveRadius, nextAngle + 90, 90)
        else:
            pencil.arcWithRadius(curveRadius, nextAngle, 90)
            pencil.draw(thickness * wallTipWidthCoefficient - curveRadius, nextAngle)

        return nextAngle + 90

    def drawZigZag(self, pencil: Pencil, nextAngle: float, *sides: float) -> float:
        for side in sides:
            pencil.draw(side, nextAngle)
            nextAngle = 180 - nextAngle
        return nextAngle

    def createWall(self, row: int, column: int, top: bool, full: bool, wallTipWidthCoefficient: float, height: float) -> Fuser:
        side = self.dimensions.getHexSide(self.dimensions.hexShortDiagonal + self.dimensions.adjacentDistance)
        shorterSideDelta = self.dimensions.pinWidth * (1 - wallTipWidthCoefficient) / cos(radians(30))
        shortTipLength = side * self.dimensions.wallTipLengthCoefficient
        longTipLength = shortTipLength + self.dimensions.pinWidth * wallTipWidthCoefficient * tan(radians(30)) - self.dimensions.pinRadius
        longerTipLength = shortTipLength + self.dimensions.pinWidth * tan(radians(30)) - self.dimensions.pinRadius + shorterSideDelta * sin(radians(30))

        pencil = Pencil(createVector(shortTipLength, 120))

        if full:
            nextAngle = self.drawZigZag(pencil, -60, shortTipLength, side, side, side - shorterSideDelta, longerTipLength)
        else:
            nextAngle = self.drawZigZag(pencil, -60, shortTipLength, shortTipLength)

        nextAngle = self.createWallTip(pencil, 270 - nextAngle, not full, self.dimensions.pinWidth, wallTipWidthCoefficient, self.dimensions.pinRadius)

        if full:
            self.drawZigZag(pencil, nextAngle, shortTipLength, side, side, side - shorterSideDelta, longerTipLength)
        else:
            self.drawZigZag(pencil, nextAngle , longTipLength, longTipLength)

        self.createWallTip(pencil, -150, False, self.dimensions.pinWidth, wallTipWidthCoefficient, self.dimensions.pinRadius)

        fuser = Fuser(pencil.extrude(height))

        if top:
            fuser.translate(Vector(0, self.dimensions.getDistanceFromHexCentreToHexCorner()))
        else:
            fuser.mirrorY()
            fuser.translate(Vector(0, -self.dimensions.getDistanceFromHexCentreToHexCorner()))

        return fuser.translate(self.dimensions.getHexCentre(row, column))

    def createWalls(self, height: float) -> Fuser:
        fuser = Fuser()

        for row in range(self.rowCount - 1):
            top = row % 2 == 0
            fuser.fuse(self.createWall(row if top else row + 1, 0, top, True, self.dimensions.wallTipWidthCoefficient, height))

        for column in range(2):
            fuser.fuse(self.createWall(0, column, False, False, (1 + self.dimensions.wallTipWidthCoefficient) / 2, height))
            fuser.fuse(self.createWall(self.rowCount - 1, column, True, False, (1 + self.dimensions.wallTipWidthCoefficient) / 2, height))

        fuser.fuse(self.createDividerWalls(height))

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
            x = self.dimensions.getCondensedDistanceX() / 2 * (row % 2) + self.dimensions.hexShortDiagonal / 2
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

    def createMagnetLocations(self, magnetDiameter: float) -> list[MagnetDetails]:
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)

        magnetDetails = []

        for i in wallFactory.getExtraMagnetRowIndices():
            magnetDetails.append(MagnetDetails(self.dimensions.getMagnetLocation(i, 0, self.rowCount, magnetDiameter)))
            magnetDetails.append(MagnetDetails(self.dimensions.getMagnetLocation(i, 3, self.rowCount, magnetDiameter)))

        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetLocation(0, 0, self.rowCount, magnetDiameter)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetLocation(0, 2, self.rowCount, magnetDiameter)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetLocation(self.rowCount, 1, self.rowCount, magnetDiameter)))
        magnetDetails.append(MagnetDetails(self.dimensions.getMagnetLocation(self.rowCount, 3, self.rowCount, magnetDiameter)))

        return magnetDetails

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
                fuser.fuse(createRoundedHexTile(self.dimensions.hexShortDiagonal, floorThickness, self.dimensions.getHexCentre(i, j), self.dimensions.hexRadius, self.dimensions.shallowEdgeAngle, self.dimensions.shorterSideMultiplier, roundedVertices, shallowEdges))

        return fuser

    def createBoard(self) -> MultiColourFuser:
        wallFactory = CondensedWalls(self.dimensions, self.rowCount)

        fuser = Fuser()
        fuser.fuse(self.createFloor(self.dimensions.floorThickness))
        fuser.fuse(wallFactory.createWalls(self.dimensions.pinHeight + self.dimensions.floorThickness))

        magnetDetails = self.createMagnetLocations(self.dimensions.magnetDiameterFloor)
        height = self.dimensions.pinHeight + self.dimensions.floorThickness
        magnetDimensions = MagnetDimensions(self.dimensions.magnetDiameterFloor, self.dimensions.magnetHeightFloor, self.dimensions.magnetBaseWall)
        bases, holes, corners = magnets.createMagnetHolders(magnetDimensions, True, height, magnetDetails)
        fuser.fuse(bases)
        fuser.cut(holes)

        return MultiColourFuser(Colour.BASE, fuser).translate(Vector(0, 0, -self.dimensions.floorThickness))

    def createHexagon(self, row: int, column: int) -> Hexagon:
        return Hexagon(self.dimensions.hexShortDiagonal, self.dimensions.getLidHeight(), self.dimensions.getHexCentre(row, column))

    def createHexagonConfiguration(self, row: int, column: int) -> HexagonConfiguration:
        config = HexagonConfiguration(self.dimensions.lidInfillThickness, self.dimensions.lidExternalWallThickness).withRays().withHiddenWalls(self.dimensions.adjacentDistance / 2)

        adjacentDistanceDelta = self.dimensions.adjacentDistance / 2 / cos(radians(30))
        pinWidthDelta = (self.dimensions.pinWidth - self.dimensions.adjacentDistance / 2) / cos(radians(30))

        offsetDistance = (self.dimensions.shorterSideMultiplier - 1) * self.dimensions.hexShortDiagonal / 2 - self.dimensions.lidSideDelta
        offsetDistanceY = 2 * offsetDistance * tan(radians(30)) - adjacentDistanceDelta
        offsetDiagonal = - offsetDistance / cos(radians(30))

        if column == 0:
            if row == 0:
                config.withVisibleWalls(0, 0, 0, HexTileEdges.SW, HexTileEdges.SE)
                config.withVisibleWalls(offsetDistance, 0, 0, HexTileEdges.W)
                config.withVisibleWalls(0, offsetDiagonal, 0, HexTileEdges.NW)

                config.withRays(adjacentDistanceDelta, HexTileVertices.NE)

            elif row % 2 == 0:
                config.withVisibleWalls(0, offsetDiagonal, 0, HexTileEdges.NW)
                config.withVisibleWalls(offsetDistance, 0, 0, HexTileEdges.W)
                config.withVisibleWalls(0, 0, offsetDiagonal, HexTileEdges.SW)

                config.withRays(adjacentDistanceDelta, HexTileVertices.NE, HexTileVertices.SE)

            elif row == self.rowCount - 1:
                config.withVisibleWalls(0, 0, 0, HexTileEdges.NW, HexTileEdges.NE)
                config.withVisibleWalls(offsetDistance, 0, pinWidthDelta + offsetDistanceY, HexTileEdges.W)

                config.withRays(adjacentDistanceDelta, HexTileVertices.SE)
                config.withRays(pinWidthDelta, HexTileVertices.S)

            else:
                config.withVisibleWalls(offsetDistance, pinWidthDelta + offsetDistanceY, pinWidthDelta + offsetDistanceY, HexTileEdges.W)

                config.withRays(adjacentDistanceDelta, HexTileVertices.NE, HexTileVertices.SE)
                config.withRays(pinWidthDelta, HexTileVertices.N, HexTileVertices.S)
        else:
            if row == 0:
                config.withVisibleWalls(offsetDistance, 0, pinWidthDelta + offsetDistanceY, HexTileEdges.E)
                config.withVisibleWalls(0, 0, 0, HexTileEdges.SE, HexTileEdges.SW)

                config.withRays(adjacentDistanceDelta, HexTileVertices.NW)
                config.withRays(pinWidthDelta, HexTileVertices.N)

            elif row % 2 == 0:
                config.withVisibleWalls(offsetDistance, pinWidthDelta + offsetDistanceY, pinWidthDelta + offsetDistanceY, HexTileEdges.E)

                config.withRays(adjacentDistanceDelta, HexTileVertices.SW, HexTileVertices.NW)
                config.withRays(pinWidthDelta, HexTileVertices.S, HexTileVertices.N)

            elif row == self.rowCount - 1:
                config.withVisibleWalls(offsetDistance, 0, 0, HexTileEdges.E)
                config.withVisibleWalls(0, 0, 0, HexTileEdges.NE, HexTileEdges.NW)
                config.withVisibleWalls(0, offsetDiagonal, 0, HexTileEdges.SE)

                config.withRays(adjacentDistanceDelta, HexTileVertices.SW)

            else:
                config.withVisibleWalls(0, 0, offsetDiagonal, HexTileEdges.NE)
                config.withVisibleWalls(offsetDistance, 0, 0, HexTileEdges.E)
                config.withVisibleWalls(0, offsetDiagonal, 0, HexTileEdges.SE)

                config.withRays(adjacentDistanceDelta, HexTileVertices.NW, HexTileVertices.SW)

        return config

    def getVertex(self, hexagon: Hexagon, vertex: HexTileVertices, external: bool, offset: float, config: HexagonConfiguration) -> Vector:
        multiplier = (1 if external else self.dimensions.lidHoleMultiplier) + hexagon.getRayMultiplierForEdgeOffset(offset)
        return hexagon.getWallsIntersection(vertex, config, multiplier)

    def createCustomWire(self, column: int, offset: float, internal: list[HexTileVertices]):
        row = int(self.rowCount / 2)
        hexagon = self.createHexagon(row, column)
        config = self.createHexagonConfiguration(row, column)

        topWire = createWire(*(self.getVertex(hexagon, vertex, vertex not in internal, offset, config) for vertex in HexTileVertices.iterate()))
        bottomWire = createWire(*(self.getVertex(hexagon, vertex, vertex in internal, offset, config) for vertex in HexTileVertices.iterate()))

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

        fuser.fuse(Colour.BASE, self.createHandleShape(0))
        fuser.cut(self.createHandleShape(-self.dimensions.lidInfillThickness * 1.2)) # due to curving

        magnetDetails = self.createMagnetLocations(self.dimensions.magnetDiameterFloor)
        height = self.dimensions.getLidHeight()
        magnetDimensions = MagnetDimensions(self.dimensions.magnetDiameter, self.dimensions.magnetHeightCeiling, self.dimensions.magnetBaseWall)
        bases, holes, corners = magnets.createMagnetHolders(magnetDimensions, False, height, magnetDetails)
        fuser.fuse(Colour.BASE, bases)
        fuser.cut(holes)

        return fuser.mirrorZ()

    def createTileBoard(self, imageFactory: Images, *tileNumbers) -> MultiColourFuser:
        assert len(tileNumbers) % 2 == 0

        images = MultiColourFuser()

        for index, number in enumerate(tileNumbers):
            images.fuseAll(imageFactory.createTile(number).translate(self.dimensions.getHexCentre(math.floor(index / 2), index % 2)))

        board = self.createBoard()

        return board.replaceAll(images.common(board))
