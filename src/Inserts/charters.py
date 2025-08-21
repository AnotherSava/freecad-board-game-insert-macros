import Part
import Draft
from FreeCAD import Vector, Document

from Inserts.common.cylinders import MultiCylinderHolder, CylinderObjectSet, DistinctCylinderHolder
from Inserts.common.fuser import Fuser, fuseAll
from Inserts.lidbox import SlidingLidBox, LidBoxDimensions
from dataclasses import dataclass


@dataclass
class Dimensions(LidBoxDimensions):
    stations: CylinderObjectSet
    markers: CylinderObjectSet
    cylinderDistanceY: float
    fontHeight: float
    numberSpace: float
    numberFontSize: float
    numberFont: str

    def getMaxObjectsHeight(self):
        return max(self.stations.height, self.markers.height)

    def getMinObjectsVisibleHeight(self):
        return min(self.stations.getVisibleHeight(), self.markers.getVisibleHeight())

# Holder for the following items: minor company stations and stock markers, company charters (as a lid)
class CharterBox:
    def __init__(self, dimensions: Dimensions, document: Document):
        self.dimensions = dimensions
        self.document = document

    def createBox(self):
        slidingLidBox = SlidingLidBox(self.dimensions)
        hollowBox = slidingLidBox.createBox()

        fusedRecesses = self.createRecess()
        hollowBox = hollowBox.cut(fusedRecesses)

        feature = Part.show(hollowBox, "box")
        feature.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
        feature.ViewObject.Transparency = 50

    def alignWidth(self, width: float):
        emptyWidth = self.dimensions.getInnerWidth() - width
        return self.dimensions.wallThickness + emptyWidth / 2

    def alignHeight(self, height):
        return self.dimensions.floorHeight + self.dimensions.getMaxObjectsHeight() - height

    def createRecess(self):
        privateRailways = MultiCylinderHolder(self.dimensions.stations.diameter, 3, False)
        privateRailwayStations = privateRailways.create(self.dimensions.stations.height)

        longerMarkerRow = MultiCylinderHolder(self.dimensions.markers.diameter, 11)
        longerMarkers = longerMarkerRow.create(self.dimensions.markers.height)
        longerRowWidth = longerMarkerRow.getTotalWidth()

        shorterMarkerRow = MultiCylinderHolder(self.dimensions.markers.diameter, 10)
        shorterMarkers = shorterMarkerRow.create(self.dimensions.markers.height)
        shorterRowWidth = shorterMarkerRow.getTotalWidth()

        shorterStationRow = DistinctCylinderHolder(self.dimensions.stations.diameter, 10, shorterRowWidth)
        shorterStations = shorterStationRow.create(self.dimensions.stations.height)

        longerStationRow = DistinctCylinderHolder(self.dimensions.stations.diameter, 11, longerRowWidth)
        longerStations = longerStationRow.create(self.dimensions.stations.height)

        privateRailwaysLength = privateRailways.getTotalLength()

        privateRailwaysTopY = max(privateRailwaysLength + self.dimensions.cylinderDistanceY,
                                  self.dimensions.markers.diameter + self.dimensions.stations.diameter + self.dimensions.cylinderDistanceY + self.dimensions.numberSpace)

        posY = privateRailwaysTopY + self.dimensions.cylinderDistanceY
        longerRowPosX = self.alignWidth(longerRowWidth)
        longerMarkers.translate(Vector(longerRowPosX, posY, self.alignHeight(self.dimensions.markers.height)))

        posY = privateRailwaysTopY + self.dimensions.cylinderDistanceY * 2 + self.dimensions.markers.diameter
        longerStations.translate(Vector(longerRowPosX, posY, self.alignHeight(self.dimensions.stations.height)))

        privateRailwayStations.translate(Vector(longerRowPosX, privateRailwaysTopY - privateRailwaysLength, self.alignHeight(self.dimensions.stations.height)))

        posY = privateRailwaysTopY - self.dimensions.markers.diameter
        shorterRowPositionX = longerRowPosX + longerRowWidth - shorterRowWidth
        shorterMarkers.translate(Vector(shorterRowPositionX, posY, self.alignHeight(self.dimensions.markers.height)))

        posY = privateRailwaysTopY - self.dimensions.cylinderDistanceY - self.dimensions.markers.diameter - self.dimensions.stations.diameter
        shorterStations.translate(Vector(shorterRowPositionX, posY, self.alignHeight(self.dimensions.stations.height)))

        numbersShort = self.createNumbers(1, 10, self.dimensions.markers.diameter)
        numbersShort.translate(Vector(shorterRowPositionX, 0, self.dimensions.getRecessDepth()))

        numbersLong = self.createNumbers(11, 21, self.dimensions.markers.diameter)
        numbersLong.translate(Vector(longerRowPosX,
                                     privateRailwaysTopY + self.dimensions.cylinderDistanceY * 2 + self.dimensions.markers.diameter + self.dimensions.stations.diameter,
                                     self.dimensions.getRecessDepth()))

        aSolid = self.createSymbol("A", self.dimensions.stations.diameter)
        aSolid.translate(Vector(longerRowPosX - self.dimensions.numberSpace, privateRailwaysTopY - self.dimensions.stations.diameter, self.dimensions.getRecessDepth()))
        bSolid = self.createSymbol("B", self.dimensions.stations.diameter)
        bSolid.translate(Vector(longerRowPosX - self.dimensions.numberSpace, privateRailwaysTopY - self.dimensions.stations.diameter * 2, self.dimensions.getRecessDepth()))
        cSolid = self.createSymbol("C", self.dimensions.stations.diameter)
        cSolid.translate(Vector(longerRowPosX - self.dimensions.numberSpace, privateRailwaysTopY - self.dimensions.stations.diameter * 3, self.dimensions.getRecessDepth()))

        return fuseAll(shorterMarkers, shorterStations, longerStations, longerMarkers, privateRailwayStations, numbersShort, numbersLong, aSolid, bSolid, cSolid)

    def createNumbers(self, numberFrom: int, numberTo: int, distance: float):
        fuser = Fuser()

        for number in range(numberFrom, numberTo + 1):
            solid = self.createSymbol(str(number), distance)
            solid.translate(Vector(distance * (number - numberFrom)))
            fuser.fuse(solid)

        return fuser.getResult()

    def createSymbol(self, symbol: str, distance: float) -> Part.Solid:
        string = Draft.makeShapeString(String=symbol, FontFile=self.dimensions.numberFont, Size=self.dimensions.numberFontSize)

        width = string.Shape.BoundBox.XLength
        height = string.Shape.BoundBox.YLength

        solid = string.Shape.extrude(Vector(0, 0, self.dimensions.fontHeight))

        posX = (distance - width) / 2
        posY = (self.dimensions.numberSpace - height) / 2
        solid.translate(Vector(posX, posY))
        self.document.removeObject(string.Name)

        return solid
