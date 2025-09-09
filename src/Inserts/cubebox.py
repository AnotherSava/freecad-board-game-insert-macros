import Draft
import Part
from FreeCAD import Vector

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser
from Inserts.common.geometry import Side
from Inserts.common.pencil import Pencil
from Inserts.common.magnets import createMagnetHolders, getWidestRadius, MagnetDetails, createMagnetHolders
from Inserts.common.primitives import createTaperedBox
from Inserts.common.smartbox import SmartBox
from dataclasses import dataclass


@dataclass
class CubeBoxDimensions:
    length: float
    width: float
    height: float
    cubeSize: float
    lidHeight: float
    lidHandleHeight: float
    gapHeight: float
    holderAngle: float
    wallThickness: float
    playerCubeSpaceWidth: float
    magnetDiameter: float
    magnetHeightBox: float
    magnetHeightLid: float
    thinnestWall: float


# Holder for the following items: minor company stations and stock markers, company charters (as a lid)
class CubeBox:
    def __init__(self, dimensions: CubeBoxDimensions):
        self.dimensions = dimensions

    def createBox(self) -> MultiColourFuser:
        fuser = Fuser(SmartBox(self.dimensions.length, self.dimensions.width, self.dimensions.height))
        fuser.cut(self.createCubesAndTokensArea())
        magnetBases, magnetHoles = createMagnetHolders(self.dimensions.magnetDiameter, self.dimensions.magnetHeightBox, True, self.dimensions.height, self.dimensions.thinnestWall, self.createMagnetLocations(True))
        fuser.fuse(magnetBases)
        fuser.cut(magnetHoles)

        return MultiColourFuser(Colour.BASE, fuser)

    def createLid(self) -> MultiColourFuser:
        lid = SmartBox(self.dimensions.length, self.dimensions.width, self.dimensions.lidHeight)
        magnetBases, magnetHoles = createMagnetHolders(self.dimensions.magnetDiameter, self.dimensions.magnetHeightLid, False, self.dimensions.lidHeight, self.dimensions.thinnestWall, self.createMagnetLocations(False))

        recess = createTaperedBox(self.dimensions.length / 6, self.dimensions.width / 2, self.dimensions.lidHandleHeight, self.dimensions.length / 4, self.dimensions.width * 2 / 3)
        recess.translate(Vector(self.dimensions.length / 2, self.dimensions.width / 2, self.dimensions.lidHeight - self.dimensions.lidHandleHeight))

        handle = createTaperedBox(self.dimensions.wallThickness, self.dimensions.width, self.dimensions.lidHeight, self.dimensions.wallThickness * 3, self.dimensions.width)
        handle.translate(Vector((self.dimensions.length - self.dimensions.wallThickness) / 2, self.dimensions.width / 2, 0))

        fuser = MultiColourFuser(Colour.WALLED_MESH, lid)
        fuser.cut(magnetBases, recess)
        fuser.fuse(Colour.BASE, magnetBases.cut(magnetHoles))
        fuser.fuse(Colour.BASE, handle)

        return fuser.translate(Vector(0, 0, 40))

    def createCubeSpace(self, width: float) -> Part.Solid:
        pencil = Pencil()
        pencil.down(self.dimensions.gapHeight)
        backStepWidth = (self.dimensions.magnetDiameter + self.dimensions.thinnestWall * 2 + self.dimensions.wallThickness) / 2
        pencil.arcFromStart(Vector(self.dimensions.width / 2, self.dimensions.wallThickness - self.dimensions.height), self.dimensions.holderAngle)
        pencil.right(self.dimensions.width / 2 - backStepWidth)
        pencil.up(self.dimensions.cubeSize * 2 / 3)
        pencil.right(backStepWidth - self.dimensions.wallThickness)
        pencil.up(self.dimensions.height - self.dimensions.wallThickness - self.dimensions.cubeSize * 2 / 3)
        return pencil.extrudeX(width)

    def createMagnetLocations(self, ramps: bool = False):
        widestRadius = getWidestRadius(self.dimensions.magnetDiameter, self.dimensions.thinnestWall)
        magnetX = [widestRadius]
        for i in [3, 5, 7]:
            magnetX.append(self.dimensions.playerCubeSpaceWidth * i + self.dimensions.wallThickness * (i + 0.5))
        magnetX.append(self.dimensions.length - widestRadius)

        for i, x in enumerate(magnetX):
            yield MagnetDetails(Vector(x, self.dimensions.width - widestRadius))
            yield MagnetDetails(Vector(x, widestRadius), Side.N if ramps else None, -1 if i == 0 else 1 if i == len(magnetX) - 1 else 0, 3, self.dimensions.wallThickness)

    def createCubesAndTokensArea(self) -> Part.Solid:
        fuser = Fuser()

        for i in range(7):
            playerCubesPositionX = self.dimensions.playerCubeSpaceWidth * i + self.dimensions.wallThickness * (i + 1)
            playerCubes = self.createCubeSpace(self.dimensions.playerCubeSpaceWidth)
            playerCubes.translate(Vector(playerCubesPositionX, 0, self.dimensions.height))
            fuser.fuse(playerCubes)

        timberCubes = self.createCubeSpace(self.dimensions.length - self.dimensions.playerCubeSpaceWidth * 7 - self.dimensions.wallThickness * 9)
        timberCubes.translate(Vector(self.dimensions.playerCubeSpaceWidth * 7 + self.dimensions.wallThickness * 8, 0, self.dimensions.height))
        fuser.fuse(timberCubes)

        return fuser.solid
