from dataclasses import dataclass

import Draft
import Part
from FreeCAD import Vector

from common.colours import MultiColourFuser, Colour
from common.fuser import Fuser
from common.magnets import MagnetDimensions, createMagnetHolders, CornerAngles
from inserts.common.meshlid import MeshLidDimensions, MeshLid
from common.pencil import Pencil
from common.smartbox import SmartBox
from common.smartsolid import SmartSolid


@dataclass
class CubeBoxDimensions:
    lid: MeshLidDimensions
    magnets: MagnetDimensions
    length: float
    width: float
    height: float
    gapHeight: float
    holderAngle: float
    wallThickness: float

    def __post_init__(self):
        self.lid.length = self.length
        self.lid.width = self.width


# Holder for the following items: minor company stations and stock markers, company charters (as a lid)
class CubeBox(SmartBox):
    def __init__(self, dimensions: CubeBoxDimensions):
        super().__init__(dimensions.length, dimensions.width, dimensions.height)
        self.dimensions = dimensions

        self.box = SmartBox(self.length - self.dimensions.magnets.getRadiusWideningAmount() * 2, self.width - self.dimensions.magnets.getRadiusWideningAmount() * 2, self.dimensions.height)
        self.box.translate(self.dimensions.magnets.getRadiusWideningAmount(), self.dimensions.magnets.getRadiusWideningAmount())

    def createBox(self) -> MultiColourFuser:
        magnetBases, magnetHoles, corners = createMagnetHolders(self.dimensions.magnets, True, self.dimensions.height, self.createMagnetLocations(False))

        fuser = Fuser(self.box)
        fuser.cut(self.createRecess(), corners).fuse(self.createWalls(), magnetBases).cut(magnetHoles)

        return MultiColourFuser(Colour.BASE, fuser)

    def createLid(self) -> MultiColourFuser:
        lid = MeshLid(self.dimensions.lid)
        magnetDetails = self.createMagnetLocations(True)
        return lid.createLid(magnetDetails)

    def createRecess(self) -> Fuser:
        pencil = Pencil()
        pencil.down(self.dimensions.gapHeight)
        pencil.left(self.dimensions.wallThickness)
        pencil.down(self.dimensions.height - self.dimensions.gapHeight - self.dimensions.wallThickness)
        pencil.arcWithCentreDirection(Vector(0, 1), Vector(self.dimensions.wallThickness - self.box.width, self.dimensions.height - self.dimensions.gapHeight - self.dimensions.wallThickness))
        pencil.up(self.dimensions.gapHeight)
        return Fuser(pencil.extrudeX(self.dimensions.length, Vector(0, self.box.yTo, self.box.zTo)))

    def createMagnetLocations(self, lid: bool):
        widerRadius = self.dimensions.magnets.getWiderBaseRadius()
        height = None if lid else self.box.height - self.dimensions.gapHeight

        return [
            self.createMagnetDetails(0, 0, 2, 3, widerRadius, None, [CornerAngles.SW], None, height),
            self.createMagnetDetails(0, 2, 2, 3, widerRadius, None, [CornerAngles.SE], None, height),

            self.createMagnetDetails(1, 0, 2, 3, widerRadius, [CornerAngles.NE], [CornerAngles.NW], None, height),
            self.createMagnetDetails(1, 2, 2, 3, widerRadius, [CornerAngles.NW], [CornerAngles.NE], None, height)
        ]

    def createWall(self) -> SmartSolid:
        return SmartBox(self.dimensions.wallThickness, self.box.width, self.dimensions.height - self.dimensions.gapHeight)

    def createLargerWall(self) -> SmartSolid:
        return SmartBox(self.dimensions.magnets.getBaseRadius() * 2, self.box.width - self.dimensions.magnets.getBaseRadius() * 2, self.dimensions.height - self.dimensions.magnets.getWideningHeight())

    def createWalls(self) -> Part.Solid:
        playerCubeSpaceLength = self.getPlayerCubeSpaceLength()
        startX = self.box.x + self.dimensions.magnets.getBaseRadius() * 2 - self.dimensions.wallThickness
        fuser = Fuser(self.createWall().translate(startX + (self.dimensions.wallThickness + playerCubeSpaceLength) * i, self.box.y) for i in range(1, 8))
        fuser.fuse(self.createLargerWall().translate(x, self.box.y + self.dimensions.magnets.getBaseRadius()) for x in [self.box.x, self.box.xTo - self.dimensions.magnets.getBaseRadius() * 2])
        return fuser.solid

    def getPlayerCubeSpaceLength(self):
        totalCubeColumns = 20
        totalCubeCompartments = 8
        cubeSize = 7.8
        totalLength = self.box.length - self.dimensions.magnets.getBaseRadius() * 4
        deltaLength = totalLength - self.dimensions.wallThickness * (totalCubeCompartments - 1) - cubeSize * totalCubeColumns
        deltaLengthPerCompartment = deltaLength / totalCubeCompartments

        return 2 * cubeSize + deltaLengthPerCompartment
