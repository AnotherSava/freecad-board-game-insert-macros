import Part
from FreeCAD import Vector
from Part import Solid

from Inserts.common.fuser import Fuser
from Inserts.common.geometry import Side
from Inserts.common.magnets import MagnetDetails
from Inserts.common.pencil import Pencil
from Inserts.common.smartsolid import SmartSolid
from enum import IntEnum


class CornerAngleType(IntEnum):
    NONE = 0
    MIN = 1
    MAX = 2

class SmartBox(SmartSolid):
    def __init__(self, length: float, width: float, height: float):
        super().__init__(length, width, height)

        self.solid = Part.makeBox(length, width, height)

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
        # feature = Part.show(cylinders)
        # feature.ViewObject.ShapeColor = (0.2, 0.8, 0.8)
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

        raise ValueError(f"Unexpected side: ${side}")

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


    def createMagnetLocation(self, row: int, column: int, rowCount: int, columnCount: int, widerRadius: float, cornerAngle: list[int] | CornerAngleType = None, rampDirection: int = None, rampCentreAdjustment: float = None, rampLengthMultiplier: float = None, wallThickness: float = None, magnetCount: int = 1):
        if cornerAngle in [CornerAngleType.MIN, CornerAngleType.MAX]:
            if row == 0:
                if column == 0:
                    angles = [135] if cornerAngle == CornerAngleType.MIN else [135, 45, -135]
                elif column == columnCount - 1:
                    angles = [-135] if cornerAngle == CornerAngleType.MIN else [135, -45, -135]
                else:
                    angles = [135, -135]
            elif row == rowCount -1:
                if column == 0:
                    angles = [45] if cornerAngle == CornerAngleType.MIN else [135, 45, -45]
                elif column == columnCount - 1:
                    angles = [-45] if cornerAngle == CornerAngleType.MIN else [45, -45, -135]
                else:
                    angles = [45, -45]
            else:
                if column == 0:
                    angles = [45, 135]
                elif column == columnCount - 1:
                    angles = [-45, -135]
                else:
                    angles = None
        elif cornerAngle == CornerAngleType.NONE:
            angles = None
        else:
            angles = cornerAngle

        x = max(min(column * self.length / (columnCount - 1), self.length - widerRadius), widerRadius)
        y = max(min(row * self.width / (rowCount - 1), self.width - widerRadius), widerRadius)

        return MagnetDetails(Vector(x, y), magnetCount, angles, rampDirection, rampCentreAdjustment, rampLengthMultiplier, wallThickness)
