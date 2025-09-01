from math import cos, radians

import Part
from FreeCAD import Vector

from Inserts.common.geometry import createVector
from dataclasses import dataclass


@dataclass
class CylinderObjectSet:
    diameter: float
    height: float
    name: str = None
    count: float = None
    separate: bool = False

    def getRecessDepth(self):
        return self.height * 0.4

    def getVisibleHeight(self):
        return self.height - self.getRecessDepth()

class MultiCylinderHolder:
    def __init__(self, diameter: float, count: int, horizontal: bool = True):
        self.diameter = diameter
        self.count = count
        self.horizontal = horizontal

    def getTotalWidth(self):
        return self.diameter * (self.count if self.horizontal else 1)

    def getTotalLength(self):
        return self.diameter * (1 if self.horizontal else self.count)

    def getCircleCentre(self, index: int) -> Vector:
        return Vector(self.diameter * (index + 0.5), self.diameter / 2)

    def getCirclePoint(self, index: int, angle: float) -> Vector:
        return self.getCircleCentre(index) + createVector(self.diameter / 2, angle)

    def getConnectiveArcExtremum(self, index: int, top: bool) -> Vector:
        return self.getCircleCentre(index) + Vector(self.diameter / 2, self.diameter * (1 - cos(radians(45))) * (1 if top else -1))

    def createWire(self) -> Part.Wire:
        arcs = []

        for i in range(self.count):
            arcs.append(Part.Arc(self.getCirclePoint(i, 45), self.getCirclePoint(i, 0), self.getCirclePoint(i, -45)))
            if i < self.count - 1:
                arcs.append(Part.Arc(self.getCirclePoint(i, -45), self.getConnectiveArcExtremum(i, True), self.getCirclePoint(i + 1, 45)))

        arcs.append(Part.Arc(self.getCirclePoint(self.count - 1, -45), self.getCirclePoint(self.count - 1, -90), self.getCirclePoint(self.count - 1, -135)))

        for i in reversed(range(self.count)):
            arcs.append(Part.Arc(self.getCirclePoint(i, -135), self.getCirclePoint(i, 180), self.getCirclePoint(i, 135)))
            if i > 0:
                arcs.append(Part.Arc(self.getCirclePoint(i, 135), self.getConnectiveArcExtremum(i - 1, False), self.getCirclePoint(i - 1, -135)))

        arcs.append(Part.Arc(self.getCirclePoint(0, 135), self.getCirclePoint(0, 90), self.getCirclePoint(0, 45)))

        # Create wire from all edges
        wire = Part.Wire([Part.Edge(arc) for arc in arcs])
        return wire

    def create(self, height: float):
        wire = self.createWire()

        if not self.horizontal:
            wire.rotate(Vector(self.diameter / 2, self.diameter / 2, 0), Vector(0, 0, 1),90)

        face = Part.Face(wire)
        return face.extrude(Vector(0, 0, height))

class DistinctCylinderHolder:
    # evenCentres evenly distributes cylinder centers (rather than empty spaces) across the width
    def __init__(self, diameter: float, count: int, width: float, evenCentres: bool = False):
        self.diameter = diameter
        self.count = count
        self.width = width
        self.evenCentres = evenCentres

    def getCircleCentre(self, index: int) -> Vector:
        if self.evenCentres:
            return Vector((self.width / self.count) * (index + 0.5), self.diameter / 2)
        else:
            emptySpace = self.width - self.diameter * self.count
            return Vector(emptySpace / (self.count + 1) * (index + 1) + self.diameter * (index + 0.5), self.diameter / 2)

    def create(self, height: float):
        result = None

        for i in range(self.count):
            cylinder = Part.makeCylinder(self.diameter / 2, height, self.getCircleCentre(i))
            result = cylinder if result is None else result.fuse(cylinder)

        return result
