from FreeCAD import Vector
import Part
from math import tan, sqrt, cos, sin, radians
from enum import Enum, auto
from dataclasses import dataclass

class HexTimeShiftDirection(Enum):
    UP = auto()
    DOWN = auto()

@dataclass
class GridConfiguration:
    firstColumnHexCount: int
    secondColumnHexCount: int
    columnsTotal: int
    shiftDirection: HexTimeShiftDirection = None # only applicable if secondColumnCount == firstColumnCount

@dataclass
class GridDimensions:
    hexWidth: float
    pinWidth: float
    pinLength: float
    pinRadius: float
    pinHeight: float
    boardHeight: float

    # distance between adjacent hex tile centres
    def getHexCentreDistance(self):
        return self.hexWidth + self.pinWidth

    # distance between adjacent hex tile centres on axis x
    def getHexCentreDistanceX(self):
        return self.getHexCentreDistance() * cos(radians(60))

    # distance between adjacent hex tile centres on axis y
    def getHexCentreDistanceY(self):
        return self.getHexCentreDistance() * sin(radians(60))

# value represents angle (CCW from y axis)
class HexPinSide(Enum):
    TOP = 0
    LEFT = 120
    RIGHT = 240

class HexBoard:
    def __init__(self, configuration: GridConfiguration, dimensions: GridDimensions):
        self.configuration = configuration
        self.dimensions = dimensions

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
        x = self.dimensions.pinRadius * cos(radians(45))
        delta = self.dimensions.pinRadius - x

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

    def createFloor(self):
        hexSizeY = 2 * self.dimensions.hexWidth * tan(radians(30))
        floorX = self.dimensions.getHexCentreDistanceX() * (self.configuration.columnsTotal + 1) + self.dimensions.pinWidth
        floorY = (hexSizeY + self.dimensions.getHexCentreDistanceY() * 2 * (self.configuration.firstColumnHexCount - 1) +
                  self.dimensions.pinWidth / 2 * tan(radians(60)) + self.dimensions.pinWidth * (2 - sqrt(3)) / 2)
        floorPos = Vector(-self.dimensions.pinWidth / 2,
                          self.dimensions.pinWidth / 2 * tan(radians(30)) - self.dimensions.hexWidth / 2 * tan(radians(30)),
                          -self.dimensions.boardHeight)
        box = Part.makeBox(floorX, floorY, self.dimensions.boardHeight, floorPos)
        boxFeature = Part.show(box, "box")
        boxFeature.ViewObject.ShapeColor = (0.8, 0.6, 0.2)

    def createPin(self, column, row, skip, shiftY):
        wire = self.createPinWire(skip)
        wire.translate(Vector(column * self.dimensions.getHexCentreDistanceX(), shiftY + row * self.dimensions.getHexCentreDistanceY() * 2))
        face = Part.Face(wire)
        pin = face.extrude(Vector(0, 0, self.dimensions.pinHeight))  # Extrude to make a solid (height=1mm)
        pinFeature = Part.show(pin, f"pin {column}-{row}")
        pinFeature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)

    def createBoard(self):
        for column in range(0, self.configuration.columnsTotal + 2):
            shiftY = 0 if column % 2 == 0 else self.dimensions.getHexCentreDistanceY()

            for row in range(0, self.configuration.firstColumnHexCount):
                skip = HexPinSide.LEFT if column == 0 \
                    else HexPinSide.RIGHT if column == self.configuration.columnsTotal + 1 \
                    else HexPinSide.TOP if row == self.configuration.firstColumnHexCount - 1 and column % 2 == 1 \
                    else None
                self.createPin(column, row, skip, shiftY)

        self.createFloor()
