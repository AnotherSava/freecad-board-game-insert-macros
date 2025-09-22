from math import cos, sin, radians

import Part
from FreeCAD import Vector
from Part import Solid, Face
from Part import Wire

from enum import IntEnum


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

def createWire(*points) -> Wire:
    return Wire(Part.makeLine(points[i], points[(i + 1) % len(points)]) for i in range(len(points)))

def extrudeWire(wire: Wire, height: float) -> Solid:
    face = Face(wire)
    return face.extrude(Vector(0, 0, height))

def alignSeveralWithin(size: float, leftBorder: float, rightBorder: float, index: int, count: int, sideInterval: float = None):
    if sideInterval is None:
        interval = (leftBorder + rightBorder - size * count) / (count + 1)
        return interval * (index + 1) + size * index
    else:
        interval = (leftBorder + rightBorder - size * count - sideInterval * 2) / (count - 1)
        return sideInterval + (interval + size) * index
