import Part
from FreeCAD import Vector

from Inserts.common.pencil import Pencil


# Box with a sliding lid
class SlidingLidBox:
    def __init__(self, dimensions):
        self.dimensions = dimensions

    def createBox(self) -> Part.Solid:
        outerBox = Part.makeBox(self.dimensions.getBoxWidth(), self.dimensions.getBoxLength(), self.dimensions.getBoxHeight())

        # Create inner cavity
        innerBox = Part.makeBox(self.dimensions.getInnerWidth(), self.dimensions.getBoxLength(), self.dimensions.getInnerHeight())
        innerBox.translate(Vector(self.dimensions.wallThickness, 0, self.dimensions.getBoxHeight() - self.dimensions.getInnerHeight()))

        # Cut inner from outer to create hollow box
        hollowBox = outerBox.cut(innerBox)

        lid = self.createLid()
        lid = lid.translate(Vector(0, 0, self.dimensions.getBoxHeight() - self.dimensions.lidHeight - self.dimensions.aboveLidHeight))

        return hollowBox.cut(lid)

    def createLid(self):
        return self.createBottomLid().fuse(self.createTopLid())

    def createBottomLid(self):
        pencil = Pencil()
        pencil.arc(self.dimensions.lidWidthDelta, 0, 90)
        pencil.jump(Vector((self.dimensions.getBoxWidth() - self.dimensions.lidWidthBack) / 2, self.dimensions.lidLength, 0))
        pencil.right(self.dimensions.lidWidthBack)
        pencil.jump(Vector(self.dimensions.getBoxWidth() - self.dimensions.lidWidthDelta, self.dimensions.lidWidthDelta))
        pencil.arc(self.dimensions.lidWidthDelta, -90, 90)
        return pencil.extrude(self.dimensions.lidHeight)

    def createTopLid(self):
        pencil = Pencil(Vector(0, 0, self.dimensions.lidHeight))
        pencil.up(self.dimensions.aboveLidLength)
        pencil.arc(self.dimensions.wallThickness, 0, 90)
        pencil.right(self.dimensions.getInnerWidth())
        pencil.arc(self.dimensions.wallThickness, -90, 90)
        pencil.down(self.dimensions.aboveLidLength)
        return pencil.extrude(self.dimensions.aboveLidHeight)
