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

# value represents angle (CCW from y axis)
class HexPinSide(Enum):
    TOP = 0
    LEFT = 120
    RIGHT = 240

class HexBoard:
    def __init__(self, configuration: GridConfiguration, dimensions: GridDimensions):
        self.configuration = configuration
        self.dimensions = dimensions

    def createHexPin(self, skip = None):
        a = self.dimensions.pinWidth / 2 * tan(radians(30))
        centre = Vector(0, 0, 0)
        z_axis = Vector(0, 0, 1)
        translate = Vector(0, a, 0)

        edges = []
        for side in [HexPinSide.TOP, HexPinSide.RIGHT, HexPinSide.LEFT]: # order is important
            angle = side.value
            wire = self.createRoundedSideWire(skip == side)
            wire.translate(translate)
            wire.rotate(centre, z_axis, angle)
            edges += list(wire.Edges)

        return Part.Wire(edges)

    def createRoundedSideWire(self, skip = False):
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

    def createBoard(self):
        # distance between adjacent hex tile centres
        hex_centre_distance = self.dimensions.hexWidth + self.dimensions.pinWidth

        # distance between adjacent hex tile centres on axis x
        hex_centre_distance_x = hex_centre_distance * cos(radians(60))

        # distance between adjacent hex tile centres on axis y
        hex_centre_distance_y = hex_centre_distance * sin(radians(60))

        for column in range(0, self.configuration.columnsTotal + 2):
            y_shift = 0 if column % 2 == 0 else hex_centre_distance_y

            for row in range(0, self.configuration.firstColumnHexCount):
                skip = HexPinSide.LEFT if column == 0 \
                    else HexPinSide.RIGHT if column == self.configuration.columnsTotal + 1 \
                    else HexPinSide.TOP if row == self.configuration.firstColumnHexCount - 1 and column % 2 == 1 \
                    else None
                wire = self.createHexPin(skip)
                wire.translate(Vector(column * hex_centre_distance_x, y_shift + row * hex_centre_distance_y * 2))
                face = Part.Face(wire)
                solid = face.extrude(Vector(0, 0, self.dimensions.pinHeight))  # Extrude to make a solid (height=1mm)

                frame_feature = Part.show(solid, f"pin {column}-{row}")
                frame_feature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)

        hex_y = 2 * self.dimensions.hexWidth * tan(radians(30))

        board_x = hex_centre_distance_x * (self.configuration.columnsTotal + 1) + self.dimensions.pinWidth
        board_y = hex_y + hex_centre_distance_y * 2 * (
                self.configuration.firstColumnHexCount - 1) + self.dimensions.pinWidth / 2 * tan(
            radians(60)) + self.dimensions.pinWidth * (2 - sqrt(3)) / 2
        board_pos = Vector(-self.dimensions.pinWidth / 2,
                           self.dimensions.pinWidth / 2 * tan(radians(30)) - self.dimensions.hexWidth / 2 * tan(radians(30)),
                           -self.dimensions.boardHeight)
        box = Part.makeBox(board_x, board_y, self.dimensions.boardHeight, board_pos)
        frame_feature = Part.show(box, "box")
        frame_feature.ViewObject.ShapeColor = (0.8, 0.6, 0.2)
