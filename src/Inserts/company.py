import Part
from FreeCAD import Vector

from Inserts.common.cylinders import MultiCylinderHolder, CylinderObjectSet
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

    def createBox(self):
        slidingLidBox = SlidingLidBox(self.dimensions)
        hollowBox = slidingLidBox.createBox()

        fusedRecesses = self.createRecess()

        boxWithRecesses = hollowBox.cut(fusedRecesses)

        feature = Part.show(boxWithRecesses, "box")
        feature.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
        feature.ViewObject.Transparency = 50

        # feature = Part.show(fusedRecesses, "objects")
        # feature.ViewObject.ShapeColor = (0.2, 0.2, 0.8)
        # feature.ViewObject.Transparency = 60

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
