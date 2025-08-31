from math import cos, sin, radians

from FreeCAD import Vector
from Part import LineSegment, Solid, Face
from Part import Wire


# angle is measured in degrees CCW from axis Y
def createVector(length: float, angle: float) -> Vector:
    return Vector(-length * sin(radians(angle)), length * cos(radians(angle)))

# angle is measured in degrees CCW from axis Y
def shiftVector(vector: Vector, length: float, angle: float) -> Vector:
    return vector + createVector(length, angle)

# invert the x-axis of a vector
def invertX(vector: Vector) -> Vector:
    return Vector(-vector.x, vector.y, vector.z)

# angle is measured in degrees CCW from axis Y
def shiftVectorTwice(vector: Vector, length1: float, angle1: float, length2: float, angle2: float) -> Vector:
    return shiftVector(shiftVector(vector, length1, angle1), length2, angle2)

def createWire(points: list[Vector]) -> Wire:
    edges = []
    for i in range(len(points)):
        edge = LineSegment(points[i], points[(i + 1) % len(points)])
        edges.append(edge)

    return Wire([edge.toShape() for edge in edges])

def extrudeWire(wire: Wire, height: float) -> Solid:
    face = Face(wire)
    return face.extrude(Vector(0, 0, height))
