from math import cos, radians

import Part
from FreeCAD import Vector

from Inserts.common.geometry import createVector


class MultiCylinderHolder:
    def __init__(self, diameter: float, count: int):
        self.diameter = diameter
        self.count = count

    def getTotalWidth(self):
        return self.diameter * self.count

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
        face = Part.Face(wire)
        return face.extrude(Vector(0, 0, height))
