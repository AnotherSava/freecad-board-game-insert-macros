import Part
from FreeCAD import Vector

from Inserts.common.pencil import Pencil
from dataclasses import dataclass

@dataclass
class LidDimensions:
    lidLength: float
    lidWidthBack: float
    lidHeight: float
    lidGap: float
    lidWidthDelta: float
    lidLengthDelta: float
    aboveLidHeight: float
    lidWidthMultiplier: float
    aboveLidLengthMultiplier: float
    supportLengthMultiplier: float
    simplify: bool = False
    supportWidth: float = None

    def __post_init__(self):
        self.lidWidthFront = self.lidWidthBack * self.lidWidthMultiplier
        self.aboveLidLength = self.lidLength * self.aboveLidLengthMultiplier + self.lidLengthDelta
        self.supportLength = self.lidLength * self.supportLengthMultiplier

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

        box = outerBox.cut(innerBox).cut(lid)
        if self.dimensions.lid.supportWidth:
            box = box.fuse(self.createLidSupport())

        return box

    def createLidSupport(self) -> Part.Solid:
        supportHeight = self.dimensions.getInnerHeight() - self.dimensions.lid.lidHeight - self.dimensions.lid.aboveLidHeight

        pencil = Pencil(Vector((self.dimensions.getBoxWidth() - self.dimensions.lid.supportWidth) / 2, 0, self.dimensions.floorHeight + self.dimensions.getRecessDepth()))
        pencil.arcWithRadius(supportHeight, -90, -90)
        pencil.right(self.dimensions.lid.supportLength - supportHeight)
        pencil.down(supportHeight)

        return pencil.extrudeX(self.dimensions.lid.supportWidth)

    def createLid(self):
        lid = self.createBottomLid()

        return lid if self.dimensions.lid.simplify else lid.fuse(self.createTopLid()).fuse(self.createTopLidBevel())

    def createBottomLid(self):
        pencil = Pencil()
        pencil.arcWithRadius(self.dimensions.lid.lidWidthDelta, 0, 90)
        pencil.jumpFromStart(Vector((self.dimensions.getBoxWidth() - self.dimensions.lid.lidWidthBack) / 2, self.dimensions.lid.lidLength, 0))
        pencil.right(self.dimensions.lid.lidWidthBack)
        pencil.jumpFromStart(Vector(self.dimensions.getBoxWidth() - self.dimensions.lid.lidWidthDelta, self.dimensions.lid.lidWidthDelta))
        pencil.arcWithRadius(self.dimensions.lid.lidWidthDelta, -90, 90)

        height = self.dimensions.lid.lidHeight
        if self.dimensions.lid.simplify:
            height += self.dimensions.lid.aboveLidHeight

        return pencil.extrude(height)

    def createTopLid(self):
        pencil = Pencil(Vector(0, 0, self.dimensions.lid.lidHeight))
        pencil.up(self.dimensions.lid.aboveLidLength)
        pencil.arcWithRadius(self.dimensions.wallThickness, 0, 90)
        pencil.right(self.dimensions.getInnerWidth())
        pencil.arcWithRadius(self.dimensions.wallThickness, -90, 90)
        pencil.down(self.dimensions.lid.aboveLidLength)
        return pencil.extrude(self.dimensions.lid.aboveLidHeight)

    def createTopLidBevel(self):
        pencil = Pencil(Vector(self.dimensions.lid.lidWidthDelta, 0, self.dimensions.lid.lidHeight))
        pencil.up(self.dimensions.lid.aboveLidHeight)
        pencil.right(self.dimensions.lid.aboveLidLength)
        pencil.arc(Vector(self.dimensions.lid.aboveLidHeight * 3, -self.dimensions.lid.aboveLidHeight), 10)
        solid = pencil.extrudeX(self.dimensions.lid.lidWidthFront)

        return solid
