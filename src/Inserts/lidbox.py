import Part
from FreeCAD import Vector

from Inserts.common.pencil import Pencil
from dataclasses import dataclass

@dataclass
class LidDimensions:
    lidLength: float
    lidWidthBack: float
    lidHeight: float
    lidGap: float = 1
    lidWidthDelta: float = 1.2
    lidLengthDelta: float = 0.8
    aboveLidHeight: float = 1.2
    simplify: bool = False # for prototype prints to avoid support

    lidWidthFront: float = None
    aboveLidLength: float = None

    lidWidthMultiplier: float = 1.02
    aboveLidLengthMultiplier: float = 0.5

    def __post_init__(self):
        self.lidWidthFront = self.lidWidthBack * self.lidWidthMultiplier
        self.aboveLidLength = self.lidLength * self.aboveLidLengthMultiplier

@dataclass
class LidBoxDimensions:
    lid: LidDimensions

    wallThickness: float
    floorHeight: float

    def getBoxWidth(self):
        return self.lid.lidWidthFront + 2 * self.lid.lidWidthDelta

    def getInnerWidth(self):
        return self.getBoxWidth() - 2 * self.wallThickness

    def getBoxLength(self):
        return self.lid.lidLength + self.lid.lidLengthDelta

    def getRecessDepth(self):
        return self.getMaxObjectsHeight() - self.getMinObjectsVisibleHeight()

    def getInnerHeight(self):
        return self.lid.aboveLidHeight + self.lid.lidHeight + self.lid.lidGap + self.getMinObjectsVisibleHeight()

    def getBoxHeight(self):
        return self.floorHeight + self.getRecessDepth() + self.getInnerHeight()

# Box with a sliding lid
class SlidingLidBox:
    def __init__(self, dimensions: LidBoxDimensions):
        self.dimensions = dimensions

    def createBox(self) -> Part.Solid:
        outerBox = Part.makeBox(self.dimensions.getBoxWidth(), self.dimensions.getBoxLength(), self.dimensions.getBoxHeight())

        # Create inner cavity
        innerBox = Part.makeBox(self.dimensions.getInnerWidth(), self.dimensions.getBoxLength(), self.dimensions.getInnerHeight())
        innerBox.translate(Vector(self.dimensions.wallThickness, 0, self.dimensions.getBoxHeight() - self.dimensions.getInnerHeight()))

        lid = self.createLid()
        lid.translate(Vector(0, 0, self.dimensions.getBoxHeight() - self.dimensions.lid.lidHeight - self.dimensions.lid.aboveLidHeight))

        return outerBox.cut(innerBox).cut(lid)

    def createLid(self):
        lid = self.createBottomLid()

        if not self.dimensions.lid.simplify:
            lid = lid.fuse(self.createTopLid())

        return lid

    def createBottomLid(self):
        pencil = Pencil()
        pencil.arc(self.dimensions.lid.lidWidthDelta, 0, 90)
        pencil.jump(Vector((self.dimensions.getBoxWidth() - self.dimensions.lid.lidWidthBack) / 2, self.dimensions.lid.lidLength, 0))
        pencil.right(self.dimensions.lid.lidWidthBack)
        pencil.jump(Vector(self.dimensions.getBoxWidth() - self.dimensions.lid.lidWidthDelta, self.dimensions.lid.lidWidthDelta))
        pencil.arc(self.dimensions.lid.lidWidthDelta, -90, 90)

        height = self.dimensions.lid.lidHeight
        if self.dimensions.lid.simplify:
            height += self.dimensions.lid.aboveLidHeight

        return pencil.extrude(height)

    def createTopLid(self):
        pencil = Pencil(Vector(0, 0, self.dimensions.lid.lidHeight))
        pencil.up(self.dimensions.lid.aboveLidLength)
        pencil.arc(self.dimensions.wallThickness, 0, 90)
        pencil.right(self.dimensions.getInnerWidth())
        pencil.arc(self.dimensions.wallThickness, -90, 90)
        pencil.down(self.dimensions.lid.aboveLidLength)
        return pencil.extrude(self.dimensions.lid.aboveLidHeight)
