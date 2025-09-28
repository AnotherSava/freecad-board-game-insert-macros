from dataclasses import dataclass

import Draft
from FreeCAD import Vector, Document

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.cylinders import MultiCylinderHolder, CylinderObjectSet, DistinctCylinderHolder
from Inserts.common.fuser import Fuser, fuse
from Inserts.common.labels import Labels
from Inserts.common.magnets import createMagnetHoles, MagnetDetails, MagnetDimensions
from Inserts.common.meshlid import MeshLidDimensions, MeshLid
from Inserts.common.smartbox import SmartBox


@dataclass
class Dimensions:
    lid: MeshLidDimensions
    magnets: MagnetDimensions
    length: float
    width: float
    height: float
    lidHeightDelta: float
    floorHeight: float
    padding: float

    stations: CylinderObjectSet
    markers: CylinderObjectSet

    fontHeight: float
    numberFontSize: float
    numberFont: str

    def __post_init__(self):
        self.lid.length = self.length
        self.lid.width = self.width
        self.lid.innerSpaceHeight = self.getLidInnerHeight()

    def getLidInnerHeight(self):
        return self.floorHeight + self.getMaxObjectsHeight() - self.height + self.lidHeightDelta

    def getMaxObjectsHeight(self):
        return max(self.stations.height, self.markers.height)

    def getLongerRowWidth(self):
        return self.markers.diameter * 11

    def getShorterRowWidth(self):
        return self.markers.diameter * 10
    
    def getLongerRowPosX(self):
        return self.length - self.getLongerRowWidth() - self.padding

    def getShorterRowPositionX(self):
        return self.getLongerRowPosX() + self.getLongerRowWidth() - self.getShorterRowWidth()

    def getStationPosZ(self):
        return self.floorHeight + self.getMaxObjectsHeight() - self.stations.height
    
    def getMarkerPosZ(self):
        return self.floorHeight + self.getMaxObjectsHeight() - self.markers.height


# Holder for the following items: minor company stations and stock markers, company charters (as a lid)
class MarkerBox(SmartBox):
    def __init__(self, dimensions: Dimensions, document: Document):
        super().__init__(dimensions.length, dimensions.width, dimensions.height)

        self.dimensions = dimensions
        self.labels = Labels(document, dimensions.numberFont, dimensions.numberFontSize)

    def createBox(self) -> MultiColourFuser:
        box = SmartBox(self.dimensions.length, self.dimensions.width, self.dimensions.height)

        labels, markersAndStationsRecess = self.createMarkersAndStations()
        magnetHoles = createMagnetHoles(self.dimensions.magnets, True, self.createCustomMagnetDetails()).translate(Vector(0, 0, box.zTo))

        fuser = MultiColourFuser(Colour.WHITE, labels)
        fuser.fuse(Colour.BASE, box).cut(markersAndStationsRecess, magnetHoles)

        return fuser

    def createLid(self) -> MultiColourFuser:
        lid = MeshLid(self.dimensions.lid)

        return lid.createLid(self.createMagnetDetails())

    def createMarkersAndStations(self):
        paddingVerticalCentre = (self.dimensions.width - self.dimensions.padding * 2 - self.dimensions.stations.diameter * 2 - self.dimensions.markers.diameter * 2) * 3 / 10

        stationsShorter = DistinctCylinderHolder(self.dimensions.stations.diameter, 10, self.dimensions.getShorterRowWidth(), self.dimensions.stations.height, True)
        posY = self.dimensions.width - self.dimensions.padding - self.dimensions.stations.diameter
        stationsShorter.translateVector(Vector(self.dimensions.getShorterRowPositionX(), posY, self.dimensions.getStationPosZ()))

        markersShorter = MultiCylinderHolder(self.dimensions.markers.diameter, 10, self.dimensions.markers.height)
        posY = (self.dimensions.width + paddingVerticalCentre) / 2
        markersShorter.translateVector(Vector(self.dimensions.getShorterRowPositionX(), posY, self.dimensions.getMarkerPosZ()))

        stationsLonger = DistinctCylinderHolder(self.dimensions.stations.diameter, 11, self.dimensions.getLongerRowWidth(), self.dimensions.stations.height, True)
        stationsLonger.translateVector(Vector(self.dimensions.getLongerRowPosX(), self.dimensions.padding, self.dimensions.getStationPosZ()))

        markersLonger = MultiCylinderHolder(self.dimensions.markers.diameter, 11, self.dimensions.markers.height)
        posY = (self.dimensions.width - paddingVerticalCentre) / 2 - self.dimensions.markers.diameter
        markersLonger.translateVector(Vector(self.dimensions.getLongerRowPosX(), posY, self.dimensions.getMarkerPosZ()))

        privateRailways = MultiCylinderHolder(self.dimensions.stations.diameter, 3, self.dimensions.stations.height)
        paddingLeft = self.dimensions.padding + (self.dimensions.markers.diameter - self.dimensions.stations.diameter) / 2
        privateRailways.translateVector(Vector(paddingLeft, stationsShorter.y, self.dimensions.getStationPosZ()))

        roundMarker = MultiCylinderHolder(self.dimensions.markers.diameter, 1, self.dimensions.markers.height)
        roundMarker.translate(markersShorter.x - self.dimensions.padding - roundMarker.length, markersShorter.y, self.dimensions.getMarkerPosZ())

        cityTokens = MultiCylinderHolder(self.dimensions.stations.diameter, 4, self.dimensions.stations.height, False)
        cityTokens.translate(paddingLeft, self.dimensions.padding, self.dimensions.getStationPosZ())

        specialTokens = MultiCylinderHolder(self.dimensions.stations.diameter, 2, self.dimensions.stations.height, False)
        specialTokens.translate(paddingLeft, cityTokens.yTo + self.dimensions.padding, self.dimensions.getStationPosZ())

        numbersShorter = self.createNumbers(1, 10, privateRailways.y - specialTokens.yTo)
        numbersShorter.translate(Vector(self.dimensions.getShorterRowPositionX(), specialTokens.yTo, self.dimensions.height))

        numbersLonger = self.createNumbers(11, 21, privateRailways.y - specialTokens.yTo)
        numbersLonger.translate(Vector(self.dimensions.getLongerRowPosX(), stationsLonger.yTo, self.dimensions.height))

        labels = Fuser(numbersShorter, numbersLonger)
        for index, letter in enumerate(["A", "B", "C"]):
            solid = self.labels.createText(letter, self.dimensions.stations.diameter, privateRailways.y - specialTokens.yTo, self.dimensions.fontHeight)
            solid.translate(Vector(privateRailways.x + index * privateRailways.diameter, specialTokens.yTo, self.dimensions.height))
            labels.fuse(solid)

        return labels, fuse(markersShorter, stationsShorter, stationsLonger, markersLonger, privateRailways, cityTokens, roundMarker, specialTokens)

    def createCustomMagnetDetails(self) -> list[MagnetDetails]:
        cornerMagnets = self.createCornerMagnetDetails(self.dimensions.magnets.getWiderBaseRadius())
        middleMagnets = [MagnetDetails(Vector(self.dimensions.length / 4 * (i + 0.5), self.dimensions.width / 2)) for i in range(4)]

        return cornerMagnets + middleMagnets

    def createNumbers(self, numberFrom: int, numberTo: int, width: float):
        return fuse(self.createSingleNumber(number, numberFrom, width) for number in range(numberFrom, numberTo + 1))

    def createSingleNumber(self, number: int, numberFrom: int, width: float):
        solid = self.labels.createText(str(number), self.dimensions.markers.diameter, width, self.dimensions.fontHeight)
        return solid.translate(Vector(self.dimensions.markers.diameter * (number - numberFrom)))
