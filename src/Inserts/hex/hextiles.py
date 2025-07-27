from math import tan, radians

import Part
from FreeCAD import Vector

from Inserts.common.geometry import createRoundedHexTile
from Inserts.hex.configuration import GridConfiguration, GridDimensions, HexPinSide, PinConfiguration, HexTileVertices
from Inserts.hex.pin import PinFactory


class HexBoard:
    def __init__(self, configuration: GridConfiguration, dimensions: GridDimensions):
        self.configuration = configuration
        self.dimensions = dimensions
        self.pinFactory = PinFactory(dimensions)

    def createPinConfiguration(self):
        pinConfiguration = PinConfiguration(self.configuration)

        for column in range(0, self.configuration.columnsTotal):
            shiftY = self.configuration.getBottomPinsRowIndexForColumn(column)

            for row in range(0, self.configuration.getHexCountInColumn(column)):
                bottomPinIndex = shiftY + row * 2
                pinConfiguration.addRays(column, bottomPinIndex, [HexPinSide.TOP, HexPinSide.RIGHT])
                pinConfiguration.addRays(column + 1, bottomPinIndex + 1, [HexPinSide.LEFT, HexPinSide.RIGHT])
                pinConfiguration.addRays(column + 2, bottomPinIndex, [HexPinSide.TOP, HexPinSide.LEFT])

        return pinConfiguration

    def createRectangularFloor(self, pinConfiguration):
        hexSizeY = self.dimensions.getDistanceFromHexCentreToOuterPinAngle() * 2
        floorX = self.dimensions.getHexCentreDistanceX() * (pinConfiguration.sizeX - 1) + self.dimensions.pinWidth
        floorY = hexSizeY + self.dimensions.getHexCentreDistanceY() * (pinConfiguration.sizeY - 2)
        floorPos = Vector(-self.dimensions.pinWidth / 2, -self.dimensions.getHexCentreDistanceY() / 2, -self.dimensions.floorThickness)
        return Part.makeBox(floorX, floorY, self.dimensions.floorThickness, floorPos)

    def createOuterBound(self, pinConfiguration: PinConfiguration):
        fusedFace = None
        for x in range(0, pinConfiguration.sizeX - 2):
            for y in range(0, pinConfiguration.sizeY - 1):
                if pinConfiguration.doesPinExist(x, y) and pinConfiguration.findMissingRay(x, y) in [None, HexPinSide.LEFT, HexPinSide.RIGHT]:
                    roundedVertices = []
                    if y == pinConfiguration.sizeY - 2:
                        roundedVertices.append(HexTileVertices.N)
                        if x <= 1:
                            roundedVertices.append(HexTileVertices.NW)
                        if x >= pinConfiguration.sizeX - 4:
                            roundedVertices.append(HexTileVertices.NE)
                    if y == 0:
                        roundedVertices.append(HexTileVertices.S)
                        if x <= 1:
                            roundedVertices.append(HexTileVertices.SW)
                        if x >= pinConfiguration.sizeX - 4:
                            roundedVertices.append(HexTileVertices.SE)

                    if x == 0:
                        roundedVertices += [HexTileVertices.NW, HexTileVertices.SW]

                    if x == pinConfiguration.sizeX - 3:
                        roundedVertices += [HexTileVertices.NE, HexTileVertices.SE]

                    wire = createRoundedHexTile(self.dimensions.hexWidth + self.dimensions.pinWidth, self.dimensions.pinWidth, roundedVertices)
                    wire.translate(Vector(x * self.dimensions.getHexCentreDistanceX(), y * self.dimensions.getHexCentreDistanceY()))
                    face = Part.Face(wire)
                    fusedFace = face if fusedFace is None else fusedFace.fuse(face)
        y = self.dimensions.pinWidth / 2 * tan(radians(30)) - self.dimensions.hexWidth / 2 * tan(radians(30)) + self.dimensions.getHexSizeY() / 2
        fusedFace.translate(Vector(self.dimensions.pinWidth / 2 + self.dimensions.hexWidth / 2, y, -self.dimensions.floorThickness))

        return fusedFace.extrude(Vector(0, 0, self.dimensions.pinHeight + self.dimensions.floorThickness))

    def createPins(self, pinConfiguration: PinConfiguration):
        pins = None
        for column in range(0, pinConfiguration.sizeX):
            for row in range(0, pinConfiguration.sizeY):
                if not pinConfiguration.doesPinExist(column, row):
                    continue

                skip = pinConfiguration.findMissingRay(column, row)
                pin = self.pinFactory.createPin(column, row, skip)
                pins = pin if not pins else pins.fuse(pin)
        return pins

    def createBoard(self):
        pinConfiguration = self.createPinConfiguration()

        pins = self.createPins(pinConfiguration)

        outerBound = self.createOuterBound(pinConfiguration)
        # floorFeature = Part.show(outerBound, "floor v2")
        # floorFeature.ViewObject.ShapeColor = (0.4, 0.8, 0.4)

        floor = self.createRectangularFloor(pinConfiguration)
        floorFeature = Part.show(floor.common(outerBound), "floor")
        floorFeature.ViewObject.ShapeColor = (0.4, 0.8, 0.4)

        pinsFeature = Part.show(pins.common(outerBound), "pins")
        pinsFeature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)
