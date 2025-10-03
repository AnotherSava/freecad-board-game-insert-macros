from FreeCAD import Vector, Part

from common.pencil import Pencil


def createTaperedBox(bottomLength: float, bottomWidth: float, height: float, topLength: float, topWidth: float):
    bottomWire = Pencil(Vector(-bottomLength / 2, -bottomWidth / 2)).up(bottomWidth).right(bottomLength).down(bottomWidth).createWire()
    topWire = Pencil(Vector(-topLength / 2, -topWidth / 2, height)).up(topWidth).right(topLength).down(topWidth).createWire()

    return Part.makeLoft([bottomWire, topWire], True)
