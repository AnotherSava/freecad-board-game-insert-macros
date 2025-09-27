import math

from Inserts.hex.configuration import HexTileVertices
from common.math import advancedRound
from typing import Iterable

import Part
from FreeCAD import Vector

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuse
from Inserts.common.hexagon import Hexagon, HexagonConfiguration
from Inserts.common.hexes import getDistanceY
from Inserts.common.magnets import createMagnetHolders, MagnetDetails
from Inserts.common.pencil import Pencil
from Inserts.common.primitives import createTaperedBox
from Inserts.common.smartbox import SmartBox
from Inserts.common.smartsolid import SmartSolid
from dataclasses import dataclass


@dataclass
class MeshLidDimensions:
    handleRadius: float
    wallThickness: float
    gridThickness: float
    magnetHeight: float
    minimalMeshHeight: float
    beautifyHandle: bool = True
    fillCorners: bool = False
    fillHandleSides: bool = False
    magnetDiameter: float = None
    delta: float = None
    hexCountLength: int = None # how many hexes length fit
    maxGridShortDiagonal: float = None
    length: float = None
    width: float = None
    height: float = None
    innerSpaceHeight: float = None

    def __post_init__(self):
        assert (self.hexCountLength is None) + (self.maxGridShortDiagonal is None) == 1

    def getHexCountLength(self) -> int:
        return self.hexCountLength or math.ceil((self.length - self.wallThickness * 2 + self.gridThickness) / (self.maxGridShortDiagonal + self.gridThickness))

    def getMeshHeight(self):
        return self.height - (self.innerSpaceHeight or 0)

    def getHexShortDiagonal(self):
        return (self.length - self.wallThickness * 2 - self.gridThickness * (self.getHexCountLength() - 1)) / self.getHexCountLength()

    def getDistanceX(self):
        return self.getHexShortDiagonal() + self.gridThickness

class MeshLid(SmartSolid):
    def __init__(self, dimensions: MeshLidDimensions):
        super().__init__(dimensions.length, dimensions.width, dimensions.height)

        self.dimensions = dimensions

        self.internalMesh = SmartBox(self.dimensions.length - self.dimensions.wallThickness * 2, self.dimensions.width - self.dimensions.wallThickness * 2, self.dimensions.getMeshHeight())
        self.internalMesh.translate(self.dimensions.wallThickness, self.dimensions.wallThickness)

        self.internalSpace = None
        if self.dimensions.innerSpaceHeight:
            self.internalSpace = SmartBox(self.dimensions.length - self.dimensions.wallThickness * 2, self.dimensions.width - self.dimensions.wallThickness * 2, self.dimensions.innerSpaceHeight)
            self.internalSpace.translate(self.dimensions.wallThickness, self.dimensions.wallThickness, self.dimensions.getMeshHeight())

        self.externalLid = SmartBox(self.dimensions.length, self.dimensions.width, self.dimensions.height)
        self.internalMeshHex = Hexagon(self.dimensions.getHexShortDiagonal(), self.dimensions.getMeshHeight())

        baseDistanceY = getDistanceY(self.dimensions.getHexShortDiagonal(), self.dimensions.gridThickness)
        self.fullRowCount = math.floor(self.internalMesh.width / baseDistanceY)
        self.fullRowCount += self.fullRowCount % 2
        self.distanceY = self.internalMesh.width / self.fullRowCount
        offsetY = self.distanceY - baseDistanceY

        self.hexesCoveredY = None

        self.hexConfiguration = HexagonConfiguration().withRays(offsetY, HexTileVertices.N, HexTileVertices.S)

    def createMeshHex(self, row: int, column: int) -> Part.Solid:
        startingHexX = self.dimensions.wallThickness -self.dimensions.gridThickness / 2
        startingHexY = self.dimensions.wallThickness

        solid = self.internalMeshHex.createRaySolid(self.hexConfiguration)
        solid.translate(Vector(startingHexX + self.dimensions.getDistanceX() * (column + row % 2 / 2), startingHexY + self.distanceY * row))

        return solid

    def createLidMesh(self) -> Fuser:
        print(f"Mesh lid: rows = {self.fullRowCount}, columns = {self.dimensions.getHexCountLength()}")
        hexes = Fuser()
        for row in range(self.fullRowCount + 1):
            for column in range(self.dimensions.getHexCountLength() + 1):
                if row not in [0, self.fullRowCount] or column not in [0, self.dimensions.getHexCountLength()]:
                    hexes.fuse(self.createMeshHex(row, column))

        return Fuser(self.externalLid).cut(self.internalSpace, hexes.common(self.internalMesh))

    def createLid(self, magnetDetails: Iterable[MagnetDetails]) -> MultiColourFuser:
        recessInner, handle = self.createHandle()
        magnetBases, magnetHoles = createMagnetHolders(self.dimensions.magnetDiameter, self.dimensions.magnetHeight, True, self.dimensions.height, self.dimensions.delta, magnetDetails)

        fuser = Fuser(self.createLidMesh(), magnetBases).cut(recessInner).fuse(handle).cut(magnetHoles)
        return MultiColourFuser(Colour.BASE, fuser)

    def createRecess(self, length: float, width: float, height) -> Fuser:

        baseSlopeLength = length / 3
        fullHexesCoveredX = max(1, int(2 * baseSlopeLength / self.internalMeshHex.shortDiagonal))
        slopeLength = fullHexesCoveredX * (self.internalMeshHex.shortDiagonal + self.dimensions.gridThickness) / 2


        baseSlopeWidth = width / 6
        hexesCoveredY = int(baseSlopeWidth / self.distanceY)
        rest = baseSlopeWidth - hexesCoveredY * self.distanceY

        if fullHexesCoveredX % 2 == 0:
            halfHexesCoveredY = 0
            hexesCoveredY = max(1, hexesCoveredY)
        else:
            back = self.internalMeshHex.side - self.distanceY
            forward = self.internalMeshHex.side
            if abs(-back - rest) < abs(forward - rest):
                hexesCoveredY = max(hexesCoveredY - 1, 0)
            halfHexesCoveredY = 1

        slopeWidth = hexesCoveredY * self.distanceY + halfHexesCoveredY * self.internalMeshHex.getSide()

        taperBox = createTaperedBox(length, width, height, length - slopeLength * 2, width - slopeWidth * 2)

        return Fuser(taperBox).translate(Vector(self.dimensions.length / 2, self.dimensions.width / 2))

    def getRecessDimensions(self) -> (float, float):
        baseRecessLength = self.dimensions.length / 4
        baseRecessWidth = self.dimensions.width * 0.6

        if not self.dimensions.beautifyHandle:
            return baseRecessLength, baseRecessWidth

        self.hexesCoveredY = advancedRound(baseRecessWidth / self.distanceY, 4, self.dimensions.getHexCountLength() * 2 + self.fullRowCount + 2, 0, self.fullRowCount - 1)
        recessWidth = self.hexesCoveredY * self.distanceY + self.internalMeshHex.side

        hexesCoveredX = advancedRound(baseRecessLength / (self.internalMeshHex.shortDiagonal + self.dimensions.gridThickness), 2, 1)
        recessLength = hexesCoveredX * (self.internalMeshHex.shortDiagonal + self.dimensions.gridThickness) - self.dimensions.gridThickness

        return recessLength, recessWidth

    def createHandle(self) -> (Fuser, Fuser):
        recessLength, recessWidth = self.getRecessDimensions()

        recess = self.createRecess(recessLength, recessWidth, self.dimensions.getMeshHeight() - self.dimensions.minimalMeshHeight)

        handleWidth = recessWidth + self.internalMeshHex.getSide()
        handleCentre = Vector(self.length / 2, (self.dimensions.width - handleWidth) / 2, self.dimensions.handleRadius / 3 * 2)
        roundedHandle = Part.makeCylinder(self.dimensions.handleRadius, handleWidth, handleCentre, Vector(0, 1, 0)).common(self.internalMesh.solid)

        handle = SmartBox(self.dimensions.wallThickness, handleWidth, self.internalMesh.height)
        handle.translate((self.dimensions.length - handle.length) / 2, (self.dimensions.width - handle.width) / 2)

        deltaHexes = (self.fullRowCount - self.hexesCoveredY) / 2

        hexBottom = self.createMeshHex(deltaHexes - 1, math.floor(self.dimensions.getHexCountLength() / 2))
        hexTop = self.createMeshHex(self.fullRowCount - deltaHexes + 1, math.floor(self.dimensions.getHexCountLength() / 2))

        fullHandle = Fuser(handle, roundedHandle)

        if self.dimensions.fillHandleSides:
            fullHandle.fuse(hexTop, hexBottom).common(self.internalMesh)
        else:
            fullHandle.cut(hexTop, hexBottom)

        return recess, fullHandle
