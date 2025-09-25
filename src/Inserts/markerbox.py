import Draft
import Part
from FreeCAD import Vector, Document

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.cylinders import MultiCylinderHolder, CylinderObjectSet, DistinctCylinderHolder
from Inserts.common.fuser import Fuser, fuse, fuseAll
from Inserts.common.labels import Labels
from Inserts.common.magnets import createCornerLocations, createMagnetHolders, createMagnetHoles, MagnetDetails
from Inserts.common.meshlid import MeshLidDimensions, MeshLid
from Inserts.common.primitives import createTaperedBox
from Inserts.common.smartbox import SmartBox
from dataclasses import dataclass


@dataclass
class Dimensions:
    lid: MeshLidDimensions
    length: float
    width: float
    height: float
    ligHeightDelta: float
    floorHeight: float
    padding: float
    delta: float
    magnetDiameter: float
    magnetHeightBox: float
    magnetCountBox: int
    magnetCountLid: int

    stations: CylinderObjectSet
    markers: CylinderObjectSet
    fontHeight: float
    numberFontSize: float
    numberFont: str

    def __post_init__(self):
        self.lid.length = self.length
        self.lid.width = self.width
        self.lid.innerSpaceHeight = self.getLidInnerHeight()
        self.lid.delta = self.delta
        self.lid.magnetDiameter = self.magnetDiameter

    def getLidInnerHeight(self):
        return self.floorHeight + self.getMaxObjectsHeight() - self.height + self.ligHeightDelta

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

    def alignHeight(self, height):
        return self.floorHeight + self.getMaxObjectsHeight() - height

    def getStationPosZ(self):
        return self.alignHeight(self.stations.height)
    
    def getMarkerPosZ(self):
        return self.alignHeight(self.markers.height)


# Holder for the following items: minor company stations and stock markers, company charters (as a lid)
class MarkerBox:
    def __init__(self, dimensions: Dimensions, document: Document):
        self.dimensions = dimensions
        self.labels = Labels(document, dimensions.numberFont, dimensions.numberFontSize)

    def createBox(self) -> MultiColourFuser:
        box = SmartBox(self.dimensions.length, self.dimensions.width, self.dimensions.height)

        labels, markersAndStationsRecess = self.createMarkersAndStations()
        magnetLocations = self.createMagnetLocations(self.dimensions.magnetCountBox, box.zTo)
        magnetHoles = createMagnetHoles(self.dimensions.magnetDiameter, self.dimensions.magnetHeightBox, True, magnetLocations)
        fuser = MultiColourFuser(Colour.WHITE, labels)
        fuser.fuse(Colour.BASE, box).cut(markersAndStationsRecess, magnetHoles)

        return fuser

    def createLid(self) -> MultiColourFuser:
        lid = MeshLid(self.dimensions.lid)

        magnetDetails = self.createMagnetLocations(self.dimensions.magnetCountLid, lid.z)

        return lid.createLid(magnetDetails)

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

    def createMagnetLocations(self, count: int, z: float) -> list[MagnetDetails]:
        locations = createCornerLocations(self.dimensions.length, self.dimensions.width, z, self.dimensions.magnetDiameter, self.dimensions.delta, count)

        for i in range(4):
            locations.append(MagnetDetails(Vector(self.dimensions.length / 4 * (i + 0.5), self.dimensions.width / 2, z), count))

        return locations

    def createNumbers(self, numberFrom: int, numberTo: int, width: float):
        return fuseAll(self.createSingleNumber(number, numberFrom, width) for number in range(numberFrom, numberTo + 1))

    def createSingleNumber(self, number: int, numberFrom: int, width: float):
        solid = self.labels.createText(str(number), self.dimensions.markers.diameter, width, self.dimensions.fontHeight)
        return solid.translate(Vector(self.dimensions.markers.diameter * (number - numberFrom)))
