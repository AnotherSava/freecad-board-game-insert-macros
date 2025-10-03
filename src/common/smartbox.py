import Part
from FreeCAD import Vector
from Part import Solid

from common.fuser import Fuser
from common.geometry import Side
from common.magnets import MagnetDetails, RampDetails
from common.pencil import Pencil
from common.smartsolid import SmartSolid


class SmartBox(SmartSolid):
    def __init__(self, length: float, width: float, height: float, x: float = 0, y: float = 0, z: float = 0):
        super().__init__(length, width, height, x, y, z)

        self.solid = Part.makeBox(length, width, height, Vector(x, y, z))

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

    # def createCornerMagnetDetails(self, widerRadius: float, count: int = 1) -> list[MagnetDetails]:
    #     return [self.createMagnetDetails(row, column, 2, 2, widerRadius, CornerAngleType.MIN, None, count) for row in range(2) for column in range(2)]

    def createMagnetDetails(self, row: int, column: int, rowCount: int, columnCount: int, widerRadius: float, cornerAngle: list[int] = None, cutAngle: list[int] = None, ramp: RampDetails = None,
                            cornerHeight: float = None, magnetCount: int = 1, adjacentToWidening: bool = True):
        x = max(min(column * self.length / (columnCount - 1), self.length - widerRadius), widerRadius)
        y = max(min(row * self.width / (rowCount - 1), self.width - widerRadius), widerRadius)

        return MagnetDetails(Vector(x, y), magnetCount, cornerAngle, cutAngle, cornerHeight, ramp, adjacentToWidening)
