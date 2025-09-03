import Part
from FreeCAD import Vector
from Part import Solid

from Inserts.common.fuser import Fuser, Fusible
from Inserts.common.geometry import Side
from Inserts.common.pencil import Pencil

class SmartBox(Fusible):
    def __init__(self, length: float, width: float, height: float):
        self.x = 0
        self.y = 0
        self.z = 0

        self.xTo = length
        self.yTo = width
        self.zTo = height

        self.length = length
        self.width = width
        self.height = height
        self.box = Part.makeBox(length, width, height)

    def getElement(self):
        return self.box

    def translate(self, x: float, y: float, z: float):
        self.base(self.x + x, self.y + y, self.z + z)

    def baseVector(self, vector: Vector):
        self.base(vector.x, vector.y, vector.z)

    def base(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

        self.xTo = x + self.length
        self.yTo = y + self.width
        self.zTo = z + self.height

        self.box.Placement.Base = Vector(x, y, z)

    def addCut(self, side: Side, length: float, extraWidth: float, height: float, shift: float = 0):
        preCutCoefficient = 0.2
        pencil = Pencil(Vector(-length / 2 + shift, -extraWidth))
        pencil.arcWithRadius(length / 2 * preCutCoefficient, 0, 90)
        pencil.arcWithRadius(length / 2 * (1 - preCutCoefficient), -90, -180)
        pencil.arcWithRadius(length / 2 * preCutCoefficient, -90, 90)
        solid = pencil.extrude(height * 2 + self.height)
        solid.rotate(Vector(), Vector(0, 0, 1), side.value).translate(self.getTranslateVector(side, height))
        self.box = self.box.fuse(solid)

    def addLedge(self, side: Side, height: float = None, coefficient: float = 0.15, thickness: float = 1.2):
        ledge = self.createLedge(side, coefficient, thickness)
        cylinders = self.createEllipticalCylinders(coefficient, thickness)
        cylinderLedge = ledge.common(cylinders).translate(Vector(0, 0, (height or self.height) - thickness))
        # feature = Part.show(cylinders)
        # feature.ViewObject.ShapeColor = (0.2, 0.8, 0.8)
        self.box = self.box.cut(cylinderLedge)

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
        return fuser.getResult()

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
