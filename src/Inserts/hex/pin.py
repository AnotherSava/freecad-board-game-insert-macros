from math import tan, sqrt, cos, sin, radians

import Part
from Part import LineSegment, Arc, Wire
from FreeCAD import Vector

from Inserts.hex.configuration import GridDimensions, HexPinSide

from Inserts.common.geometry import shiftVector, shiftVectorTwice

class PinFactory:
    def __init__(self, dimensions: GridDimensions):
        self.dimensions = dimensions

    # create wire from the centre of the far side of one ray to the centre of the far side of the next one
    # full pin consists of three such wires
    def createAnglePinWire(self) -> Wire:
        v1 = Vector(0, self.dimensions.pinLength)
        v2 = shiftVector(v1, self.dimensions.pinWidth / 2 - self.dimensions.pinRadius, -90)
        v23 = shiftVectorTwice(v2, self.dimensions.pinRadius, 180, self.dimensions.pinRadius, -45)
        v3 = shiftVectorTwice(v23, self.dimensions.pinRadius, 135, self.dimensions.pinRadius, -90)
        v4 = shiftVector(v3, self.dimensions.pinLength - self.dimensions.pinRadius, 180)
        v5 = shiftVector(v4, self.dimensions.pinLength - self.dimensions.pinRadius, -120)

        v56 = shiftVectorTwice(v5, self.dimensions.pinRadius, 150, self.dimensions.pinRadius, -75)
        v6 = shiftVectorTwice(v56, self.dimensions.pinRadius, 105, self.dimensions.pinRadius, -120)
        v7 = shiftVector(v6, self.dimensions.pinWidth / 2 - self.dimensions.pinRadius, 150)

        parts = [
            LineSegment(v1, v2),
            Arc(v2, v23, v3),
            LineSegment(v3, v4),
            LineSegment(v4, v5),
            Arc(v5, v56, v6),
            LineSegment(v6, v7)
        ]

        return Part.Wire([part.toShape() for part in parts])

    # create wire from the centre of the far side of one ray, skipping next one and going to the centre of the far side of the one after
    # two-ray pin consists of one angle pin wire and one outer pin wire
    def createOuterPinWire(self) -> Wire:
        lengthToCentre = self.dimensions.pinLength + self.dimensions.pinWidth / 2 * tan(radians(30))
        # delta = self.dimensions.pinRadius * (1 - cos(radians(45)))

        v1 = Vector(0, self.dimensions.pinLength)
        v2 = shiftVector(v1, lengthToCentre, 180)
        v3 = shiftVector(v2, lengthToCentre, 120)

        parts = [
            LineSegment(v1, v2),
            LineSegment(v2, v3)
        ]

        return Part.Wire([part.toShape() for part in parts])

    def createNewPinWire(self, skip = None) -> Wire:
        return self.createNewFullPinWire() if skip is None else self.createNewHalfPinWire(skip)

    def createNewFullPinWire(self) -> Wire:
        a = self.dimensions.pinWidth / 2 * tan(radians(30))
        edges = []
        for side in [HexPinSide.TOP, HexPinSide.RIGHT, HexPinSide.LEFT]: # order is important
            angle = side.value
            wire = self.createAnglePinWire()
            wire.translate(Vector(0, a, 0))
            wire.rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle)
            edges += list(wire.Edges)

        return Part.Wire(edges)

    def createNewHalfPinWire(self, skip) -> Wire:
        a = self.dimensions.pinWidth / 2 * tan(radians(30))
        edges = []

        angle = skip.value
        wire = self.createAnglePinWire()
        wire.translate(Vector(0, a, 0))
        wire.rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle - 120)
        edges += list(wire.Edges)

        wire = self.createOuterPinWire()
        wire.translate(Vector(0, a, 0))
        wire.rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle + 120)
        edges += list(wire.Edges)

        return Part.Wire(edges)

    def createPinWire(self, skip = None):
        a = self.dimensions.pinWidth / 2 * tan(radians(30))
        edges = []
        for side in [HexPinSide.TOP, HexPinSide.RIGHT, HexPinSide.LEFT]: # order is important
            angle = side.value
            wire = self.createPinRayWire(skip == side)
            wire.translate(Vector(0, a, 0))
            wire.rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle)
            edges += list(wire.Edges)

        return Part.Wire(edges)

    def createPinRayWire(self, skip = False):
        delta = self.dimensions.pinRadius * (1 - cos(radians(45)))

        v1 = Vector(-self.dimensions.pinWidth / 2, 0, 0)

        v2 = Vector(-self.dimensions.pinWidth / 2, self.dimensions.pinLength - self.dimensions.pinRadius, 0)
        v23 = Vector(-self.dimensions.pinWidth / 2 + delta, self.dimensions.pinLength - delta, 0)
        v3 = Vector(-self.dimensions.pinWidth / 2 + self.dimensions.pinRadius, self.dimensions.pinLength, 0)

        v4 = Vector(self.dimensions.pinWidth / 2 - self.dimensions.pinRadius, self.dimensions.pinLength, 0)
        v45 = Vector(self.dimensions.pinWidth / 2 - delta, self.dimensions.pinLength - delta, 0)
        v5 = Vector(self.dimensions.pinWidth / 2, self.dimensions.pinLength - self.dimensions.pinRadius, 0)

        v6 = Vector(self.dimensions.pinWidth / 2, 0, 0)
        v61 = Vector(0, self.dimensions.pinWidth * (2 - sqrt(3)) / 2, 0)

        edges = [Part.Arc(v6, v61, v1).toShape()] if skip else [
            Part.LineSegment(v1, v2).toShape(),
            Part.Arc(v2, v23, v3).toShape(),
            Part.LineSegment(v3, v4).toShape(),
            Part.Arc(v4, v45, v5).toShape(),
            Part.LineSegment(v5, v6).toShape()
        ]

        return Part.Wire(edges)

    def createPin(self, column, row, skip):
        # wire = self.createNewPinWire(skip)
        # wire = self.createNewPinWire(skip)
        wire = self.createPinWire(skip)
        wire.translate(Vector(column * self.dimensions.getHexCentreDistanceX(), row * self.dimensions.getHexCentreDistanceY()))
        face = Part.Face(wire)
        return face.extrude(Vector(0, 0, self.dimensions.pinHeight))  # Extrude to make a solid (height=1mm)
