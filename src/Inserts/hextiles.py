import FreeCAD
import Part
import math
from enum import Enum

class HexPinSide(Enum):
    TOP = 0
    RIGHT = 1
    LEFT = 2

def create_hex_pin(width, length, radius, skip = None):
    a = width / 2 * math.tan(math.radians(30))
    centre = FreeCAD.Vector(0, 0, 0)
    z_axis = FreeCAD.Vector(0, 0, 1)
    translate = FreeCAD.Vector(0, a, 0)

    edges = []
    for side in HexPinSide:
        angle = -120 * side.value
        wire = create_rounded_side_wire(width, length, radius, skip == side)
        wire.translate(translate)
        wire.rotate(centre, z_axis, angle)
        edges += list(wire.Edges)

    return Part.Wire(edges)

def create_rounded_side_wire(width, length, radius, skip = False):
    x = radius * math.cos(math.radians(45))
    delta = radius - x

    v1 = FreeCAD.Vector(-width / 2, 0, 0)

    v2 = FreeCAD.Vector(-width / 2, length - radius, 0)
    v23 = FreeCAD.Vector(-width / 2 + delta, length - delta, 0)
    v3 = FreeCAD.Vector(-width / 2 + radius, length, 0)

    v4 = FreeCAD.Vector(width / 2 - radius, length, 0)
    v45 = FreeCAD.Vector(width / 2 - delta, length - delta, 0)
    v5 = FreeCAD.Vector(width / 2, length - radius, 0)

    v6 = FreeCAD.Vector(width / 2, 0, 0)
    v61 = FreeCAD.Vector(0, width * (2 - math.sqrt(3)) / 2, 0)

    edges = [Part.Arc(v6, v61, v1).toShape()] if skip else [
        Part.LineSegment(v1, v2).toShape(),
        Part.Arc(v2, v23, v3).toShape(),
        Part.LineSegment(v3, v4).toShape(),
        Part.Arc(v4, v45, v5).toShape(),
        Part.LineSegment(v5, v6).toShape()
    ]

    return Part.Wire(edges)

def create_hex_board(count_y, count_x, hex_width, pin_width, pin_length, pin_radius, pin_height, board_height):
    # distance between adjacent hex tile centres
    hex_centre_distance = hex_width + pin_width

    # distance between adjacent hex tile centres on axis x
    hex_centre_distance_x = hex_centre_distance * math.cos(math.radians(60))

    # distance between adjacent hex tile centres on axis y
    hex_centre_distance_y = hex_centre_distance * math.sin(math.radians(60))

    for column in range(0, count_x + 2):
        y_shift = 0 if column % 2 == 0 else hex_centre_distance_y

        for row in range(0, count_y):
            skip = HexPinSide.LEFT if column == 0 \
                else HexPinSide.RIGHT if column == count_x + 1 \
                else HexPinSide.TOP if row == count_y - 1 and column % 2 == 1 \
                else None
            wire = create_hex_pin(pin_width, pin_length, pin_radius, skip)
            wire.translate(FreeCAD.Vector(column * hex_centre_distance_x, y_shift + row * hex_centre_distance_y * 2))
            face = Part.Face(wire)
            solid = face.extrude(FreeCAD.Vector(0, 0, pin_height))  # Extrude to make a solid (height=1mm)

            frame_feature = Part.show(solid, f"pin {column}-{row}")
            frame_feature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)

    hex_y = 2 * hex_width * math.tan(math.radians(30))

    board_x = hex_centre_distance_x * (count_x + 1) + pin_width
    board_y = hex_y + hex_centre_distance_y * 2 * (count_y - 1) + pin_width / 2 * math.tan(math.radians(60)) + pin_width * (2 - math.sqrt(3)) / 2
    board_pos = FreeCAD.Vector(-pin_width / 2, pin_width / 2 * math.tan(math.radians(30)) - hex_width / 2 * math.tan(math.radians(30)), -board_height)
    box = Part.makeBox(board_x, board_y, board_height, board_pos)
    frame_feature = Part.show(box, "box")
    frame_feature.ViewObject.ShapeColor = (0.8, 0.6, 0.2)


def create_object(width, length, height, radius):
    # wire = make_rounded_side(width, length, 3, True)
    wire = create_hex_pin(width, length, radius)
    face = Part.Face(wire)

    # face = create_face(width, length)
    # face = make_rectangle()
    # face = Part.Face(wire)

    solid = face.extrude(FreeCAD.Vector(0, 0, height))  # Extrude to make a solid (height=1mm)

    frame_feature = Part.show(solid, 'test object')
    frame_feature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)
