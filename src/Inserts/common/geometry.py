from math import cos, sin, radians
from enum import IntEnum

from FreeCAD import Vector
from Part import LineSegment, Solid, Face
from Part import Wire


class Side(IntEnum):
    S = 180
    E = 270
    N = 0
    W = 90


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

def alignWithin(size: float, leftBorder: float, rightBorder: float):
    return (leftBorder + rightBorder - size) / 2

def alignSeveralWithin(size: float, leftBorder: float, rightBorder: float, index: int, count: int, sideInterval: float = None):
    if sideInterval is None:
        interval = (leftBorder + rightBorder - size * count) / (count + 1)
        return interval * (index + 1) + size * index
    else:
        interval = (leftBorder + rightBorder - size * count - sideInterval * 2) / (count - 1)
        return sideInterval + (interval + size) * index

def alignSeveralCentre(size: float, leftBorder: float, rightBorder: float, index: int, count: int, interval: float):
    return (rightBorder + leftBorder - size * count - interval * (count - 1)) / 2 + (size + interval) * index
