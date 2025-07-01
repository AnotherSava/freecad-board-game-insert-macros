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

def create_hex_pin(width, length, radius, skip = None):
    a = width / 2 * tan(radians(30))
    centre = Vector(0, 0, 0)
    z_axis = Vector(0, 0, 1)
    translate = Vector(0, a, 0)

    edges = []
    for side in [HexPinSide.TOP, HexPinSide.RIGHT, HexPinSide.LEFT]: # order is important
        angle = side.value
        wire = create_rounded_side_wire(width, length, radius, skip == side)
        wire.translate(translate)
        wire.rotate(centre, z_axis, angle)
        edges += list(wire.Edges)

    return Part.Wire(edges)

def create_rounded_side_wire(width, length, radius, skip = False):
    x = radius * cos(radians(45))
    delta = radius - x

    v1 = Vector(-width / 2, 0, 0)

    v2 = Vector(-width / 2, length - radius, 0)
    v23 = Vector(-width / 2 + delta, length - delta, 0)
    v3 = Vector(-width / 2 + radius, length, 0)

    v4 = Vector(width / 2 - radius, length, 0)
    v45 = Vector(width / 2 - delta, length - delta, 0)
    v5 = Vector(width / 2, length - radius, 0)

    v6 = Vector(width / 2, 0, 0)
    v61 = Vector(0, width * (2 - sqrt(3)) / 2, 0)

    edges = [Part.Arc(v6, v61, v1).toShape()] if skip else [
        Part.LineSegment(v1, v2).toShape(),
        Part.Arc(v2, v23, v3).toShape(),
        Part.LineSegment(v3, v4).toShape(),
        Part.Arc(v4, v45, v5).toShape(),
        Part.LineSegment(v5, v6).toShape()
    ]

    return Part.Wire(edges)

def create_hex_board(configuration: GridConfiguration, dimensions: GridDimensions):
    # distance between adjacent hex tile centres
    hex_centre_distance = dimensions.hexWidth + dimensions.pinWidth

    # distance between adjacent hex tile centres on axis x
    hex_centre_distance_x = hex_centre_distance * cos(radians(60))

    # distance between adjacent hex tile centres on axis y
    hex_centre_distance_y = hex_centre_distance * sin(radians(60))

    for column in range(0, configuration.columnsTotal + 2):
        y_shift = 0 if column % 2 == 0 else hex_centre_distance_y

        for row in range(0, configuration.firstColumnHexCount):
            skip = HexPinSide.LEFT if column == 0 \
                else HexPinSide.RIGHT if column == configuration.columnsTotal + 1 \
                else HexPinSide.TOP if row == configuration.firstColumnHexCount - 1 and column % 2 == 1 \
                else None
            wire = create_hex_pin(dimensions.pinWidth, dimensions.pinLength, dimensions.pinRadius, skip)
            wire.translate(Vector(column * hex_centre_distance_x, y_shift + row * hex_centre_distance_y * 2))
            face = Part.Face(wire)
            solid = face.extrude(Vector(0, 0, dimensions.pinHeight))  # Extrude to make a solid (height=1mm)

            frame_feature = Part.show(solid, f"pin {column}-{row}")
            frame_feature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)

    hex_y = 2 * dimensions.hexWidth * tan(radians(30))

    board_x = hex_centre_distance_x * (configuration.columnsTotal + 1) + dimensions.pinWidth
    board_y = hex_y + hex_centre_distance_y * 2 * (
            configuration.firstColumnHexCount - 1) + dimensions.pinWidth / 2 * tan(
        radians(60)) + dimensions.pinWidth * (2 - sqrt(3)) / 2
    board_pos = Vector(-dimensions.pinWidth / 2, dimensions.pinWidth / 2 * tan(radians(30)) - dimensions.hexWidth / 2 * tan(radians(30)), -dimensions.boardHeight)
    box = Part.makeBox(board_x, board_y, dimensions.boardHeight, board_pos)
    frame_feature = Part.show(box, "box")
    frame_feature.ViewObject.ShapeColor = (0.8, 0.6, 0.2)
