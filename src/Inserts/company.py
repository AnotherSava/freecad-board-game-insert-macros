import Part
from FreeCAD import Vector

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.cylinders import MultiCylinderHolder, CylinderObjectSet, DistinctCylinderHolder
from Inserts.common.fuser import Fuser
from Inserts.lidbox import SlidingLidBox, LidBoxDimensions
from dataclasses import dataclass


@dataclass
class Dimensions(LidBoxDimensions):
    cylinderObjectSets: list[CylinderObjectSet]

    def getMaxObjectsHeight(self):
        return max(objectSet.height for objectSet in self.cylinderObjectSets)

    def getMinObjectsVisibleHeight(self):
        return min(objectSet.getVisibleHeight() for objectSet in self.cylinderObjectSets)


# Holder for a public company: shares (except for concession) and markers
# Shares: 41 x 63 mm
# implement CompanyBox class so that createBox creates a FreeCAD box object, empty inside, with sliding lid (size of cards in Dimensions), with two recesses: one for 5 stations, another for 2 markers (see Dimensions). Recess depth should be 1/3 of the item height. Top part of stations and markers should be on the same height just under the lid
class CompanyBox:
    def __init__(self, dimensions: Dimensions):
        self.dimensions = dimensions

    def createBox(self) -> MultiColourFuser:
        slidingLidBox = SlidingLidBox(self.dimensions)
        hollowBox = slidingLidBox.createBox()

        fusedRecesses = self.createRecess()

        boxWithRecesses = hollowBox.cut(fusedRecesses)

        return MultiColourFuser(Colour.BASE, boxWithRecesses)

    def createRecess(self):
        emptyWidth = self.dimensions.getBoxWidth() - sum(objectSet.diameter for objectSet in self.dimensions.cylinderObjectSets)
        widthInterval = emptyWidth / (len(self.dimensions.cylinderObjectSets) + 1)
        shiftY = widthInterval
        fuser = Fuser()
        for setIndex, objectSet in enumerate(self.dimensions.cylinderObjectSets):
            if objectSet.separate:
                multiCylinderHolder = MultiCylinderHolder(objectSet.diameter, objectSet.count, objectSet.height)
                recess = multiCylinderHolder.solid

                emptyLength = self.dimensions.getInnerLength() - multiCylinderHolder.getTotalWidth()

                shiftX = self.dimensions.wallThickness + emptyLength / 2
            else:
                distinctCylinderHolder = DistinctCylinderHolder(objectSet.diameter, objectSet.count, self.dimensions.getInnerLength(), True)
                recess = distinctCylinderHolder.create(objectSet.height)
                shiftX = self.dimensions.wallThickness

            shiftZ = self.dimensions.floorHeight + self.dimensions.getMaxObjectsHeight() - objectSet.height
            recess.translate(Vector(shiftX, shiftY, shiftZ))
            fuser.fuse(recess)

            shiftY += objectSet.diameter + widthInterval

        return fuser.solid
