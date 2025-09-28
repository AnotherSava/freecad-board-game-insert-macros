from dataclasses import dataclass

import Draft
import Part
from FreeCAD import Vector

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuse
from Inserts.common.geometry import Side
from Inserts.common.magnets import MagnetDimensions, createMagnetHolders, RampDetails, CornerAngles
from Inserts.common.meshlid import MeshLidDimensions, MeshLid
from Inserts.common.pencil import Pencil
from Inserts.common.smartbox import SmartBox
from Inserts.common.smartsolid import SmartSolid


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
        backStepWidth = self.dimensions.magnets.getBaseRadius() + self.dimensions.magnets.getWiderBaseRadius()
        pencil.arcWithDestinationFromStart(Vector(self.dimensions.width - backStepWidth, self.dimensions.wallThickness - self.dimensions.height), self.dimensions.holderAngle)
        pencil.up(self.dimensions.height - self.dimensions.gapHeight - self.dimensions.wallThickness)
        pencil.right(backStepWidth)
        pencil.up(self.dimensions.gapHeight)
        return Fuser(pencil.extrudeX(self.dimensions.length)).translate(Vector(0, 0, self.dimensions.height))

    def createMagnetLocations(self, lid: bool):
        widerRadius = self.dimensions.magnets.getWiderBaseRadius()

        return [
            self.createMagnetDetails(0, 0, 2, 3, widerRadius, None, [CornerAngles.SW], None if lid else RampDetails(Side.N, -1, 3, self.dimensions.wallThickness), 1, False),
            self.createMagnetDetails(0, 1, 2, 3, widerRadius, None, None, None if lid else RampDetails(Side.N, 0, 3, self.dimensions.wallThickness), 1, False),
            self.createMagnetDetails(0, 2, 2, 3, widerRadius, None, [CornerAngles.SE], None if lid else RampDetails(Side.N, 1, 3, self.dimensions.wallThickness), 1, False),

            self.createMagnetDetails(1, 0, 2, 3, widerRadius, [CornerAngles.SW], [CornerAngles.NW], None, 1, False),
            self.createMagnetDetails(1, 1, 2, 3, widerRadius, None, None),
            self.createMagnetDetails(1, 2, 2, 3, widerRadius, [CornerAngles.SE], [CornerAngles.NE], None, 1, False)
        ]

    def createWall(self) -> SmartSolid:
        return SmartBox(self.dimensions.wallThickness, self.box.width, self.dimensions.height - self.dimensions.gapHeight)

    def createLargerWall(self) -> SmartSolid:
        return SmartBox(self.dimensions.wallThickness, self.dimensions.width - self.dimensions.magnets.getWiderBaseRadius() * 2, self.dimensions.height - self.dimensions.magnets.getWideningHeight())

    def createWalls(self) -> Part.Solid:
        playerCubeSpaceLength = (self.box.length / 2 - self.dimensions.wallThickness * 5.5) / 5
        fuser = Fuser(self.createWall().translate(self.box.x + (self.dimensions.wallThickness + playerCubeSpaceLength) * i, self.box.y) for i in [1, 2, 3, 4, 6, 7])
        fuser.fuse(self.createLargerWall().translate(self.box.x + (self.dimensions.wallThickness + playerCubeSpaceLength) * i, self.dimensions.magnets.getWiderBaseRadius()) for i in [0, 5, 10])
        return fuser.solid
