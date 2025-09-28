from FreeCAD import Vector


class SmartSolid:
    def __init__(self, length: float, width: float, height: float, x: float = 0, y: float = 0, z: float = 0):
        self.length = length
        self.width = width
        self.height = height
        self.solid = None

        self.x = x
        self.y = y
        self.z = z

        self.xTo = x + length
        self.yTo = x + width
        self.zTo = z + height


    def getVector(self):
        return Vector(self.x, self.y, self.z)

    def translateVector(self, vector: Vector):
        self.baseVector(self.getVector() + vector)

    def translate(self, x: float, y: float = 0, z: float = 0) -> 'SmartSolid':
        self.base(self.x + x, self.y + y, self.z + z)
        return self

    def baseVector(self, vector: Vector):
        self.base(vector.x, vector.y, vector.z)

    def base(self, x: float = 0, y: float = 0, z: float = 0):
        self.x = x
        self.y = y
        self.z = z

        self.xTo = x + self.length
        self.yTo = y + self.width
        self.zTo = z + self.height

        self.solid.Placement.Base = Vector(x, y, z)
