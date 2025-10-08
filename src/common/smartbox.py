from dataclasses import dataclass
from enum import IntEnum

import Part
from FreeCAD import Vector
from Part import Solid

from common.fuser import Fuser
from common.geometry import Side, shiftVector
from common.magnets import MagnetDetails, RampDetails, CornerAngles
from common.pencil import Pencil
from common.smartsolid import SmartSolid


class CuboidEdges(IntEnum):
    NB = 1
    WB = 2
    SB = 3
    EB = 4
    NT = 5
    WT = 6
    ST = 7
    ET = 8
    NW = 9
    SW = 10
    SE = 11
    NE = 12

@dataclass
class RoundedLengths:
    ne: float = 0
    nw: float = 0
    sw: float = 0
    se: float = 0

    @classmethod
    def createSimple(cls, length: float):
        return RoundedLengths(length, length, length, length)

    @classmethod
    def createComplex(cls, ne: float, nw: float = None, sw:float = None, se: float = None):
        assert nw is not None or sw is None and se is None

        return RoundedLengths(ne, ne if nw is None else nw, ne if sw is None else sw, ne if se is None else se)


class SmartBox(SmartSolid):
    def __init__(self, length: float, width: float, height: float, x: float = 0, y: float = 0, z: float = 0):
        super().__init__(length, width, height, x, y, z)

        self.roundedFront = RoundedLengths()
        self.roundedTop = RoundedLengths()
        self.roundedRight = RoundedLengths()

        self.updateBox()

    def withRoundedTop(self, ne: float, nw: float = None, sw:float = None, se: float = None):
        self.roundedTop = RoundedLengths.createComplex(ne, nw, sw, se)
        self.updateBox()
        return self

    def withRoundedFront(self, ne: float, nw: float = None, sw:float = None, se: float = None):
        self.roundedFront = RoundedLengths.createComplex(ne, nw, sw, se)
        self.updateBox()
        return self

    def withRoundedRight(self, ne: float, nw: float = None, sw:float = None, se: float = None):
        self.roundedRight = RoundedLengths.createComplex(ne, nw, sw, se)
        self.updateBox()
        return self

    def updateBox(self):
        top = self.createRoundedWire(self.length, self.width, self.roundedTop).extrude(self.height)
        front = self.createRoundedWire(self.length, self.height, self.roundedFront).extrudeY(self.width)
        right = self.createRoundedWire(self.width, self.height, self.roundedRight).extrudeX(self.length)

        self.solid = top.common(front).common(right)
        self.solid.translate(Vector(self.x, self.y, self.z))

    def createRoundedAngle(self, pencil: Pencil, length1: float, angle1: float, length2: float, angle2: float, roundedLength: float) -> Pencil:
        if roundedLength:
            pencil.draw(length1 - roundedLength, angle1)
            destination = shiftVector(pencil.location, roundedLength, angle1, roundedLength, angle2)
            angle = angle1 + 90 if (angle2 - angle1) % 360 > 180 else angle1 - 90
            pencil.arcWithAngleToCentreAbs(angle, destination)
            pencil.draw(length2 - roundedLength, angle2)
        else:
            pencil.draw(length1, angle1)
            pencil.draw(length2, angle2)

        return pencil

    def createRoundedWire(self, length: float, width: float, roundedLengths: RoundedLengths) -> Pencil:
        pencil = Pencil(Vector(length, width / 2))

        self.createRoundedAngle(pencil, width / 2, 0, length / 2, 90, roundedLengths.ne)
        self.createRoundedAngle(pencil, length / 2, 90, width / 2, 180, roundedLengths.nw)
        self.createRoundedAngle(pencil, width / 2, 180, length / 2, 270, roundedLengths.sw)
        self.createRoundedAngle(pencil, length / 2, 270, width / 2, 0, roundedLengths.se)

        return pencil

    def addCut(self, side: Side, length: float, extraWidth: float, height: float, shift: float = 0):
        preCutCoefficient = 0.2
        pencil = Pencil(Vector(-length / 2 + shift, -extraWidth))
        pencil.arcWithRadius(length / 2 * preCutCoefficient, 0, 90)
        pencil.arcWithRadius(length / 2 * (1 - preCutCoefficient), -90, -180)
        pencil.arcWithRadius(length / 2 * preCutCoefficient, -90, 90)
        solid = pencil.extrude(height * 2 + self.height)
        solid.rotate(Vector(), Vector(0, 0, 1), side.value + 180).translate(self.getTranslateVector(side, height))
        self.solid = self.solid.fuse(solid)

    def addLedge(self, side: Side, height: float = None, coefficient: float = 0.15, thickness: float = 1.2):
        ledge = self.createLedge(side, coefficient, thickness)
        cylinders = self.createEllipticalCylinders(coefficient, thickness)
        cylinderLedge = ledge.common(cylinders).translate(Vector(0, 0, (height or self.height) - thickness))
        self.solid = self.solid.cut(cylinderLedge)

    def createEllipticalCylinder(self, x: float, y: float, z: float, coefficient: float, thickness: float) -> Solid:
        if self.length <= self.width:
            ellipse = Part.Ellipse(Vector(0, 0, 0), Vector(self.length * coefficient / 2, 0, 0), Vector(0, self.width * coefficient / 2, 0))
            ellipse.translate(Vector(0, -self.width * coefficient / 2, 0))
        else:
            ellipse = Part.Ellipse(Vector(0, 0, 0), Vector(0, self.width * coefficient / 2, 0), Vector(self.length * coefficient / 2, 0, 0))
            ellipse.translate(Vector(-self.length * coefficient / 2, 0, 0))

        face = Part.Face(Part.Wire([(ellipse.toShape())]))
        solid = face.extrude(Vector(0, 0, thickness))
        solid.translate(Vector(x, y, z))
        return solid

    def createEllipticalCylinders(self, coefficient: float, thickness: float) -> Solid:
        fuser = Fuser()
        fuser.fuse(self.createEllipticalCylinder(self.x, self.y, self.z, coefficient, thickness))
        fuser.fuse(self.createEllipticalCylinder(self.xTo, self.y, self.z, coefficient, thickness))
        fuser.fuse(self.createEllipticalCylinder(self.x, self.yTo, self.z, coefficient, thickness))
        fuser.fuse(self.createEllipticalCylinder(self.xTo, self.yTo, self.z, coefficient, thickness))
        return fuser.solid

    def createLedge(self, side: Side, coefficient: float, thickness: float) -> Solid:
        match side:
            case Side.S:
                return Part.makeBox(self.length, self.width * coefficient, thickness, Vector(self.x, self.y, self.z))
            case Side.N:
                return Part.makeBox(self.length, self.width * coefficient, thickness, Vector(self.x, self.yTo - self.width * coefficient, self.z))
            case Side.W:
                return Part.makeBox(self.length * coefficient, self.width, thickness, Vector(self.x, self.y, self.z))
            case Side.E:
                return Part.makeBox(self.length * coefficient, self.width, thickness, Vector(self.xTo - self.length * coefficient, self.y, self.z))

    def getTranslateVector(self, side: Side, height: float) -> Vector:
        match side:
            case Side.S:
                return Vector((self.x + self.xTo) / 2, self.y, self.z - height)
            case Side.N:
                return Vector((self.x + self.xTo) / 2, self.yTo, self.z - height)
            case Side.W:
                return Vector(self.x, (self.y + self.yTo) / 2, self.z - height)
            case Side.E:
                return Vector(self.xTo, (self.y + self.yTo) / 2, self.z - height)

        raise ValueError(f"Unexpected side: ${side}")

    def createCornerMagnetDetails(self, widerRadius: float, holeVector: Vector = None) -> list[MagnetDetails]:
        return [
            self.createMagnetDetails(0, 0, 2, 2, widerRadius, CornerAngles.allBut(CornerAngles.NE), holeVector=holeVector),
            self.createMagnetDetails(0, 1, 2, 2, widerRadius, CornerAngles.allBut(CornerAngles.NW), holeVector=holeVector),
            self.createMagnetDetails(1, 0, 2, 2, widerRadius, CornerAngles.allBut(CornerAngles.SE), holeVector=holeVector),
            self.createMagnetDetails(1, 1, 2, 2, widerRadius, CornerAngles.allBut(CornerAngles.SW), holeVector=holeVector),
        ]

    def createMagnetDetails(self, row: int, column: int, rowCount: int, columnCount: int, widerRadius: float, cornerAngle: list[int] = None, cutAngle: list[int] = None, ramp: RampDetails = None,
                            cornerHeight: float = None, adjacentToWidening: bool = True, holeVector: Vector = None, z: float = 0):
        x = max(min(column * self.length / (columnCount - 1), self.length - widerRadius), widerRadius)
        y = max(min(row * self.width / (rowCount - 1), self.width - widerRadius), widerRadius)

        return MagnetDetails(Vector(x, y, z), cornerAngle, cutAngle, cornerHeight, ramp, adjacentToWidening, holeVector)
