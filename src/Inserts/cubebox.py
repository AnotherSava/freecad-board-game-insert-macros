import Draft
import Part
from FreeCAD import Vector

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuse
from Inserts.common.geometry import Side
from Inserts.common.magnets import getWidestRadius, createMagnetHolders
from Inserts.common.meshlid import MeshLidDimensions, MeshLid
from Inserts.common.pencil import Pencil
from Inserts.common.smartbox import SmartBox, CornerAngleType
from dataclasses import dataclass


@dataclass
class CubeBoxDimensions:
    lid: MeshLidDimensions
    length: float
    width: float
    height: float
    cubeSize: float
    lidHeight: float
    gapHeight: float
    holderAngle: float
    wallThickness: float
    playerCubeSpaceWidth: float
    magnetDiameter: float
    magnetHeightBox: float
    magnetHeightLid: float
    thinnestWall: float
    internalWallRadius: float

    def __post_init__(self):
        self.lid.length = self.length
        self.lid.width = self.width
        self.lid.delta = self.thinnestWall
        self.lid.magnetDiameter = self.magnetDiameter


# Holder for the following items: minor company stations and stock markers, company charters (as a lid)
class CubeBox(SmartBox):
    def __init__(self, dimensions: CubeBoxDimensions):
        super().__init__(dimensions.length, dimensions.width, dimensions.height)
        self.dimensions = dimensions

    def createBox(self) -> MultiColourFuser:
        magnetBases, magnetHoles = createMagnetHolders(self.dimensions.magnetDiameter, self.dimensions.magnetHeightBox, True, self.dimensions.height, self.dimensions.thinnestWall, self.createMagnetLocations(False))

        fuser = Fuser(SmartBox(self.dimensions.length, self.dimensions.width, self.dimensions.height))
        fuser.cut(self.createRecess()).fuse(self.createWalls(), magnetBases).cut(magnetHoles)

        return MultiColourFuser(Colour.BASE, fuser)

    def createLid(self) -> MultiColourFuser:
        lid = MeshLid(self.dimensions.lid)
        magnetDetails = self.createMagnetLocations(True)
        return lid.createLid(magnetDetails)

    def createRecess(self) -> Fuser:
        pencil = Pencil()
        pencil.down(self.dimensions.gapHeight)
        backStepWidth = (self.dimensions.magnetDiameter + self.dimensions.thinnestWall * 2 + self.dimensions.wallThickness) / 2
        pencil.arcWithDestinationFromStart(Vector(self.dimensions.width / 2, self.dimensions.wallThickness - self.dimensions.height), self.dimensions.holderAngle)
        pencil.right(self.dimensions.width / 2 - backStepWidth)
        pencil.up(self.dimensions.cubeSize * 2 / 3)
        pencil.right(backStepWidth - self.dimensions.wallThickness)
        pencil.up(self.dimensions.height - self.dimensions.wallThickness - self.dimensions.cubeSize * 2 / 3)
        return Fuser(pencil.extrudeX(self.dimensions.length - self.dimensions.wallThickness * 2)).translate(Vector(self.dimensions.wallThickness, 0, self.dimensions.height))

    def createMagnetLocations(self, lid: bool):
        widerRadius = getWidestRadius(self.dimensions.magnetDiameter, self.dimensions.thinnestWall)
        rampDirection = None if lid else Side.N
        angleTypes = CornerAngleType.MAX if lid else CornerAngleType.MIN

        return [
            self.createMagnetLocation(0, 0, 2, 3, widerRadius, angleTypes, rampDirection, -1, 3, self.dimensions.wallThickness),
            self.createMagnetLocation(0, 1, 2, 3, widerRadius, angleTypes, rampDirection, 0, 3, self.dimensions.wallThickness),
            self.createMagnetLocation(0, 2, 2, 3, widerRadius, angleTypes, rampDirection, 1, 3, self.dimensions.wallThickness),

            *[self.createMagnetLocation(1, i, 2, 3, widerRadius, CornerAngleType.MAX) for i in range(2)]
        ]

    def createWall(self) -> Fuser:
        pencil = Pencil()
        pencil.up(self.dimensions.height - self.dimensions.internalWallRadius)
        pencil.arcWithRadius(self.dimensions.internalWallRadius, -90, -90)
        pencil.right(self.dimensions.width - self.dimensions.internalWallRadius)
        pencil.down(self.dimensions.height)
        return Fuser(pencil.extrudeX(self.dimensions.wallThickness))

    def createWalls(self) -> Part.Solid:
        playerCubeSpaceLength = (self.dimensions.length / 2 - self.dimensions.wallThickness * 5.5) / 5
        return fuse(self.createWall().translate(Vector((self.dimensions.wallThickness + playerCubeSpaceLength) * (i + 1))) for i in range(0, 7))
