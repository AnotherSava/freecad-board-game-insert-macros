from math import floor

import Part
from FreeCAD import Vector

from Inserts.common.fuser import Fuser, fuseAll
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

    def decode(self) -> tuple[float, float, float]:
        redInt = (self.value >> 16) & 0xFF
        greenInt = (self.value >> 8) & 0xFF
        blueInt = self.value & 0xFF
        return redInt / 255.0, greenInt / 255.0, blueInt / 255.0
    
    def getName(self) -> str:
        return self.name.lower()

class MultiColourFuser:
    def __init__(self, colour: Colour = None, solid: Part.Solid = None):
        self.fuserByColour = {}
        if colour is not None and solid is not None:
            self.fuse(colour, solid)

    def fuse(self, colour: Colour, solid: Part.Solid) -> 'MultiColourFuser':
        if colour not in self.fuserByColour:
            self.fuserByColour[colour] = Fuser(solid)
        else:
            self.fuserByColour[colour].fuse(solid)

        return self

    def fuseAll(self, other: 'MultiColourFuser') -> 'MultiColourFuser':
        for (colour, fuser) in other.fuserByColour.items():
            self.fuse(colour, fuser.getResult())

        return self
    
    def fuseUnique(self, colour: Colour, solid: Part.Solid) -> 'MultiColourFuser':
        uniqueSolid = solid.copy()
        for fuser in self.fuserByColour.values():
            uniqueSolid = uniqueSolid.cut(fuser.getResult())

        return self.fuse(colour, uniqueSolid)

    def common(self, solid: Part.Solid) -> 'MultiColourFuser':
        for fuser in self.fuserByColour.values():
            fuser.common(solid)

        return self

    def translate(self, vector: Vector) -> 'MultiColourFuser':
        for fuser in self.fuserByColour.values():
            fuser.translate(vector)

        return self

    def getResult(self):
        return fuseAll(fuser.getResult() for fuser in self.fuserByColour.values())

    def show(self, transparency: int = 100):
        for (color, fuser) in self.fuserByColour.items():
            feature = Part.show(fuser.getResult(), color.getName())
            feature.ViewObject.ShapeColor = color.decode()
            feature.ViewObject.Transparency = transparency
