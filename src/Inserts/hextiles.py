from math import tan, sqrt, cos, sin, radians

import Part
from FreeCAD import Vector

from Inserts.configuration import GridConfiguration, GridDimensions, HexPinSide, PinConfiguration


class HexBoard:
    def __init__(self, configuration: GridConfiguration, dimensions: GridDimensions):
        self.configuration = configuration
        self.dimensions = dimensions

    def createPinWire(self, skip = None):
        a = self.dimensions.pinWidth / 2 * tan(radians(30))
        edges = []
        for side in [HexPinSide.TOP, HexPinSide.RIGHT, HexPinSide.LEFT]: # order is important
            angle = side.value
            wire = self.createPinRayWire(skip == side)
            wire.translate(Vector(0, a, 0))
            wire.rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle)
            edges += list(wire.Edges)

        return Part.Wire(edges)

    def createPinRayWire(self, skip = False):
        x = self.dimensions.pinRadius * cos(radians(45))
        delta = self.dimensions.pinRadius - x

        v1 = Vector(-self.dimensions.pinWidth / 2, 0, 0)

        v2 = Vector(-self.dimensions.pinWidth / 2, self.dimensions.pinLength - self.dimensions.pinRadius, 0)
        v23 = Vector(-self.dimensions.pinWidth / 2 + delta, self.dimensions.pinLength - delta, 0)
        v3 = Vector(-self.dimensions.pinWidth / 2 + self.dimensions.pinRadius, self.dimensions.pinLength, 0)

        v4 = Vector(self.dimensions.pinWidth / 2 - self.dimensions.pinRadius, self.dimensions.pinLength, 0)
        v45 = Vector(self.dimensions.pinWidth / 2 - delta, self.dimensions.pinLength - delta, 0)
        v5 = Vector(self.dimensions.pinWidth / 2, self.dimensions.pinLength - self.dimensions.pinRadius, 0)

        v6 = Vector(self.dimensions.pinWidth / 2, 0, 0)
        v61 = Vector(0, self.dimensions.pinWidth * (2 - sqrt(3)) / 2, 0)

        edges = [Part.Arc(v6, v61, v1).toShape()] if skip else [
            Part.LineSegment(v1, v2).toShape(),
            Part.Arc(v2, v23, v3).toShape(),
            Part.LineSegment(v3, v4).toShape(),
            Part.Arc(v4, v45, v5).toShape(),
            Part.LineSegment(v5, v6).toShape()
        ]

        return Part.Wire(edges)

    def createPin(self, column, row, skip):
        wire = self.createPinWire(skip)
        wire.translate(Vector(column * self.dimensions.getHexCentreDistanceX(), row * self.dimensions.getHexCentreDistanceY()))
        face = Part.Face(wire)
        pin = face.extrude(Vector(0, 0, self.dimensions.pinHeight))  # Extrude to make a solid (height=1mm)
        pinFeature = Part.show(pin, f"pin {column}-{row}")
        pinFeature.ViewObject.ShapeColor = (0.2, 0.6, 0.8)

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
        hexSizeY = 2 * self.dimensions.hexWidth * tan(radians(30))
        floorX = self.dimensions.getHexCentreDistanceX() * (pinConfiguration.sizeX - 1) + self.dimensions.pinWidth
        floorY = hexSizeY + self.dimensions.getHexCentreDistanceY() * (pinConfiguration.sizeY - 2) + self.dimensions.pinWidth / 2 * tan(radians(60)) + self.dimensions.pinWidth * (2 - sqrt(3)) / 2
        floorPos = Vector(-self.dimensions.pinWidth / 2,
                          self.dimensions.pinWidth / 2 * tan(radians(30)) - self.dimensions.hexWidth / 2 * tan(radians(30)),
                          -self.dimensions.floorThickness)
        box = Part.makeBox(floorX, floorY, self.dimensions.floorThickness, floorPos)
        boxFeature = Part.show(box, "box")
        boxFeature.ViewObject.ShapeColor = (0.8, 0.6, 0.2)

    def createRoundedHexFloorTile(self):
        # Align arc shortening distance with one in createPinRayWire
        arcOffset = self.dimensions.pinWidth / 2 / cos(radians(30))

        # Calculate unit vectors for hexagon vertices from its centre
        verticeUnits = [Vector(sin(radians(60 * i)), cos(radians(60 * i)), 0) for i in range(0, 6)]

        # Calculate unit vectors for hexagon edges (normalized directions)
        edgeUnits = [(verticeUnits[(i + 1) % 6] - verticeUnits[i]).normalize() for i in range(0, 6)]

        # Calculate all 6 vertices of the hexagon
        vertices = [self.dimensions.getDistanceFromHexCentreToOuterPinAngle() * verticeUnit for verticeUnit in verticeUnits]

        edges = list()

        # Create shortened edges with arc connections
        for currentVertexIndex in range(0, 6):
            nextVertexIndex = (currentVertexIndex + 1) % 6

            # Shorten the edge by arcOffset at each end
            v1Short = vertices[currentVertexIndex] + edgeUnits[currentVertexIndex] * arcOffset
            v2Short = vertices[nextVertexIndex] - edgeUnits[currentVertexIndex] * arcOffset
            
            # Add the shortened straight edge
            edges.append(Part.LineSegment(v1Short, v2Short).toShape())
            
            # Add arc at the corner connecting this edge to the next
            arcStart = v2Short
            arcEnd = vertices[nextVertexIndex] + edgeUnits[nextVertexIndex] * arcOffset
            arcMidOffset = self.dimensions.pinWidth * (2 - sqrt(3)) / 2
            arcMid = (arcStart + arcEnd) / 2 + verticeUnits[nextVertexIndex] * arcMidOffset

            edges.append(Part.Arc(arcStart, arcMid, arcEnd).toShape())

        return Part.Wire(edges)

    def createHexFloor(self, pinConfiguration: PinConfiguration):
        fusedFace = None
        for x in range(0, pinConfiguration.sizeX - 2):
            for y in range(0, pinConfiguration.sizeY):
                if pinConfiguration.doesPinExist(x, y) and pinConfiguration.findMissingRay(x, y) in [None, HexPinSide.LEFT, HexPinSide.RIGHT]:
                    wire = self.createRoundedHexFloorTile()
                    wire.translate(Vector(x * self.dimensions.getHexCentreDistanceX(), y * self.dimensions.getHexCentreDistanceY()))
                    face = Part.Face(wire)
                    fusedFace = face if fusedFace is None else fusedFace.fuse(face)
        y = self.dimensions.pinWidth / 2 * tan(radians(30)) - self.dimensions.hexWidth / 2 * tan(radians(30)) + self.dimensions.getHexSizeY() / 2
        fusedFace.translate(Vector(self.dimensions.pinWidth / 2 + self.dimensions.hexWidth / 2, y, -self.dimensions.floorThickness))

        floor = fusedFace.extrude(Vector(0, 0, self.dimensions.floorThickness))
        floorFeature = Part.show(floor, "floor v2")
        floorFeature.ViewObject.ShapeColor = (0.4, 0.8, 0.4)

    def createBoard(self):
        pinConfiguration = self.createPinConfiguration()

        for column in range(0, pinConfiguration.sizeX):
            for row in range(0, pinConfiguration.sizeY):
                if not pinConfiguration.doesPinExist(column, row):
                    continue

                skip = pinConfiguration.findMissingRay(column, row)
                self.createPin(column, row, skip)

        self.createHexFloor(pinConfiguration)
        # self.createFloor(pinConfiguration)
