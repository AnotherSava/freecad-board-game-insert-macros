from math import radians, sin

import Part
import Draft
from FreeCAD import Vector, Document

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.cylinders import MultiCylinderHolder, CylinderObjectSet, DistinctCylinderHolder
from Inserts.common.fuser import Fuser, fuse, fuseAll
from Inserts.common.geometry import alignWithin
from Inserts.common.pencil import Pencil
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
    playerCubeSpaceWidth: float
    timberCubeSpaceWidth: float
    playerCubeSpaceDistanceSides: float
    playerCubeSpaceLength: float
    cubeSpaceAngle: float
    cubeSpaceDepth: float

    def alignWidth(self, width: float):
        emptyWidth = self.getInnerWidth() - width
        return self.wallThickness + emptyWidth / 2

    def alignHeight(self, height):
        return self.floorHeight + self.getMaxObjectsHeight() - height
    
    def getMaxObjectsHeight(self):
        return max(self.stations.height, self.markers.height)

    def getMinObjectsVisibleHeight(self):
        return min(self.stations.getVisibleHeight(), self.markers.getVisibleHeight())

    def getPrivateRailwaysLength(self):
        return self.stations.diameter * 3

    def getPrivateRailwaysTopY(self):
        return max(
            self.getPrivateRailwaysLength() + self.cylinderDistanceY,
            self.markers.diameter + self.stations.diameter + self.cylinderDistanceY + self.numberSpace
        )

    def getLongerRowWidth(self):
        return self.markers.diameter * 11

    def getShorterRowWidth(self):
        return self.markers.diameter * 10
    
    def getLongerRowPosX(self):
        return self.alignWidth(self.getLongerRowWidth())

    def getShorterRowPositionX(self):
        return self.getLongerRowPosX() + self.getLongerRowWidth() - self.getShorterRowWidth()

    def getStationPosZ(self):
        return self.alignHeight(self.stations.height)
    
    def getMarkerPosZ(self):
        return self.alignHeight(self.markers.height)
        
    def getPlayerCubeHolderLength(self):
        return self.playerCubeSpaceLength + self.cubeSpaceDepth / sin(radians(self.cubeSpaceAngle))

    def getCubeAreaDistance(self):
        return (self.getInnerWidth() - self.playerCubeSpaceWidth * 7 - self.timberCubeSpaceWidth - self.stations.diameter - self.markers.diameter - self.playerCubeSpaceDistanceSides * 2) / 9


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

        # printBox = Part.makeBox(self.dimensions.getInnerWidth() - self.dimensions.playerCubeSpaceWidth, self.dimensions.getPlayerCubeHolderLength() + 3,
        #                    self.dimensions.getBoxHeight())
        # printBox.translate(Vector(self.dimensions.wallThickness + self.dimensions.playerCubeSpaceWidth / 2, self.dimensions.getBoxLength() - self.dimensions.getPlayerCubeHolderLength() - 2))

        # feature = Part.show(printBox, "box")
        # feature.ViewObject.ShapeColor = (0.2, 0.8, 0.8)
        # feature.ViewObject.Transparency = 50

        # feature = Part.show(hollowBox, "box")

        # return MultiColourFuser(Colour.BLACK, hollowBox.common(printBox))
        return MultiColourFuser(Colour.BLACK, hollowBox)

    def alignWidth(self, width: float):
        return alignWithin(width, self.dimensions.wallThickness, self.dimensions.getInnerWidth() + self.dimensions.wallThickness)

    def alignHeight(self, height):
        return self.dimensions.floorHeight + self.dimensions.getMaxObjectsHeight() - height

    def createMarkersAndStations(self) -> Part.Solid:
        privateRailways = MultiCylinderHolder(self.dimensions.stations.diameter, 3, False)
        privateRailwayStations = privateRailways.create(self.dimensions.stations.height)

        longerMarkerRow = MultiCylinderHolder(self.dimensions.markers.diameter, 11)
        longerMarkers = longerMarkerRow.create(self.dimensions.markers.height)
        
        shorterMarkerRow = MultiCylinderHolder(self.dimensions.markers.diameter, 10)
        shorterMarkers = shorterMarkerRow.create(self.dimensions.markers.height)
        
        shorterStationRow = DistinctCylinderHolder(self.dimensions.stations.diameter, 10, self.dimensions.getShorterRowWidth())
        shorterStations = shorterStationRow.create(self.dimensions.stations.height)

        longerStationRow = DistinctCylinderHolder(self.dimensions.stations.diameter, 11, self.dimensions.getLongerRowWidth())
        longerStations = longerStationRow.create(self.dimensions.stations.height)

        posY = self.dimensions.getPrivateRailwaysTopY() + self.dimensions.cylinderDistanceY
        longerMarkers.translate(Vector(self.dimensions.getLongerRowPosX(), posY, self.dimensions.getMarkerPosZ()))

        posY = self.dimensions.getPrivateRailwaysTopY() + self.dimensions.cylinderDistanceY * 2 + self.dimensions.markers.diameter
        longerStations.translate(Vector(self.dimensions.getLongerRowPosX(), posY, self.dimensions.getStationPosZ()))

        privateRailwayStations.translate(
            Vector(self.dimensions.getLongerRowPosX(), self.dimensions.getPrivateRailwaysTopY() - self.dimensions.getPrivateRailwaysLength(),
                   self.dimensions.getStationPosZ()))

        posY = self.dimensions.getPrivateRailwaysTopY() - self.dimensions.markers.diameter
        shorterMarkers.translate(Vector(self.dimensions.getShorterRowPositionX(), posY, self.dimensions.getMarkerPosZ()))

        posY = self.dimensions.getPrivateRailwaysTopY() - self.dimensions.cylinderDistanceY - self.dimensions.markers.diameter - self.dimensions.stations.diameter
        shorterStations.translate(Vector(self.dimensions.getShorterRowPositionX(), posY, self.dimensions.getStationPosZ()))

        return fuse(shorterMarkers, shorterStations, longerStations, longerMarkers, privateRailwayStations)

    def createLabels(self) -> Part.Solid:
        numbersShort = self.createNumbers(1, 10, self.dimensions.markers.diameter)
        numbersShort.translate(Vector(self.dimensions.getShorterRowPositionX(), 0, self.dimensions.getRecessDepth()))

        numbersLong = self.createNumbers(11, 21, self.dimensions.markers.diameter)
        posY = self.dimensions.getPrivateRailwaysTopY() + self.dimensions.cylinderDistanceY * 2 + self.dimensions.markers.diameter + self.dimensions.stations.diameter
        numbersLong.translate(Vector(self.dimensions.getLongerRowPosX(), posY, self.dimensions.getRecessDepth()))

        fuser = Fuser(numbersShort, numbersLong)

        for index, letter in enumerate(["A", "B", "C"]):
            solid = self.createText(letter, self.dimensions.stations.diameter)
            solid.translate(Vector(self.dimensions.getLongerRowPosX() - self.dimensions.numberSpace,
                                   self.dimensions.getPrivateRailwaysTopY() - self.dimensions.stations.diameter * (1 + index),
                                   self.dimensions.getRecessDepth()))
            fuser.fuse(solid)

        return fuser.getResult()

    def createCubeSpace(self, width: float) -> Part.Solid:
        pencil = Pencil()
        pencil.right(self.dimensions.playerCubeSpaceLength)
        pencil.draw(self.dimensions.playerCubeSpaceLength, self.dimensions.cubeSpaceAngle - 90)
        pencil.up(self.dimensions.playerCubeSpaceWidth)
        pencil.draw(self.dimensions.playerCubeSpaceLength, 90 + self.dimensions.cubeSpaceAngle)
        pencil.left(self.dimensions.playerCubeSpaceLength)
        return pencil.extrudeX(width)

    def createCubesAndTokensArea(self) -> Part.Solid:
        fuser = Fuser()
        posY = self.dimensions.getBoxLength() - self.dimensions.getPlayerCubeHolderLength()
        posZ = self.dimensions.getRecessDepth() - self.dimensions.cubeSpaceDepth
        playerCubesPositionX = self.dimensions.playerCubeSpaceDistanceSides + self.dimensions.wallThickness
        for i in range(7):
            playerCubes = self.createCubeSpace(self.dimensions.playerCubeSpaceWidth)
            playerCubes.translate(Vector(playerCubesPositionX, posY, posZ))
            fuser.fuse(playerCubes)
            playerCubesPositionX += self.dimensions.playerCubeSpaceWidth + self.dimensions.getCubeAreaDistance()

        timberCubes = self.createCubeSpace(self.dimensions.timberCubeSpaceWidth)
        timberCubesPositionX = self.dimensions.getBoxWidth() - self.dimensions.timberCubeSpaceWidth - self.dimensions.wallThickness - self.dimensions.playerCubeSpaceDistanceSides
        timberCubes.translate(Vector(timberCubesPositionX, posY, posZ))
        fuser.fuse(timberCubes)

        cityTokenHolder = MultiCylinderHolder(self.dimensions.stations.diameter, 4, False)
        cityTokens = cityTokenHolder.create(self.dimensions.stations.height)
        cityTokens.translate(Vector(playerCubesPositionX, posY, self.dimensions.getStationPosZ()))
        fuser.fuse(cityTokens)

        roundMarkerHolder = MultiCylinderHolder(self.dimensions.markers.diameter, 1)
        roundMarker = roundMarkerHolder.create(self.dimensions.markers.height)
        roundMarkerPosX = playerCubesPositionX + self.dimensions.stations.diameter + self.dimensions.getCubeAreaDistance()
        roundMarkerPosY = posY + self.dimensions.stations.diameter * 4 - self.dimensions.markers.diameter
        roundMarker.translate(Vector(roundMarkerPosX, roundMarkerPosY, self.dimensions.getMarkerPosZ()))
        fuser.fuse(roundMarker)

        privateTokenHolder = MultiCylinderHolder(self.dimensions.stations.diameter, 2, False)
        privateTokens = privateTokenHolder.create(self.dimensions.stations.height)
        privateTokensPosX = roundMarkerPosX + (self.dimensions.markers.diameter - self.dimensions.stations.diameter) / 2
        privateTokens.translate(Vector(privateTokensPosX, posY, self.dimensions.getStationPosZ()))
        fuser.fuse(privateTokens)

        return fuser.getResult()

    def createRecess(self):
        markersAndStations = self.createMarkersAndStations()
        # labels = self.createLabels()
        cubeSpaces = self.createCubesAndTokensArea()

        # feature = Part.show(cubeSpaces, "cubeSpaces")
        # feature.ViewObject.ShapeColor = (0.2, 0.8, 0.8)
        # feature.ViewObject.Transparency = 50

        return fuse(markersAndStations, cubeSpaces)
        # return fuse(markersAndStations, labels, cubeSpaces)

    def createNumbers(self, numberFrom: int, numberTo: int, distance: float):
        return fuseAll(self.createSingleNumber(distance, number, numberFrom) for number in range(numberFrom, numberTo + 1))

    def createSingleNumber(self, distance, number, numberFrom):
        solid = self.createText(str(number), distance)
        return solid.translate(Vector(distance * (number - numberFrom)))

    # text is aligned in the middle of a square width a side equals space
    def createText(self, text: str, space: float) -> Part.Solid:
        string = Draft.makeShapeString(String=text, FontFile=self.dimensions.numberFont, Size=self.dimensions.numberFontSize)

        solid = string.Shape.extrude(Vector(0, 0, self.dimensions.fontHeight))
        solid.translate(Vector((space - string.Shape.BoundBox.XLength) / 2, (self.dimensions.numberSpace - string.Shape.BoundBox.YLength) / 2))

        self.document.removeObject(string.Name)

        return solid
