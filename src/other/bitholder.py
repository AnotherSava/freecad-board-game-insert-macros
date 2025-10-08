from dataclasses import dataclass
from typing import Iterable

import Part
from FreeCAD import Vector
from Part import makeLoft

from common.colours import MultiColourFuser, Colour
from common.fuser import Fuser
from common.hexagon import Hexagon, getDiagonal
from common.magnets import createMagnetHoles, MagnetDimensions, MagnetDetails
from common.smartbox import SmartBox


@dataclass
class BitHolderDimensions:
    shortDiagonal: float
    shortDiagonalDelta: float
    gap: float
    padding: float
    height: float
    holeHeight: float
    magnetDimensions: MagnetDimensions
    magnetCount: int
    roundedLength: float
    innerWallThickness: float
    innerWallDelta: float
    outerWallThickness: float
    rowLengths: list[int]
    outerWallRoundedLength: float
    circularHoleDiameter: float

    def getRightWidth(self):
        return self.getMagnetSidePadding() + getDiagonal(self.shortDiagonal) + self.padding / 2

    def getWidth(self):
        return self.padding + self.shortDiagonal

    def getLength(self, count: int) -> float:
        return getDiagonal(self.shortDiagonal) * count + self.gap * (count - 1) + self.getMagnetSidePadding() + self.padding

    def getMagnetSidePadding(self):
        return self.magnetDimensions.height + self.padding

    def getRowStart(self, row: int) -> Vector:
        return Vector(0, self.outerWallThickness + self.innerWallDelta * (row + 0.5) + (self.innerWallThickness + self.getWidth()) * row, self.outerWallThickness)

    def getRowMiddle(self, row: int) -> Vector:
        return self.getRowStart(row) + Vector(0, self.getWidth() / 2)

class BitHolder:
    def __init__(self, dimensions: BitHolderDimensions):
        self.dimensions = dimensions

    def createHolder(self) -> MultiColourFuser:
        length = self.dimensions.getLength(12) + self.dimensions.getMagnetSidePadding()
        width = self.dimensions.outerWallThickness * 2 + self.dimensions.innerWallThickness * 5 + (self.dimensions.innerWallDelta + self.dimensions.getWidth()) * 6
        height = self.dimensions.height

        box = SmartBox(length, width, height).withRoundedFront(0, self.dimensions.outerWallRoundedLength, 0, 0)

        fuser = Fuser(box)
        fuserMagnetHoles = Fuser()

        for row, length in enumerate(self.dimensions.rowLengths):
            solid = self.createBox(self.dimensions.getLength(length), 1, True).translateVector(self.dimensions.getRowStart(row))
            fuser.cut(solid)
            fuser.cut(solid.translate(-self.dimensions.roundedLength))

            magnetHoles = createMagnetHoles(self.dimensions.magnetDimensions, self.createMagnetDetails(Vector(1, 0, 0)))
            magnetHoles.translate(self.dimensions.getRowStart(row) + Vector(solid.length))
            fuserMagnetHoles.fuse(magnetHoles)

        fuserBody, fuserRecess = self.createSpecialParts(True)

        posA = Vector(box.xTo - self.dimensions.padding * 2 - getDiagonal(self.dimensions.shortDiagonal) / 2, self.dimensions.getRowStart(4).y + self.dimensions.shortDiagonal / 2)
        posB = posA - Vector(0, (getDiagonal(self.dimensions.shortDiagonal) + self.dimensions.padding) * 1.5)

        fuserRecess.fuse(self.createSingleHole().translate(pos) for pos in [posA, posB])

        fuserRecess.fuse(self.createCircularHole().translate(Vector(posA.x, self.dimensions.getRowStart(0).y + self.dimensions.circularHoleDiameter / 2)))

        fuser.cut(fuserBody)
        fuser.cut(fuserBody.translate(Vector(self.dimensions.innerWallDelta)))
        fuser.cut(fuserMagnetHoles, fuserRecess)

        return MultiColourFuser(Colour.BASE, fuser)

    def createRow(self, row: int, count: int) -> MultiColourFuser:
        box = self.createBox(self.dimensions.getLength(count))
        recess = self.createRecess(count)

        return MultiColourFuser(Colour.BASE, Fuser(box).cut(recess).translate(self.dimensions.getRowStart(row)))

    def createSpecial(self) -> MultiColourFuser:
        fuserBody, fuserRecess = self.createSpecialParts()
        return MultiColourFuser(Colour.BASE, fuserBody.cut(fuserRecess))

    def createSpecialParts(self, enlarge: bool = False) -> tuple[Fuser, Fuser]:
        totalWidth = self.dimensions.getLength(12) - self.dimensions.getRightWidth() - self.dimensions.getMagnetSidePadding() - self.dimensions.innerWallDelta
        row0 = self.createBox(totalWidth - self.dimensions.getLength(4), 1, enlarge)
        row1 = self.createBox(totalWidth - self.dimensions.getLength(5), 2, enlarge)
        row2 = self.createBox(totalWidth - self.dimensions.getLength(6), 3, enlarge)
        row3 = self.createBox(totalWidth - self.dimensions.getLength(9), 5, enlarge)
        rows = [row0, row1, row2, row3]

        fuserBody = Fuser()

        for row in rows:
            row.translate(row0.length - row.length)
            fuserBody.fuse(row)

        diameters = {5: 7.9, 6: 9.9, 7: 10.9, 10: 13.7, 11: 15.5, 12: 16.7, 13: 18.3, "Handle": 25.0}

        position13 = Vector(row3.xTo - diameters[13] / 2, row3.yTo - diameters[13] / 2)
        fuserRecess = Fuser(self.createSingleHole().translate(position13))

        diametersRow0 = [diameters[size] for size in [5, 6, 7, 10]]
        gap = (row0.length - self.dimensions.padding - self.dimensions.getMagnetSidePadding() - sum(diametersRow0)) / 3

        positionsX = []
        for i in range(4):
            x = gap * i + self.dimensions.padding + sum(diametersRow0[:i]) + diametersRow0[i] / 2
            if i > 0:
                x = x - gap + self.dimensions.gap
            positionsX.append(x)
            fuserRecess.fuse(self.createSingleHole().translate(Vector(x, self.dimensions.shortDiagonal / 2)))


        fuserRecess.fuse(self.createSingleHole().translate(Vector((positionsX[-2] + positionsX[-3]) / 2, row2.yTo - diameters[12] / 2)))
        fuserRecess.fuse(self.createSingleHole().translate(Vector((positionsX[-1] + positionsX[-2]) / 2, row2.yTo - diameters[12] / 2)))

        for fuser in [fuserBody, fuserRecess]:
            fuser.translate(self.dimensions.getRowStart(0) + Vector(self.dimensions.getLength(4) + self.dimensions.getMagnetSidePadding()))

        return fuserBody, fuserRecess

    def createBox(self, length: float, widthCount: int = 1, enlarged: bool = False) -> SmartBox:
        width = self.dimensions.getWidth() * widthCount + (self.dimensions.innerWallThickness + self.dimensions.innerWallDelta) * (widthCount - 1)
        if enlarged:
            width += self.dimensions.innerWallDelta

        return (SmartBox(length, width, self.dimensions.height)
                .withRoundedTop(self.dimensions.roundedLength)
                .withRoundedRight(self.dimensions.roundedLength, self.dimensions.roundedLength, 0, 0)
                .withRoundedFront(self.dimensions.roundedLength, self.dimensions.roundedLength, 0, 0)).translate(0, -self.dimensions.innerWallDelta / 2 if enlarged else 0)

    def createSingleHole(self, delta: float = -0.05) -> Fuser:
        narrowWire = Hexagon(self.dimensions.shortDiagonal + delta).createWalledWire()
        wideWire = Hexagon(self.dimensions.shortDiagonal + self.dimensions.shortDiagonalDelta + delta).createWalledWire().translate(Vector(0, 0, self.dimensions.holeHeight))

        hole = makeLoft([narrowWire, wideWire], True, True)
        hole.rotate(Vector(), Vector(0, 0, 1), 30)
        hole.translate(Vector(0, 0, self.dimensions.height - self.dimensions.holeHeight))

        return Fuser(hole)

    def createCircleWire(self, diameter: float) -> Part.Wire:
        return Part.Wire(Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), diameter / 2).toShape().Edges)

    def createCircularHole(self, delta: float = -0.05) -> Fuser:
        bottomWire = self.createCircleWire(self.dimensions.circularHoleDiameter + delta)
        topWire = self.createCircleWire(self.dimensions.circularHoleDiameter + delta + self.dimensions.shortDiagonalDelta).translate(Vector(0, 0, self.dimensions.holeHeight))

        return Fuser(makeLoft([bottomWire, topWire], True, True)).translate(Vector(0, 0, self.dimensions.height - self.dimensions.holeHeight))

    def createMagnetDetails(self, holeVector: Vector) -> Iterable[MagnetDetails]:
        gap = (self.dimensions.height - self.dimensions.roundedLength - self.dimensions.magnetDimensions.diameter * self.dimensions.magnetCount) / (self.dimensions.magnetCount + 1)
        return (MagnetDetails(Vector(0, self.dimensions.getWidth() / 2, gap * (i + 1) + self.dimensions.magnetDimensions.diameter * (i + 0.5)), holeVector=holeVector) for i in range(self.dimensions.magnetCount))

    def getPositionX(self, index: int) -> float:
        return getDiagonal(self.dimensions.shortDiagonal) * (index + 0.5) + self.dimensions.gap * index + self.dimensions.padding

    def createRecess(self, count: int) -> Fuser:
        fuser = Fuser(self.createSingleHole().translate(Vector(self.getPositionX(i), self.dimensions.shortDiagonal / 2)) for i in range(count))

        magnetDetails = self.createMagnetDetails(Vector(-1, 0, 0))
        magnetHoles = createMagnetHoles(self.dimensions.magnetDimensions, magnetDetails)
        magnetHoles.translate(Vector(self.dimensions.getLength(count)))

        fuser.fuse(magnetHoles)

        return fuser
