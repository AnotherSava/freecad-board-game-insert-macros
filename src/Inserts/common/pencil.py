from math import cos, radians

import Part
from FreeCAD import Vector

from Inserts.common.geometry import createVector, shiftVector


class Pencil:
    def __init__(self, start: Vector = Vector(0, 0)):
        self.curves = []
        self.start = start
        self.location = start

    def arc(self, radius: float, centreAngle: float, arcDegrees: float):
        centre = shiftVector(self.location, radius, centreAngle)
        degreesDestinationFromCentre = ((arcDegrees + centreAngle + 180) % 360) * (1 if arcDegrees > 0 else -1)
        degreesMiddleFromCentre = ((arcDegrees / 2 + centreAngle + 180) % 360) * (1 if arcDegrees > 0 else -1)
        destination = shiftVector(centre, radius, degreesDestinationFromCentre)
        middle = shiftVector(centre, radius, degreesMiddleFromCentre)
        self.curves.append(Part.Arc(self.location, middle, destination))
        self.location = destination
        return self

    def jump(self, destination: Vector):
        self.curves.append(Part.LineSegment(self.location, destination))
        self.location = destination
        return self

    def draw(self, length: float, angle: float):
        destination = shiftVector(self.location, length, angle)
        return self.jump(destination)

    def up(self, length: float):
        return self.draw(length, 0)

    def left(self, length: float):
        return self.draw(length, 90)

    def down(self, length: float):
        return self.draw(length, 180)

    def right(self, length: float):
        return self.draw(length, -90)

    def extrude(self, height: float):
        wire = self.createWire()
        face = Part.Face(wire)
        return face.extrude(Vector(0, 0, height))

    def createWire(self):
        if self.location != self.start:
            self.curves.append(Part.LineSegment(self.location, self.start))

        return Part.Wire([curve.toShape() for curve in self.curves])
