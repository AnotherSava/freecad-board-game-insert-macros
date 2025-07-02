from FreeCAD import Vector
import Part
from math import tan, sqrt, cos, sin, radians
from enum import Enum, auto
from dataclasses import dataclass
import numpy as np

class HexTimeShiftDirection(Enum):
    UP = auto()
    DOWN = auto()

@dataclass
class GridConfiguration:
    firstColumnHexCount: int
    secondColumnHexCount: int
    columnsTotal: int
    shiftDirection: HexTimeShiftDirection = None # is not none only if secondColumnCount == firstColumnCount

    def __post_init__(self):
        if self.firstColumnHexCount == self.secondColumnHexCount and self.shiftDirection is None:
            raise ValueError("Shift direction must be specified")

    def getHexCountInColumn(self, column):
        return 0 if column < 0 or column >= self.columnsTotal \
            else self.firstColumnHexCount if column % 2 == 0 \
            else self.secondColumnHexCount

    def getBottomPinsRowIndexForColumn(self, column):
        if column % 2 == 0:
            return 0 if self.shiftDirection is HexTimeShiftDirection.UP or self.secondColumnHexCount < self.firstColumnHexCount else 1

        return 0 if self.shiftDirection is HexTimeShiftDirection.DOWN or self.secondColumnHexCount > self.firstColumnHexCount else 1

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

class PinConfiguration:
    def __init__(self, configuration: GridConfiguration):
        self.configuration = configuration

        self.sizeX = self.configuration.columnsTotal + 2
        self.sizeY = self.configuration.firstColumnHexCount + self.configuration.secondColumnHexCount + 1

        self.pinBoard = np.empty((self.sizeX, self.sizeY), dtype=object)

    def addRays(self, column, row, rays):
        currentRays = self.pinBoard[column, row]
        self.pinBoard[column, row] = rays if currentRays is None else list(set(currentRays) | set(rays))

    def doesPinExist(self, column, row):
        return self.pinBoard[column, row] is not None

    def findMissingRay(self, column, row):
        if len(self.pinBoard[column, row]) < 2:
            raise ValueError("Pin expected to have at least 2 rays")

        for side in HexPinSide:
            if side not in self.pinBoard[column, row]:
                return side
        return None

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

    def createFloor(self, pinConfiguration):
        hexSizeY = 2 * self.dimensions.hexWidth * tan(radians(30))
        floorX = self.dimensions.getHexCentreDistanceX() * (pinConfiguration.sizeX - 1) + self.dimensions.pinWidth
        floorY = hexSizeY + self.dimensions.getHexCentreDistanceY() * (pinConfiguration.sizeY - 2) + self.dimensions.pinWidth / 2 * tan(radians(60)) + self.dimensions.pinWidth * (2 - sqrt(3)) / 2
        floorPos = Vector(-self.dimensions.pinWidth / 2,
                          self.dimensions.pinWidth / 2 * tan(radians(30)) - self.dimensions.hexWidth / 2 * tan(radians(30)),
                          -self.dimensions.boardHeight)
        box = Part.makeBox(floorX, floorY, self.dimensions.boardHeight, floorPos)
        boxFeature = Part.show(box, "box")
        boxFeature.ViewObject.ShapeColor = (0.8, 0.6, 0.2)

    def createPin(self, column, row, skip):
        wire = self.createPinWire(skip)
        wire.translate(Vector(column * self.dimensions.getHexCentreDistanceX(), row * self.dimensions.getHexCentreDistanceY()))
        face = Part.Face(wire)
        pin = face.extrude(Vector(0, 0, self.dimensions.pinHeight))  # Extrude to make a solid (height=1mm)
        pinFeature = Part.show(pin, f"pin {column}-{row}")
        pinFeature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)

    def createPinConfiguration(self):
        pinConfiguration = PinConfiguration(self.configuration)

        for column in range(0, self.configuration.columnsTotal):
            shiftY = self.configuration.getBottomPinsRowIndexForColumn(column)

            for row in range(0, self.configuration.getHexCountInColumn(column)):
                bottomPinIndex = shiftY + row * 2
                pinConfiguration.addRays(column, bottomPinIndex, [HexPinSide.TOP, HexPinSide.RIGHT])
                pinConfiguration.addRays(column + 1, bottomPinIndex + 1, [HexPinSide.LEFT, HexPinSide.RIGHT])
                pinConfiguration.addRays(column + 2, bottomPinIndex, [HexPinSide.TOP, HexPinSide.LEFT])

        return pinConfiguration

    def createBoard(self):
        pinConfiguration = self.createPinConfiguration()

        for column in range(0, pinConfiguration.sizeX):
            for row in range(0, pinConfiguration.sizeY):
                if not pinConfiguration.doesPinExist(column, row):
                    continue

                skip = pinConfiguration.findMissingRay(column, row)
                self.createPin(column, row, skip)

        self.createFloor(pinConfiguration)
