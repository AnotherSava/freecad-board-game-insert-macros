from math import floor

import Part

from Inserts.common.fuser import Fuser
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
    def __init__(self):
        self.fuserByColour = {}
    
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
    
    def show(self):
        for (color, fuser) in self.fuserByColour.items():
            feature = Part.show(fuser.getResult(), color.getName())
            feature.ViewObject.ShapeColor = color.decode()
