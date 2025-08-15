import math

import Part
from FreeCAD import Vector

from Inserts.common.cylinders import MultiCylinderHolder
from Inserts.common.pencil import Pencil
from dataclasses import dataclass

@dataclass
class CylinderObjectSet:
    name: str
    diameter: float
    height: float
    count: float

    def getRecessDepth(self):
        return self.height * 0.4

    def getVisibleHeight(self):
        return self.height - self.getRecessDepth()

@dataclass
class Dimensions:
    cylinderObjectSets: list[CylinderObjectSet]
    lidLength: float
    lidWidthFront: float
    lidWidthBack: float
    lidHeight: float
    lidGap: float

    wallThickness: float
    floorHeight: float
    lidWidthDelta: float
    lidLengthDelta: float
    aboveLidHeight: float
    aboveLidLength: float

    def getBoxWidth(self):
        return self.lidWidthFront + 2 * self.lidWidthDelta

    def getInnerWidth(self):
        return self.getBoxWidth() - 2 * self.wallThickness

    def getBoxLength(self):
        return self.lidLength + self.lidLengthDelta

    def getMaxObjectsHeight(self):
        return max(objectSet.height for objectSet in self.cylinderObjectSets)

    def getMinObjectsVisibleHeight(self):
        return min(objectSet.getVisibleHeight() for objectSet in self.cylinderObjectSets)

    def getRecessDepth(self):
        return self.getMaxObjectsHeight() - self.getMinObjectsVisibleHeight()

    def getInnerHeight(self):
        return self.aboveLidHeight + self.lidHeight + self.lidGap + self.getMinObjectsVisibleHeight()

    def getBoxHeight(self):
        return self.floorHeight + self.getRecessDepth() + self.getInnerHeight()


# Holder for a public company: shares (except for concession) and markers
# Shares: 41 x 63 mm
# implement CompanyBox class so that createBox creates a FreeCAD box object, empty inside, with sliding lid (size of cards in Dimensions), with two recesses: one for 5 stations, another for 2 markers (see Dimensions). Recess depth should be 1/3 of the item height. Top part of stations and markers should be on the same height just under the lid
class CompanyBox:
    def __init__(self, dimensions: Dimensions):
        self.dimensions = dimensions

    def createBox(self):
        outerBox = Part.makeBox(self.dimensions.getBoxWidth(), self.dimensions.getBoxLength(), self.dimensions.getBoxHeight())

        # Create inner cavity
        innerBox = Part.makeBox(self.dimensions.getInnerWidth(), self.dimensions.getBoxLength(), self.dimensions.getInnerHeight())
        innerBox.translate(Vector(self.dimensions.wallThickness, 0, self.dimensions.getRecessDepth() + self.dimensions.floorHeight))

        # Cut inner from outer to create hollow box
        hollowBox = outerBox.cut(innerBox)

        fusedRecesses = self.createRecess()

        lid = self.createLid()
        lid = lid.translate(Vector(0, 0, self.dimensions.getBoxHeight() - self.dimensions.lidHeight - self.dimensions.aboveLidHeight))

        boxWithRecesses = hollowBox.cut(fusedRecesses).cut(lid)

        feature = Part.show(boxWithRecesses, "box")
        feature.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
        feature.ViewObject.Transparency = 50

        # feature = Part.show(lid, "lid")
        # feature.ViewObject.ShapeColor = (0.2, 0.8, 0.2)
        # feature.ViewObject.Transparency = 80

        # feature = Part.show(fusedRecesses, "objects")
        # feature.ViewObject.ShapeColor = (0.2, 0.2, 0.8)
        # feature.ViewObject.Transparency = 60

        # feature = Part.show(innerBox, "inner")
        # feature.ViewObject.ShapeColor = (0.8, 0.8, 0.8)
        # feature.ViewObject.Transparency = 75

    def createRecess(self):
        emptyLength = self.dimensions.getBoxLength() - sum(objectSet.diameter for objectSet in self.dimensions.cylinderObjectSets)
        lengthInterval = emptyLength / (len(self.dimensions.cylinderObjectSets) + 1)
        shiftY = 0
        fusedRecesses = None
        for setIndex, objectSet in enumerate(self.dimensions.cylinderObjectSets):
            multiCylinderHolder = MultiCylinderHolder(objectSet.diameter, objectSet.count)
            recess = multiCylinderHolder.create(objectSet.height)

            emptyWidth = self.dimensions.getInnerWidth() - multiCylinderHolder.getTotalWidth()
            shiftY += lengthInterval

            shiftX = self.dimensions.wallThickness + emptyWidth / 2
            shiftZ = self.dimensions.floorHeight + self.dimensions.getMaxObjectsHeight() - objectSet.height
            recess.translate(Vector(shiftX, shiftY, shiftZ))
            fusedRecesses = recess if fusedRecesses is None else fusedRecesses.fuse(recess)

            shiftY += objectSet.diameter

        return fusedRecesses

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
