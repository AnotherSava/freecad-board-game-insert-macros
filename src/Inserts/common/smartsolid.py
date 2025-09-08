from FreeCAD import Vector


class SmartSolid:
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
        self.solid = None

    def getVector(self):
        return Vector(self.x, self.y, self.z)

    def translateVector(self, vector: Vector):
        self.baseVector(self.getVector() + vector)

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

        self.solid.Placement.Base = Vector(x, y, z)
