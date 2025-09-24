from math import floor

import Part
from FreeCAD import Vector

from Inserts.common.fuser import Fuser, fuseAll, getElement
from enum import IntEnum


def createColour(red: float, green: float, blue: float) -> int:
    assert 0 <= red <= 1, f"Red value {red} must be in range [0, 1]"
    assert 0 <= green <= 1, f"Green value {green} must be in range [0, 1]"
    assert 0 <= blue <= 1, f"Blue value {blue} must be in range [0, 1]"

    redInt = int(floor(red * 255))
    greenInt = int(floor(green * 255))
    blueInt = int(floor(blue * 255))

    return (redInt << 16) | (greenInt << 8) | blueInt

class Colour(IntEnum):
    BLACK = createColour(0.0, 0.0, 0.0)
    BLUE = createColour(0.0, 0.0, 1.0)
    BROWN = createColour(0.6, 0.3, 0.1)
    GRAY = createColour(0.5, 0.5, 0.5)
    GREEN = createColour(0.0, 1.0, 0.0)
    WHITE = createColour(1.0, 1.0, 1.0)
    YELLOW = createColour(1.0, 1.0, 0.0)
    BASE = createColour(0.9, 0.9, 0.1)
    MESH = createColour(0.8, 0.0, 0.8)
    WALLED_MESH = createColour(0.3, 0.0, 0.3)

    def decode(self) -> tuple[float, float, float]:
        redInt = (self.value >> 16) & 0xFF
        greenInt = (self.value >> 8) & 0xFF
        blueInt = self.value & 0xFF
        return redInt / 255.0, greenInt / 255.0, blueInt / 255.0
    
    def getName(self) -> str:
        return self.name.lower().replace("_", "-")

class MultiColourFuser:
    def __init__(self, colour: Colour = None, element = None):
        self.fuserByColour = {}
        if colour is not None and element is not None:
            self.fuse(colour, element)

    def fuse(self, colour: Colour, element) -> 'MultiColourFuser':
        if colour not in self.fuserByColour:
            self.fuserByColour[colour] = Fuser(element)
        else:
            self.fuserByColour[colour].fuse(element)

        return self

    def fuseAll(self, *args: 'MultiColourFuser') -> 'MultiColourFuser':
        for arg in args:
            for (colour, fuser) in arg.fuserByColour.items():
                self.fuse(colour, fuser.solid)

        return self

    def fuseColour(self, colour: Colour, *args: 'MultiColourFuser') -> 'MultiColourFuser':
        for arg in args:
            elem = arg.fuserByColour[colour]
            if elem:
                self.fuse(colour, elem.solid)

        return self

    def fuseUnique(self, colour: Colour, element) -> 'MultiColourFuser':
        uniqueSolid = getElement(element).copy()
        for fuser in self.fuserByColour.values():
            uniqueSolid = uniqueSolid.cut(fuser.solid)

        return self.fuse(colour, uniqueSolid)

    def replace(self, colour: Colour, element) -> 'MultiColourFuser':
        self.cut(element)
        return self.fuse(colour, element)

    def common(self, solid: Part.Solid) -> 'MultiColourFuser':
        for fuser in self.fuserByColour.values():
            fuser.common(solid)

        return self

    def cut(self, *args) -> 'MultiColourFuser':
        for arg in args:
            for fuser in self.fuserByColour.values():
                fuser.cut(arg)

        return self

    def translate(self, vector: Vector) -> 'MultiColourFuser':
        for fuser in self.fuserByColour.values():
            fuser.translate(vector)

        return self

    def rotate(self, centre: Vector, axis: Vector, angle: float) -> 'MultiColourFuser':
        for fuser in self.fuserByColour.values():
            fuser.rotate(centre, axis, angle)

        return self

    def mirrorX(self):
        for fuser in self.fuserByColour.values():
            fuser.mirrorX()
        return self

    def mirrorY(self):
        for fuser in self.fuserByColour.values():
            fuser.mirrorY()
        return self

    def mirrorZ(self):
        for fuser in self.fuserByColour.values():
            fuser.mirrorZ()
        return self

    def getResult(self):
        return fuseAll(fuser.solid for fuser in self.fuserByColour.values())

    def show(self, transparency: int = 0):
        for (color, fuser) in self.fuserByColour.items():
            feature = Part.show(fuser.solid, color.getName())
            feature.ViewObject.ShapeColor = color.decode()
            feature.ViewObject.Transparency = transparency
