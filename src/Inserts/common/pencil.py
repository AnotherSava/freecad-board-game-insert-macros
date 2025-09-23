from math import tan, radians

import Part
from FreeCAD import Vector

from Inserts.common.geometry import shiftVector


class Pencil:
    # If relative, all vectors are relative to start vector
    def __init__(self, start: Vector = Vector(0, 0)):
        self.curves = []
        self.start = start
        self.location = start

    def checkDestination(self, destination: Vector) -> Vector:
        tolerance = 1e-7
        return self.start if (destination - self.start).Length < tolerance else destination


    def arcWithRadius(self, radius: float, centreAngle: float, arcDegrees: float):
        centre = shiftVector(self.location, radius, centreAngle)
        degreesDestinationFromCentre = ((arcDegrees + centreAngle + 180) % 360)
        degreesMiddleFromCentre = ((arcDegrees / 2 + centreAngle + 180) % 360)
        destination = self.checkDestination(shiftVector(centre, radius, degreesDestinationFromCentre))
        middle = shiftVector(centre, radius, degreesMiddleFromCentre)
        self.curves.append(Part.Arc(self.location, middle, destination))
        self.location = destination
        return self

    # create arc with specific destination and angle measure
    def arcTo(self, absDestination: Vector, angle: float):
        # Calculate chord (straight line distance between start and end)
        absDestination = self.checkDestination(absDestination)
        chord = absDestination - self.location
        chordMidpoint = (self.location + absDestination) / 2
        
        # Direction perpendicular to chord (for center calculation)
        perpDirection = Vector(-chord.y, chord.x).normalize()

        perpDistance = chord.Length / 2 * tan(radians(angle / 2))
        midpoint = chordMidpoint - perpDirection * perpDistance
        self.curves.append(Part.Arc(self.location, midpoint, absDestination))
        self.location = absDestination
        return self

    # create arc with specific destination and angle measure
    def arcFromStart(self, destination: Vector, angle: float):
        return self.arcTo(destination + self.start, angle)

    # create arc with specific destination and angle measure
    def arc(self, destination: Vector, angle: float):
        return self.arcTo(destination + self.location, angle)

    def jumpTo(self, absDestination: Vector):
        absDestination = self.checkDestination(absDestination)
        self.curves.append(Part.LineSegment(self.location, absDestination))
        self.location = absDestination
        return self

    def jump(self, destination: Vector):
        return self.jumpTo(destination + self.location)

    def jumpFromStart(self, destination: Vector):
        return self.jumpTo(destination + self.start)

    def draw(self, length: float, angle: float):
        absDestination = shiftVector(self.location, length, angle)
        return self.jumpTo(absDestination)

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

    def extrudeX(self, height: float, transpose: Vector = Vector()):
        solid = self.extrude(height)
        solid.rotate(self.start, Vector(1, 0, 0), 90).rotate(self.start, Vector(0, 0, 1), 90)
        solid.translate(transpose)
        return solid

    def extrudeY(self, height: float):
        solid = self.extrude(-height)
        solid.rotate(self.start, Vector(1, 0, 0), 90)
        return solid

    def createWire(self):
        curves = self.curves.copy()
        if self.location != self.start:
            curves.append(Part.LineSegment(self.location, self.start))

        return Part.Wire([curve.toShape() for curve in curves])
